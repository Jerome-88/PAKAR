"""Threaded, access-scoped business discussion on the existing financial reducer."""
from copy import deepcopy

from .contracts import BusinessAction, SwarmAction
from uuid import uuid4
from .simulation import BusinessSimulation, fixture_action

VERSION = "swarm-v1"
MESSAGE_KINDS = {"post_message", "reply_message"}
LENSES = (
    ("Nilai dan harga", "Memeriksa manfaat dibanding harga yang dibayar"),
    ("Kualitas dan kejelasan", "Memeriksa kualitas dan informasi produk yang belum terbukti"),
    ("Keandalan layanan", "Memeriksa konsistensi layanan dan ketersediaan pasokan"),
    ("Kemudahan penggunaan", "Memeriksa hambatan mencoba dan menggunakan produk atau layanan"),
    ("Alternatif pilihan", "Membandingkan diferensiasi dengan alternatif yang disebut dokumen"),
    ("Dukungan setelah pembelian", "Memeriksa kebutuhan bantuan dan penanganan keluhan"),
)


def is_quiet_round(sim, start, round_number, round_limit, scheduled_shock=None):
    if not sim.events[start:] or any(e["kind"] != "abstain" for e in sim.events[start:]):
        return False
    if scheduled_shock:
        begins = scheduled_shock["effective_round"]
        ends = begins + scheduled_shock.get("duration_rounds", 3)
        if any(round_number < milestone <= round_limit for milestone in (begins, ends)):
            return False
    return True


def expand_customer_cohort(personas, count=4, limit=8):
    """Lenses are scenario hypotheses, never inferred demographics or market shares."""
    base = next((p for p in personas if p["role"] == "customer"), None)
    if not base:
        raise ValueError("Swarm memerlukan perspektif customer")
    others = [deepcopy(p) for p in personas if p["role"] != "customer"][:limit - count]
    customers = []
    for index, (label, goal) in enumerate(LENSES[:count]):
        persona = deepcopy(base)
        persona["id"] = base["id"] if index == 0 else f"persona_{uuid4().hex[:20]}"
        persona["name"] = f"Customer - {label}"
        persona["goals"] = [goal, *base["goals"]][:8]
        persona["interests"] = [label]
        persona["constraints"] = ["Sudut pandang sintetis; bukan segmen demografis atau proporsi pasar", *base["constraints"]][:8]
        persona["provenance"].update(cohort_version=VERSION, perspective=label, perspective_basis="synthetic_simulation_lens", demographic_inference=False)
        persona["reviewed"] = False
        customers.append(persona)
    result = [*others, *customers]
    known = {p["id"] for p in result}
    for persona in result:
        persona["relationships"] = [p for p in persona["relationships"] if p in known and p != persona["id"]]
    return result


