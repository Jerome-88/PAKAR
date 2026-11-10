"""Request schemas scoped to one turn or review; never replace reducer checks."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from decimal import Decimal
from urllib.parse import urlparse

from .contracts import BusinessAction, SwarmAction, DialogueAction, Finding


def strict_schema(schema):
    result = deepcopy(schema)

    def visit(value):
        if isinstance(value, dict):
            if value.get("type") == "object":
                value["additionalProperties"] = False
                value["required"] = list(value.get("properties", {}))
            value.pop("default", None)
            if isinstance(value.get("title"), str):
                value.pop("title")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(result)
    return result


def reference_array(values):
    values = sorted(set(values))
    return {"type": "array", "items": {"type": "string", **({"enum": values} if values else {})}, **({} if values else {"maxItems": 0})}


def discovery_schema(claims, limit=4, candidates=None):
    text = {"type": "string", "minLength": 2, "maxLength": 300}
    item = {"type": "object", "additionalProperties": False, "required": ["name", "role", "goals", "constraints", "claim_ids", "rationale"], "properties": {
        "name": {**text, "maxLength": 160},
        "role": {"type": "string", "enum": ["operator", "customer", "supplier", "competitor", "employee", "regulator", "partner", "investor", "community"]},
        "goals": {"type": "array", "items": text, "minItems": 1, "maxItems": 2},
        "constraints": {"type": "array", "items": text, "maxItems": 2},
        "claim_ids": reference_array(c["id"] for c in claims),
        "rationale": text,
    }}
    item["properties"]["claim_ids"]["maxItems"] = min(3, len(claims))
    if candidates:
        item["properties"]["role"]["enum"] = [p["role"] for p in candidates]
        item["properties"]["name"]["enum"] = [p["name"] for p in candidates]
    return {"type": "object", "additionalProperties": False, "required": ["personas"], "properties": {"personas": {"type": "array", "items": item, "minItems": 2, "maxItems": limit}}}


def action_schema(simulation, persona_id):
    schema = strict_schema(BusinessAction.model_json_schema())
    props = schema["properties"]
    props["actor_id"] = {"type": "string", "enum": [persona_id]}
    props["expected_version"] = {"type": "integer", "enum": [simulation.states[persona_id]["version"]]}
    props["target_id"] = {"type": "string", "enum": [key for key in simulation.personas if key != persona_id]}
    role = simulation.personas[persona_id].role
    kinds = ["express_concern", "request_information", "cooperate", "compete"]
    if role == "supplier" and any(p.role == "operator" for p in simulation.personas.values()):
        kinds.append("offer_terms")
    if role == "operator":
        if any(e["kind"] == "offer_terms" and e["target_id"] == persona_id for e in simulation.visible_events(persona_id)):
            kinds.append("accept_terms")
        if simulation.shock and simulation.shock["kind"] == "competitor_price_cut" and simulation.shock["response_strategy"] == "match_price" and simulation.environment["competitor_price"] is not None:
            kinds.append("adjust_price")
    props["kind"] = {"type": "string", "enum": kinds}
    props["parent_event_ids"] = reference_array(e["id"] for e in simulation.visible_events(persona_id))
    props["parent_event_ids"]["maxItems"] = min(10, len(simulation.visible_events(persona_id)))
    # JSON numbers avoid provider-specific regex support for Decimal strings.
    props["amount"] = {"type": ["number", "null"], "exclusiveMinimum": 0, "maximum": 1e15}
    if not {"offer_terms", "adjust_price"} & set(kinds):
        props["amount"] = {"type": "null"}
    if "adjust_price" in kinds and Decimal(str(simulation.states[persona_id]["selling_price"])) != Decimal(str(simulation.environment["competitor_price"])):
        # This is the user's explicit scenario policy, not an inferred market
        # response. Preserve its exact decimal value instead of a float roundtrip.
        props["kind"]["enum"] = ["adjust_price"]
        props["amount"] = {"type": "string", "enum": [str(simulation.environment["competitor_price"])]}
    return schema


def review_schema(role, snapshot, simulation, evidence):
    finding = strict_schema(Finding.model_json_schema())
    props = finding["properties"]
    props["author"] = {"type": "string", "enum": [role]}
    props["status"] = {"type": "string", "enum": ["NEEDS_VALIDATION"]}
    for field, values in {
        "claim_ids": (c["id"] for c in snapshot["claims"]),
        "persona_ids": (p["id"] for p in snapshot["personas"]),
        "event_ids": (e["id"] for e in simulation["events"]),
        "evidence_ids": (e["id"] for e in evidence),
        "calculation_ids": [simulation["calculation"]["id"]],
    }.items():
        props[field] = reference_array(values)
    return {"type": "object", "properties": {"findings": {"type": "array", "items": finding, "maxItems": 2}, "disagreements": {"type": "array", "items": {"type": "string", "maxLength": 2000}, "maxItems": 8}}, "required": ["findings", "disagreements"], "additionalProperties": False}


def swarm_action_schema(simulation, persona_id, context=None):
    context = context or simulation.turn_context(persona_id)
    events = context["visible_events"]
    schema = strict_schema((DialogueAction if hasattr(simulation, "current_dispatch") else SwarmAction).model_json_schema())
    props = schema["properties"]
    legacy = action_schema(simulation, persona_id)["properties"]
    props["actor_id"] = legacy["actor_id"]
    props["expected_version"] = legacy["expected_version"]
    props["target_id"] = {"type": "string", "enum": ["all", *[key for key in simulation.personas if key != persona_id]]}
    messages = [e for e in events if e["kind"] in {"post_message", "reply_message"}]
    business = [kind for kind in legacy["kind"]["enum"] if kind in {"offer_terms", "accept_terms", "adjust_price"}]
    props["kind"] = {"type": "string", "enum": ["post_message", "abstain", *(["reply_message"] if messages else []), *business]}
    if legacy["kind"]["enum"] == ["adjust_price"]:
        props["kind"] = legacy["kind"]
    props["amount"] = legacy["amount"]
    props["parent_event_ids"] = reference_array(e["id"] for e in events)
    props["parent_event_ids"]["maxItems"] = min(5, len(events))
    props["influenced_by_event_ids"] = reference_array(e["id"] for e in events if e["actor_id"] != persona_id)
    props["influenced_by_event_ids"]["maxItems"] = min(3, len(events))
    props["reply_to"] = {"type": ["string", "null"], "enum": [None, *[e["id"] for e in messages]]}
    props["thread_id"] = {"type": ["string", "null"], "enum": [None, *sorted({e["thread_id"] for e in messages})]}
    props["content"]["maxLength"] = 600
    props["stance_reason"]["maxLength"] = 240
    trigger = (getattr(simulation, "current_dispatch", None) or {}).get("trigger_event_id")
    if getattr(simulation, "strict_trigger_reply", False) and trigger:
        parent = next(e for e in events if e["id"] == trigger)
        props["kind"] = {"type": "string", "enum": ["reply_message"]}
        props["target_id"] = {"type": "string", "enum": [parent["actor_id"]]}
        props["reply_to"] = {"type": "string", "enum": [trigger]}
        props["thread_id"] = {"type": "string", "enum": [parent["thread_id"]]}
        props["visibility"] = {"type": "string", "enum": [parent["visibility"]]}
        props["parent_event_ids"] = {"type": "array", "items": {"type": "string", "enum": [trigger]}, "minItems": 1, "maxItems": 1}
        props["influenced_by_event_ids"] = {"type": "array", "items": {"type": "string", "enum": [trigger]}, "maxItems": 1}
    return schema


def response_format(name, schema):
    return {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}}


def provider_options(base_url, *, sort=None, model=None):
    if urlparse(base_url or "").hostname == "openrouter.ai":
        # Fail visibly if this model has no compatible provider. No model fallback.
        provider = {"require_parameters": True}
        raw_order = os.getenv("PAKAR_OPENROUTER_PROVIDER_ORDER")
        if raw_order:
            order = json.loads(raw_order)
            if not isinstance(order, list) or not 1 <= len(order) <= 8 or any(not isinstance(item, str) or not item.strip() or len(item) > 100 for item in order):
                raise ValueError("Provider order must contain one to eight provider names")
            provider.update(order=[item.strip() for item in order], allow_fallbacks=False)
        if sort is not None:
            if sort != "latency":
                raise ValueError("Unsupported provider ordering")
            provider["sort"] = sort
        raw = os.getenv("PAKAR_OPENROUTER_MAX_PRICE")
        if raw:
            caps = json.loads(raw)
            if not isinstance(caps, dict) or not {"prompt", "completion"} <= caps.keys() or set(caps) - {"prompt", "completion", "request"}:
                raise ValueError("Price caps require prompt/completion prices per million tokens")
            if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0 for value in caps.values()):
                raise ValueError("Price caps must be finite nonnegative numbers")
            provider["max_price"] = caps
            provider["allow_fallbacks"] = False
        body = {"provider": provider}
        # Qwen's hidden reasoning shares the output cap with the required JSON.
        # These bounded turns need the visible action, not an extra reasoning pass.
        if (model or "").casefold().startswith("qwen/"):
            body["reasoning"] = {"enabled": False}
        return {"extra_body": body}
    return {}


def completion_parameters(model, output_limit):
    leaf = (model or "").casefold().rsplit("/", 1)[-1]
    if leaf.startswith("gpt-6"):
        # Luna's Chat Completions tool calling requires non-reasoning mode.
        return {"max_completion_tokens": output_limit, "reasoning_effort": "none"}
    if leaf.startswith("gpt-5"):
        return {"max_completion_tokens": output_limit}
    return {"max_tokens": output_limit, "temperature": 0.2}
