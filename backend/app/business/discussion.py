"""Bounded reactive dialogue on the existing swarm reducer, without extra LLMs."""
from collections import Counter
from copy import deepcopy
from difflib import SequenceMatcher
import re

from .contracts import DialogueAction
from .swarm import SwarmSimulation, MESSAGE_KINDS

POLICY = "reactive-v2"
TRIGGERS = {"question", "challenge"}


def quality(events, personas):
    messages = [e for e in events if e["kind"] in MESSAGE_KINDS]
    by_id = {e["id"]: e for e in messages}
    roles = {key: p.role for key, p in personas.items()}
    links, repeated, texts = set(), [], []
    customer_replies = 0
    question_like_answers = []
    for event in messages:
        parent = by_id.get(event.get("reply_to"))
        if parent and parent["actor_id"] != event["actor_id"]:
            links.add((event["actor_id"], parent["actor_id"]))
            customer_replies += roles.get(event["actor_id"]) == roles.get(parent["actor_id"]) == "customer"
        text = re.sub(r"\W+", " ", event.get("content", "").casefold()).strip()
        if len(text) >= 40 and any(SequenceMatcher(None, text, prior, autojunk=False).ratio() >= .85 for prior in texts):
            repeated.append(event["id"])
        texts.append(text)
        if event.get("dialogue_act") == "answer" and event.get("content", "").rstrip().endswith("?"):
            question_like_answers.append(event["id"])
    questions = [e for e in messages if e.get("dialogue_act") == "question"]
    unanswered = [e["id"] for e in questions if not any(reply.get("reply_to") == e["id"] and reply["actor_id"] == e["target_id"] for reply in messages)]
    reciprocal = {tuple(sorted((a, b))) for a, b in links if (b, a) in links}
    warnings = []
    if not reciprocal:
        warnings.append("Belum ada pasangan peserta yang saling membalas dua arah.")
    if len(repeated) >= 2 and len(repeated) / max(1, len(messages)) >= .25:
        warnings.append("Banyak pesan sangat mirip; kedalaman diskusi perlu diperiksa.")
    if unanswered:
        warnings.append(f"{len(unanswered)} pertanyaan belum mendapat balasan dari penerimanya.")
    return {"version": "dialogue-structure-v1", "messages": len(messages), "reply_pairs": len(links), "reciprocal_pairs": len(reciprocal),
            "customer_peer_replies": customer_replies, "near_duplicate_event_ids": repeated,
            "question_like_answer_event_ids": question_like_answers,
            "questions": len(questions), "questions_without_recipient_reply": unanswered,
            "warnings": warnings, "limited_exchange": not reciprocal or (len(repeated) >= 2 and len(repeated) / max(1, len(messages)) >= .25),
            "notice": "Kemiripan dihitung dari teks dan balasan dari referensi event. Ini bukan penilaian kebenaran, kecukupan jawaban atau kualitas bisnis."}


