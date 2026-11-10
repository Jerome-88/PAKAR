"""Wait only for explicitly rate-rejected Groq requests, never model failures.

The caller's process/async deadline remains authoritative. SDK retries stay off.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from urllib.parse import urlsplit
from functools import lru_cache


def failure_details(error):
    """Expose fixed diagnostic terms, never provider bodies or generated text."""
    status = getattr(error, "status_code", None)
    status = status if isinstance(status, int) and 400 <= status <= 599 else None
    body = getattr(error, "body", None)
    value = json.dumps(body, default=str).casefold() if isinstance(body, (dict, list)) else ""
    terms = [term for term in ("maxlength", "maxitems", "minitems", "additionalproperties", "required", "enum", "json_validate_failed", "json_schema", "response_format", "max_tokens", "not supported", "rate limit", "tokens per minute", "tokens per day") if term in value]
    return {"status_code": status, "failure_terms": terms}


@lru_cache(maxsize=1)
def token_encoder():
    import tiktoken
    return tiktoken.get_encoding("o200k_base")


def request_tokens(messages, formatting, output_tokens):
    # Count the complete bounded wire context plus completion and provider
    # overhead. This is an admission estimate, not provider billing usage.
    wire = json.dumps({"messages": messages, "response_format": formatting}, ensure_ascii=False, separators=(",", ":"))
    return len(token_encoder().encode(wire, disallowed_special=())) + output_tokens + 512


def is_groq_reasoning_model(base_url, model):
    return urlsplit(base_url or "").hostname == "api.groq.com" and str(model).rsplit("/", 1)[-1].startswith("gpt-oss-")


def retry_delay(error, base_url, attempt):
    if urlsplit(base_url or "").hostname != "api.groq.com" or attempt >= 3 or getattr(error, "status_code", None) != 429:
        return None
    headers = getattr(getattr(error, "response", None), "headers", {})
    try:
        delay = float(headers.get("retry-after", ""))
    except (ValueError, TypeError):
        return None
    return max(1.0, delay + 0.5) if math.isfinite(delay) and 0 <= delay <= 45 else None


def complete(operation, base_url, on_wait=None):
    for attempt in range(4):
        try:
            return operation()
        except Exception as error:
            delay = retry_delay(error, base_url, attempt)
            if delay is None:
                raise
            if on_wait:
                on_wait(delay)
            time.sleep(delay)


async def complete_async(operation, base_url, on_wait=None):
    for attempt in range(4):
        try:
            return await operation()
        except Exception as error:
            delay = retry_delay(error, base_url, attempt)
            if delay is None:
                raise
            if on_wait:
                on_wait(delay)
            await asyncio.sleep(delay)
