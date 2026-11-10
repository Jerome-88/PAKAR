"""Rebuild partial state only from already committed, validated interaction events."""
from copy import deepcopy

from .contracts import BusinessAction, SwarmAction, DialogueAction, Shock
from .simulation import BusinessSimulation
from .swarm import SwarmSimulation
from .usage import summarize_calls
from .discussion import DialogueSimulation, reactive
from .information import scoped as information_scoped


def replay_committed(snapshot, events, calls=(), *, stop_reason="runtime_time_budget", reserved_token_cap=0):
    if not events:
        raise ValueError("Tidak ada interaksi tersimpan untuk dipulihkan")
    swarm = snapshot.get("config", {}).get("interaction_mode") == "swarm"
    active_dialogue = reactive(snapshot.get("config", {}))
    run_id = events[0]["id"].rsplit(":event:", 1)[0]
    extra = {"strict_trigger_reply": snapshot["config"].get("strict_trigger_reply", False), "public_room": information_scoped(snapshot)} if active_dialogue else {}
    sim = (DialogueSimulation if active_dialogue else SwarmSimulation if swarm else BusinessSimulation)(run_id, snapshot["personas"], snapshot["values"], snapshot["config"]["max_events"], **extra)
    for event in events:
        kind, round_number = event["kind"], event["round"]
        if kind == "shock":
            rebuilt = sim.inject(Shock.model_validate(event["shock"]), round_number)
        elif kind == "shock_expired":
            rebuilt = sim.expire_shock(round_number)
        elif kind == "action_rejected":
            rebuilt = sim.reject(event, event["rationale"], round_number)
        else:
            raw = {"actor_id": event["actor_id"], "target_id": event["target_id"], "kind": kind,
                   "expected_version": event["state_before"]["version"], "parent_event_ids": event["parent_event_ids"], "amount": event.get("amount"), "rationale": event["rationale"]}
            if swarm:
                stance = event["stance_update"]
                raw.update(visibility=event["visibility"], thread_id=None if kind == "post_message" else event.get("thread_id"), reply_to=event.get("reply_to"), content=event.get("content", ""),
                           stance=stance["after"], stance_reason=stance["reason"], influenced_by_event_ids=stance["influenced_by_event_ids"])
            if active_dialogue:
                raw["dialogue_act"] = event["dialogue_act"]
                sim.current_dispatch = event.get("dispatch")
            rebuilt = sim.apply((DialogueAction if active_dialogue else SwarmAction if swarm else BusinessAction).model_validate(raw), round_number)
        if not rebuilt or rebuilt["id"] != event["id"] or rebuilt["kind"] != kind:
            raise ValueError("Urutan event pemulihan tidak konsisten")
        # Compare authoritative deltas, not narrative alone, before publishing.
        if "state_after" in event and rebuilt["state_after"] != event["state_after"]:
            raise ValueError("State pemulihan berbeda dari event tersimpan")
    copied_calls = deepcopy(list(calls))
    reserved = max(reserved_token_cap, sum(c.get("reserved_tokens_upper_bound", c.get("tokens") or 0) for c in copied_calls))
    return sim.snapshot() | {"engine": "oasis-business", "stop_reason": stop_reason, "response_mode": snapshot.get("response_mode", "json_object"),
                             "usage": summarize_calls(copied_calls) | {"reserved_tokens_upper_bound": reserved},
                             "recovery": {"method": "validated_event_replay_v1", "committed_events": len(events), "new_model_calls": 0}}