class DialogueSimulation(SwarmSimulation):
    def __init__(self, *args, strict_trigger_reply=False, public_room=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_dispatch = None
        self.strict_trigger_reply = strict_trigger_reply
        self.public_room = public_room

    def turn_context(self, actor_id, trigger_id=None):
        if not trigger_id and (self.current_dispatch or {}).get("actor_id") == actor_id:
            trigger_id = self.current_dispatch.get("trigger_event_id")
        context = super().turn_context(actor_id)
        if trigger_id:
            parent = next((e for e in self.visible_events(actor_id) if e["id"] == trigger_id and e["actor_id"] != actor_id), None)
            if parent:
                fields = ("id", "sequence", "round", "actor_id", "target_id", "kind", "amount", "content", "rationale", "visibility", "thread_id", "reply_to", "parent_event_ids", "stance_update", "dialogue_act")
                if not any(e["id"] == trigger_id for e in context["visible_events"]):
                    context["visible_events"].append({k: parent[k] for k in fields if k in parent})
                context["suggested_reply_to"] = trigger_id
                context["suggested_reply_template"] = {"kind": "reply_message", "target_id": parent["actor_id"], "visibility": parent["visibility"], "thread_id": parent["thread_id"], "reply_to": trigger_id, "parent_event_ids": [trigger_id]}
        selected = {event["id"] for event in context["visible_events"][-5:]}
        if context["suggested_reply_to"]:
            selected.add(context["suggested_reply_to"])
        roots = {event.get("thread_id") for event in context["visible_events"] if event["id"] in selected}
        context["visible_events"] = [event for event in context["visible_events"] if event["id"] in selected or event["id"] in roots]
        return context

    def apply(self, action: DialogueAction, round_number):
        if self.public_room and (action.kind not in {"post_message", "reply_message", "abstain"} or (action.kind != "abstain" and action.visibility != "public") or action.amount is not None):
            raise ValueError("Ruang stakeholder hanya menerima diskusi publik; transaksi dan data internal tidak dibagikan")
        trigger = (self.current_dispatch or {}).get("trigger_event_id")
        if self.strict_trigger_reply and trigger and (action.kind != "reply_message" or action.reply_to != trigger):
            raise ValueError("Giliran respons harus membalas event pemicu yang ditugaskan")
        if self.strict_trigger_reply and trigger:
            parent = next((e for e in self.visible_events(action.actor_id) if e["id"] == trigger), None)
            if not parent or action.target_id != parent["actor_id"]:
                raise ValueError("Penerima respons harus penulis pesan pemicu yang terlihat")
        if action.kind == "abstain" and action.dialogue_act != "abstain":
            raise ValueError("Abstain memerlukan intent abstain")
        if action.kind != "abstain" and action.dialogue_act == "abstain":
            raise ValueError("Intent abstain tidak membuat pesan")
        if action.dialogue_act in {"question", "challenge"} and action.target_id not in self.personas:
            raise ValueError("Pertanyaan/sanggahan memerlukan penerima persona spesifik")
        if action.dialogue_act in {"answer", "challenge", "clarification"} and not action.reply_to:
            raise ValueError("Jawaban/sanggahan/klarifikasi harus merujuk pesan")
        event = super().apply(action, round_number)
        event["dialogue_act"] = action.dialogue_act
        if self.current_dispatch:
            event["dispatch"] = deepcopy(self.current_dispatch)
        self.events[-1] = deepcopy(event)
        return event

    def snapshot(self):
        return super().snapshot() | {"discussion_policy": POLICY, "discussion_quality": quality(self.events, self.personas)}


class ReactiveAgenda:
    """All actors get a base turn; bounded targeted follow-ups can interrupt it."""
    def __init__(self, sim, followups=2, peer_exchange=False, *, adaptive=False, final_round=None):
        self.sim, self.followups, self.peer_exchange = sim, followups, peer_exchange
        self.adaptive, self.final_round = adaptive, final_round

    def turns(self, round_number):
        remaining = list(self.sim.turn_order())
        shock = self.sim.shock or {}
        announcement = shock.get("announce_to_personas") and round_number in {shock.get("effective_round"), shock.get("effective_round", 0) + shock.get("duration_rounds", 0)}
        if self.adaptive and not announcement and 1 < round_number < (self.final_round or round_number):
            public = [event for event in self.sim.events if event.get("kind") in MESSAGE_KINDS and event.get("visibility") == "public"]
            def has_new_input(actor):
                own = [event for event in public if event["actor_id"] == actor]
                if not own or self.sim.personas[actor].role == "operator":
                    return True
                own_ids = {event["id"] for event in own}
                last = max(event["sequence"] for event in own)
                return any(event["sequence"] > last and event["actor_id"] != actor
                           and (event.get("target_id") == actor or event.get("reply_to") in own_ids) for event in public)
            remaining = [actor for actor in remaining if has_new_input(actor)]
        counts, selected_triggers = Counter(), set()
        extra = 0
        while remaining or extra < self.followups:
            pending = []
            for event in self.sim.events:
                actor = event["target_id"]
                if event.get("dialogue_act") not in TRIGGERS or actor not in self.sim.personas or event["id"] in selected_triggers:
                    continue
                if any(e.get("reply_to") == event["id"] and e["actor_id"] == actor for e in self.sim.events):
                    continue
                if counts[actor] >= 2 or (actor not in remaining and extra >= self.followups):
                    continue
                if event["id"] not in {e["id"] for e in self.sim.visible_events(actor)}:
                    continue
                pending.append(event)
            # Finish a participant's requested response before another opening
            # statement, while the base list guarantees eventual coverage.
            trigger = pending[0] if pending else None
            if trigger:
                actor = trigger["target_id"]
                selected_triggers.add(trigger["id"])
            elif remaining:
                actor = remaining[0]
                if self.peer_exchange and round_number >= 2 and self.sim.personas[actor].role == "customer":
                    peers = [e for e in self.sim.visible_events(actor)
                        if e["kind"] in MESSAGE_KINDS and e.get("visibility") == "public"
                        and e["actor_id"] != actor and self.sim.personas[e["actor_id"]].role == "customer"
                        and not any(reply.get("reply_to") == e["id"] and reply["actor_id"] == actor for reply in self.sim.events)]
                    if peers:
                        # Prefer another lens and an opening statement over a
                        # repeated question; use existing base slots, not N² calls.
                        peers.sort(key=lambda e: (e.get("dialogue_act") in TRIGGERS, -e["sequence"]))
                        trigger = peers[0]
            else:
                return
            followup = actor not in remaining
            if followup:
                extra += 1
            else:
                remaining.remove(actor)
            counts[actor] += 1
            yield {"actor_id": actor, "round": round_number, "trigger_event_id": trigger["id"] if trigger else None,
                   "reason": "targeted_response" if trigger in pending else "peer_exchange" if trigger else "participant_turn", "followup": followup}


def reactive(config):
    return config.get("interaction_mode") == "swarm" and config.get("discussion_policy") == POLICY
