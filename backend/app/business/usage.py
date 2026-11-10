"""Usage coverage is explicit: an unreported bill is not a zero bill."""
from __future__ import annotations

import math


def valid_cost(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def summarize_calls(calls):
    known = [call["cost"] for call in calls if valid_cost(call.get("cost"))]
    tokens = [call["tokens"] for call in calls if isinstance(call.get("tokens"), int) and not isinstance(call.get("tokens"), bool) and call["tokens"] >= 0]
    complete_cost = bool(calls) and len(known) == len(calls)
    return {"call_count": len(calls), "calls": calls, "actual_tokens": sum(tokens) if calls and len(tokens) == len(calls) else None,
            "reported_tokens_subtotal": sum(tokens), "cost": sum(known) if complete_cost else None,
            "reported_cost_subtotal": sum(known), "calls_with_reported_cost": len(known),
            "cost_status": "provider_reported" if complete_cost else "partial" if known else "unknown"}


def openai_usage_upper_bound(usage, base_url, model):
    """Conservative token-priced estimate, never a provider-reported invoice.

    Luna Standard: $0.10/$0.50 per million input/output tokens. Charge every
    input at the cache-write ceiling ($0.125), ignoring cache discounts.
    Long prompts apply 2x input and 1.5x output. Unknown usage stays reserved.
    """
    from decimal import Decimal
    from urllib.parse import urlsplit
    if urlsplit(base_url or "").hostname != "api.openai.com" or model != "gpt-6-luna" or not isinstance(usage, dict):
        return None
    prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if any(not isinstance(n, int) or isinstance(n, bool) or n < 0 for n in (prompt, completion)):
        return None
    input_rate, output_rate = (Decimal(".25"), Decimal(".75")) if prompt > 272000 else (Decimal(".125"), Decimal(".50"))
    return float((prompt * input_rate + completion * output_rate) / Decimal(1000000))
