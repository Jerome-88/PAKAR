"""One external operation per process. stdout is a sanitized JSON envelope."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import HTTPRedirectHandler, Request, build_opener

# Avoid importing the application package merely to monitor its owner.
if __package__:
    from ..child_guard import watch_parent
    from ..llm_access import require_allowed_llm_endpoint
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from child_guard import watch_parent
    from llm_access import require_allowed_llm_endpoint
watch_parent()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_error(error):
    """Classify a failure without exporting messages, URLs, headers or prompts."""
    status = getattr(error, "status_code", None)
    if not isinstance(status, int) or not 400 <= status <= 599:
        status = None
    body = getattr(error, "body", None)
    # Only use text internally to choose a fixed enum. Never return it.
    text = json.dumps(body, default=str).lower() if isinstance(body, (dict, list)) else ""
    name = type(error).__name__
    kind = "worker_error"
    if status == 429: kind = "rate_limit"
    elif status in (401, 403): kind = "authorization"
    elif status == 402: kind = "credit_budget"
    elif status == 413: kind = "request_too_large"
    elif status and status >= 500: kind = "provider_unavailable"
    elif status in (400, 422): kind = "schema_or_parameters" if any(word in text for word in ("schema", "parameter", "maxlength", "maxitems")) else "provider_request"
    elif "Timeout" in name: kind = "timeout"
    elif "Connection" in name: kind = "connection"
    terms = [term for term in ("maxlength", "maxitems", "additionalproperties", "required", "json_schema", "response_format", "max_tokens", "guided_json", "not supported", "concurren", "rate limit", "tokens per minute", "requests per minute", "upstream") if term in text]
    result = {"ok": False, "error_type": name, "status_code": status, "failure_kind": kind, "failure_terms": terms}
    headers = getattr(getattr(error, "response", None), "headers", {})
    retry_after = headers.get("Retry-After") if hasattr(headers, "get") else None
    if isinstance(retry_after, str) and retry_after.isdigit() and 0 <= int(retry_after) <= 3600:
        result["retry_after_seconds"] = int(retry_after)
    return result


def main():
    try:
        message = json.load(sys.stdin)
        payload = message["payload"]
        if message["operation"] == "bps_fetch":
            from urllib.parse import urlsplit

            url = urlsplit(payload["url"])
            if url.scheme != "https" or url.hostname != "webapi.bps.go.id" or url.username or url.password:
                raise ValueError("Invalid official host")
            request = Request(payload["url"], headers={"Accept": "application/json", "User-Agent": "PAKAR/1.1"})
            with build_opener(NoRedirect).open(request, timeout=payload["timeout"]) as response:
                raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ValueError("Oversized source")
            # Return raw content for the checksum without leaking request URLs.
            data = {"raw": raw.decode("utf-8")}
        elif message["operation"] == "openrouter_credit":
            require_allowed_llm_endpoint("https://openrouter.ai/api/v1")
            # Fixed official host, no redirects and no key-bearing diagnostics.
            headers = {"Authorization": "Bearer " + payload["api_key"], "Accept": "application/json"}
            def read(endpoint):
                with build_opener(NoRedirect).open(Request("https://openrouter.ai/api/v1/" + endpoint, headers=headers), timeout=8) as response:
                    raw = response.read(65537)
                    if len(raw) > 65536:
                        raise ValueError("Oversized credit response")
                    return json.loads(raw)["data"]
            credit = read("key")
            remaining = credit.get("limit_remaining")
            if remaining is None:
                credit = read("credits")
                remaining = float(credit["total_credits"]) - float(credit["total_usage"])
            data = {"remaining_usd": remaining}
        elif message["operation"] == "llm_completion":
            require_allowed_llm_endpoint(payload["base_url"])
            from openai import OpenAI

            client = OpenAI(api_key=payload["api_key"], base_url=payload["base_url"],
                            timeout=payload["timeout"], max_retries=0,
                            default_headers={"User-Agent": "curl/8.5.0", "Accept": "application/json"})
            try:
                if __package__:
                    from .groq_limits import complete
                else:
                    from groq_limits import complete
                rate_waits = []
                response = complete(lambda: client.chat.completions.create(**payload["request"]), payload["base_url"], rate_waits.append)
                data = {"id": response.id, "model": response.model, "provider": getattr(response, "provider", None),
                        "usage": response.usage.model_dump() if response.usage else None,
                        "finish_reason": response.choices[0].finish_reason,
                        "content": response.choices[0].message.content,
                        "rate_limit_waits_seconds": rate_waits}
            finally:
                client.close()
        else:
            raise ValueError("Unsupported worker operation")
        envelope = {"ok": True, "data": data}
    except Exception as error:
        envelope = safe_error(error)
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