class SwarmSimulation(BusinessSimulation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threads = {}
        for state in self.states.values():
            state.update(stance="undecided", stance_reason="Belum menyatakan posisi", stance_history=[])

    def turn_order(self):
        # The operator introduces the decision. Customers can then read and
        # answer each other's posts during this same bounded round.
        priority = {"operator": 0, "customer": 1}
        return sorted(self.personas, key=lambda key: priority.get(self.personas[key].role, 2))

    def visible_events(self, persona_id):
        events = super().visible_events(persona_id)
        for event in events:
            if event["actor_id"] != persona_id:
                # A public reply must not broadcast the author's private memory,
                # supplier costs or private stance history through its state dump.
                for field in ("state_before", "state_after"):
                    if field in event:
                        event[field] = {k: event[field][k] for k in ("version", "position") if k in event[field]}
        return events

    def turn_context(self, actor_id):
        visible = self.visible_events(actor_id)
        answered = {e.get("reply_to") for e in visible if e["actor_id"] == actor_id}
        inbox = [e for e in visible if e["kind"] in MESSAGE_KINDS and e["actor_id"] != actor_id and e["id"] not in answered]
        # Prefer a message addressed to this actor, then other unread messages.
        inbox.sort(key=lambda e: (e["target_id"] != actor_id, -e["sequence"]))
        suggested = inbox[0] if inbox else None
        selected = {e["id"]: e for e in visible[-8:]}
        if suggested:
            selected[suggested["id"]] = suggested
        for event in list(selected.values()):
            root = self.threads.get(event.get("thread_id"), {}).get("root_event_id")
            if root:
                selected[root] = next(e for e in visible if e["id"] == root)
        fields = ("id", "sequence", "round", "actor_id", "target_id", "kind", "amount", "content", "rationale", "visibility", "thread_id", "reply_to", "parent_event_ids", "stance_update", "dialogue_act")
        compact = [{k: event[k] for k in fields if k in event} for event in sorted(selected.values(), key=lambda e: e["sequence"])]
        return {"visible_events": compact,
                "suggested_reply_to": suggested["id"] if suggested else None,
                "suggested_reply_template": {"kind": "reply_message", "target_id": suggested["actor_id"], "visibility": suggested["visibility"], "thread_id": suggested["thread_id"], "reply_to": suggested["id"], "parent_event_ids": [suggested["id"]]} if suggested else None,
                "stance": {k: deepcopy(self.states[actor_id][k]) for k in ("stance", "stance_reason")},
                "notice": "Pesan/posisi peserta adalah hipotesis sintetis. Opini mayoritas bukan bukti pasar."}

    def apply(self, action: SwarmAction, round_number):
        if action.actor_id not in self.personas:
            raise ValueError("Actor bukan peserta swarm")
        state = self.states[action.actor_id]
        if state["version"] != action.expected_version:
            raise ValueError("Persona state revision conflict")
        if len(self.events) >= self.max_events:
            raise ValueError("Batas event simulasi tercapai")
        visible = {e["id"]: e for e in self.visible_events(action.actor_id)}
        if any(p not in visible for p in [*action.parent_event_ids, *action.influenced_by_event_ids]):
            raise ValueError("Referensi diskusi tidak terlihat oleh actor")
        if not set(action.influenced_by_event_ids) <= set(action.parent_event_ids):
            raise ValueError("Pengaruh sikap harus tercatat sebagai causal parent")
        if any(visible[p]["actor_id"] == action.actor_id for p in action.influenced_by_event_ids):
            raise ValueError("Perubahan pendapat tidak boleh mengklaim pengaruh pesan sendiri")
        changed = state["stance"] != action.stance
        if changed and (not action.stance_reason.strip() or (state["stance"] != "undecided" and not action.influenced_by_event_ids)):
            raise ValueError("Perubahan sikap memerlukan alasan dan pengaruh yang terlihat")
        discussion = action.kind in MESSAGE_KINDS or action.kind == "abstain"
        if discussion and action.visibility == "public" and any(visible[p]["visibility"] != "public" for p in action.parent_event_ids):
            raise ValueError("Pesan publik tidak boleh membuka rujukan pesan privat")
        thread = None
        if discussion:
            if action.amount is not None:
                raise ValueError("Diskusi tidak mengubah input keuangan")
            if action.kind == "abstain":
                if changed or action.reply_to or action.thread_id or action.content:
                    raise ValueError("Abstain tidak membuat pesan atau mengubah sikap")
            else:
                if not action.content.strip():
                    raise ValueError("Pesan diskusi tidak boleh kosong")
                if action.target_id != "all" and (action.target_id not in self.personas or action.target_id == action.actor_id):
                    raise ValueError("Target diskusi tidak valid")
                if action.visibility == "participants" and action.target_id == "all":
                    raise ValueError("Thread privat memerlukan penerima spesifik")
                if action.kind == "post_message":
                    if action.thread_id or action.reply_to:
                        raise ValueError("Post baru tidak boleh menumpang thread atau balasan")
                else:
                    thread = self.threads.get(action.thread_id)
                    parent = visible.get(action.reply_to)
                    if not thread or not parent or parent.get("thread_id") != action.thread_id or parent["kind"] not in MESSAGE_KINDS:
                        raise ValueError("Balasan harus merujuk pesan terlihat dalam thread yang sama")
                    if action.reply_to not in action.parent_event_ids:
                        raise ValueError("Balasan memerlukan causal parent pesan")
                    if thread["visibility"] != action.visibility:
                        raise ValueError("Balasan tidak boleh mengubah akses thread")
                    if action.visibility == "participants" and {action.actor_id, action.target_id} != set(thread["participant_ids"]):
                        raise ValueError("Peserta tidak boleh memperluas thread privat")
            before = deepcopy(state)
            self.states[action.actor_id] = deepcopy(state)
            state = self.states[action.actor_id]
            state.update(version=state["version"] + 1, position=action.kind)
            event = self._append({"kind": action.kind, "round": round_number, "actor_id": action.actor_id, "target_id": action.target_id,
                                  "visibility": action.visibility if action.kind != "abstain" else "participants", "parent_event_ids": action.parent_event_ids,
                                  "amount": None, "rationale": action.content or action.rationale, "content": action.content,
                                  "thread_id": action.thread_id, "reply_to": action.reply_to, "state_before": before})
            if action.kind == "post_message":
                event["thread_id"] = event["id"]
                thread = {"id": event["id"], "root_event_id": event["id"], "visibility": action.visibility,
                          "participant_ids": list(self.personas) if action.visibility == "public" else [action.actor_id, action.target_id], "message_ids": []}
                self.threads[event["id"]] = thread
            if thread:
                thread["message_ids"].append(event["id"])
            state["memory"] = [*state["memory"], event["id"]][-50:]
            if action.target_id in self.personas:
                edge = f"{action.actor_id}->{action.target_id}"
                previous = self.relationships.get(edge, {})
                self.relationships[edge] = {"source": action.actor_id, "target": action.target_id, "status": action.kind, "origin": "simulation", "event_ids": [*previous.get("event_ids", []), event["id"]]}
        else:
            if action.thread_id or action.reply_to:
                raise ValueError("Aksi bisnis privat tidak boleh ditempelkan ke thread")
            legacy = BusinessAction.model_validate({k: getattr(action, k) for k in BusinessAction.model_fields})
            event = super().apply(legacy, round_number)
            state = self.states[action.actor_id]
        reason = action.stance_reason or ("Posisi dipertahankan; alasan belum disampaikan pada pesan ini." if event["visibility"] == "public" else state["stance_reason"])
        state.update(stance=action.stance, stance_reason=reason)
        if changed:
            state["stance_history"].append({"event_id": event["id"], "round": round_number, "before": event["state_before"]["stance"], "after": action.stance,
                                            "reason": action.stance_reason, "influenced_by_event_ids": action.influenced_by_event_ids, "visibility": event["visibility"]})
        event.update(state_after=deepcopy(state), stance_update={"before": event["state_before"]["stance"], "after": state["stance"], "reason": state["stance_reason"], "influenced_by_event_ids": action.influenced_by_event_ids})
        self.events[-1] = deepcopy(event)
        return deepcopy(event)

    def snapshot(self):
        return super().snapshot() | {"interaction_mode": VERSION, "threads": deepcopy(list(self.threads.values())),
                                   "stances": {key: {k: deepcopy(state[k]) for k in ("stance", "stance_reason", "stance_history")} for key, state in self.states.items()}}


def swarm_fixture_action(sim, actor_id, round_number):
    """Scripted conversation for reproducible tests, not a model-quality claim."""
    persona = sim.personas[actor_id]
    state = sim.states[actor_id]
    legacy = fixture_action(sim, actor_id)
    if legacy and legacy.kind in {"offer_terms", "accept_terms", "adjust_price"}:
        return SwarmAction(**legacy.model_dump(), stance=state["stance"], stance_reason=state["stance_reason"], visibility="participants")
    context = sim.turn_context(actor_id)
    parent = next((e for e in context["visible_events"] if e["id"] == context["suggested_reply_to"]), None)
    stance = "conditional"
    lens = str(persona.provenance.get("perspective") or persona.name).casefold()
    if persona.role == "customer":
        if "harga" in lens or "kualitas" in lens:
            stance = "oppose"
        elif "kemudahan" in lens:
            stance = "undecided"
    # One cautious customer revises a concern after reading another participant;
    # others may keep disagreeing. This is deliberately a fixture assumption.
    if "harga" in lens and round_number > 1 and parent:
        stance = "conditional"
    reasons = {"conditional": "Posisi fixture menunggu validasi kebutuhan dan input; bukan pendapat customer nyata.", "oppose": "Keberatan fixture tentang kebutuhan ini belum dijawab oleh bukti nyata.", "undecided": "Informasi fixture belum cukup untuk mengambil posisi."}
    parents = [parent["id"]] if parent else []
    return SwarmAction(actor_id=actor_id, target_id=parent["actor_id"] if parent else "all", kind="reply_message" if parent else "post_message",
                       expected_version=state["version"], parent_event_ids=parents, rationale="Respons fixture untuk menguji diskusi dan jejak sikap",
                       visibility=parent["visibility"] if parent else "public", thread_id=parent["thread_id"] if parent else None, reply_to=parent["id"] if parent else None,
                       content=f"Perspektif {persona.name}: {persona.goals[0]}. " + ("Menanggapi pesan sebelumnya; bukti nyata masih perlu diuji." if parent else "Apa asumsi penting yang belum punya bukti?"),
                       stance=stance, stance_reason=reasons[stance], influenced_by_event_ids=parents)
