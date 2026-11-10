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
