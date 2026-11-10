"""Server-authoritative state transitions for synthetic business interactions.

The same reducer validates fixture actions and structured actions proposed by live
personas. A platform post is never treated as a transaction or observed evidence.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_CEILING

from .contracts import BusinessAction, Persona, Shock


def number(value) -> Decimal | None:
    if value is None:
        return None
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("Nilai harus berupa angka terbatas non-negatif")
    return result


def financials(values: dict) -> dict:
    """Only IDR/unit, IDR/month and units/month inputs reach this calculator."""
    price = number(values.get("selling_price"))
    cost = number(values.get("variable_cost"))
    fixed = number(values.get("fixed_cost_monthly"))
    volume = number(values.get("volume_monthly"))
    missing = [key for key in ("selling_price", "variable_cost", "fixed_cost_monthly") if values.get(key) is None]
    margin = price - cost if price is not None and cost is not None else None
    breakeven = (fixed / margin).to_integral_value(rounding=ROUND_CEILING) if fixed is not None and margin is not None and margin > 0 else None
    profit = margin * volume - fixed if margin is not None and volume is not None and fixed is not None else None
    return {
        "id": "unit-economics-v1", "method_version": "pakar-decimal-v1",
        "inputs": {key: str(value) if value is not None else None for key, value in values.items()},
        "contribution_margin": str(margin) if margin is not None else None,
        "break_even_units_monthly": format(breakeven, "f") if breakeven is not None else None,
        "profit_monthly": str(profit) if profit is not None else None,
        "margin_unit": "IDR/unit", "profit_unit": "IDR/month", "missing_inputs": missing,
        "formulas": {"contribution_margin": "selling_price - variable_cost", "break_even_units_monthly": "ceil(fixed_cost_monthly / contribution_margin)", "profit_monthly": "contribution_margin * volume_monthly - fixed_cost_monthly"},
        "status": "MISSING_INPUTS" if missing else "NON_POSITIVE_MARGIN" if margin is not None and margin <= 0 else "COMPUTED_CONDITIONAL_ON_INPUTS",
    }


class BusinessSimulation:
    def __init__(self, run_id: str, personas: list[dict], values: dict, max_events: int = 80):
        validated = [Persona.model_validate(item) for item in personas]
        if len({p.id for p in validated}) != len(validated):
            raise ValueError("Persona ID harus unik")
        self.run_id = run_id
        self.personas = {p.id: p for p in validated if p.active}
        self.initial_values = deepcopy(values)
        self.values = deepcopy(values)
        self.max_events = max_events
        self.events: list[dict] = []
        self.states = {p.id: {"version": 0, "position": "initial", "memory": [], "offered_cost": None, "selling_price": values.get("selling_price") if p.role == "operator" else None} for p in self.personas.values()}
        self.shock: dict | None = None
        self.relationships = {}
        for persona in self.personas.values():
            for target in persona.relationships:
                if target in self.personas:
                    self.relationships[f"{persona.id}->{target}"] = {"source": persona.id, "target": target, "status": "proposed_context", "origin": "synthetic_hypothesis", "event_ids": []}
        self.environment = {"supplier_cost": values.get("variable_cost"), "competitor_price": None, "regulation": None}

    def visible_events(self, persona_id: str) -> list[dict]:
        return [deepcopy(e) for e in self.events if e.get("visibility") == "public" or persona_id in {e.get("actor_id"), e.get("target_id")}]

    def visible_environment(self, persona_id: str) -> dict:
        result = {key: value for key, value in self.environment.items() if key != "supplier_cost"}
        if self.personas[persona_id].role in {"supplier", "operator"}:
            result["supplier_cost"] = self.environment["supplier_cost"]
        return deepcopy(result)

    def _append(self, item: dict) -> dict:
        if len(self.events) >= self.max_events:
            raise ValueError("Batas event simulasi tercapai")
        event = {"id": f"{self.run_id}:event:{len(self.events) + 1}", "sequence": len(self.events) + 1, "origin": "simulation", "evidence_status": "SYNTHETIC_HYPOTHESIS", **item}
        self.events.append(event)
        return deepcopy(event)

    def inject(self, shock: Shock, round_number: int) -> dict:
        if self.shock is not None:
            raise ValueError("Satu run MVP hanya menerima satu shock")
        if round_number != shock.effective_round:
            raise ValueError("Shock hanya boleh diterapkan pada ronde yang ditentukan")
        self.shock = shock.model_dump(mode="json")
        factor = shock.magnitude_percent / 100
        previous = deepcopy(self.environment)
        if shock.kind == "supplier_cost_increase":
            base = number(self.initial_values.get("variable_cost"))
            self.environment["supplier_cost"] = str(base * (1 + factor)) if base is not None else None
        elif shock.kind == "competitor_price_cut":
            # A proxy comparator is explicitly a scenario assumption, not a real observed competitor price.
            base = number(self.initial_values.get("selling_price"))
            self.environment["competitor_price"] = str(base * (1 - factor)) if base is not None else None
        else:
            self.environment["regulation"] = shock.description or "Perubahan regulasi hipotetis perlu ditinjau"
        private = shock.kind == "supplier_cost_increase"
        target = next((p.id for p in self.personas.values() if p.role == "supplier"), "no_eligible_supplier") if private else "all"
        shown_keys = {"supplier_cost"} if private else {"competitor_price", "regulation"}
        return self._append({"kind": "shock", "round": round_number, "actor_id": "environment", "target_id": target, "visibility": "participants" if private else "public", "parent_event_ids": [], "rationale": shock.description or shock.kind, "environment_before": {k: previous[k] for k in shown_keys}, "environment_after": {k: self.environment[k] for k in shown_keys}, "shock": self.shock})

    def expire_shock(self, round_number: int) -> dict | None:
        if not self.shock or self.shock.get("expired") or round_number < self.shock["effective_round"] + self.shock["duration_rounds"]:
            return None
        before = deepcopy(self.environment)
        self.environment = {"supplier_cost": self.initial_values.get("variable_cost"), "competitor_price": None, "regulation": None}
        self.shock["expired"] = True
        shock_event = next(e for e in self.events if e["kind"] == "shock")
        shown_keys = set(shock_event["environment_after"])
        return self._append({"kind": "shock_expired", "round": round_number, "actor_id": "environment", "target_id": shock_event["target_id"], "visibility": shock_event["visibility"], "parent_event_ids": [shock_event["id"]], "rationale": "Durasi shock selesai; keputusan persona yang telah diterapkan tetap tercatat.", "environment_before": {k: before[k] for k in shown_keys}, "environment_after": {k: self.environment[k] for k in shown_keys}})

    def apply(self, action: BusinessAction, round_number: int) -> dict:
        if action.actor_id not in self.personas or action.target_id not in self.personas:
            raise ValueError("Actor dan target harus persona aktif dalam run ini")
        if action.actor_id == action.target_id:
            raise ValueError("Interaksi harus ditujukan ke persona lain")
        actor = self.personas[action.actor_id]
        state = self.states[actor.id]
        if state["version"] != action.expected_version:
            raise ValueError("Persona state revision conflict")
        visible = {e["id"]: e for e in self.visible_events(actor.id)}
        if any(parent not in visible for parent in action.parent_event_ids):
            raise ValueError("Causal parent harus event yang diterima actor dalam run yang sama")
        parents = [visible[parent] for parent in action.parent_event_ids]
        before = deepcopy(state)
        new_state = deepcopy(state)
        next_values = deepcopy(self.values)
        if action.kind == "offer_terms":
            if actor.role != "supplier" or self.personas[action.target_id].role != "operator" or action.amount is None:
                raise ValueError("Penawaran biaya hanya dari supplier ke operator dengan amount positif")
            new_state.update(position="terms_offered", offered_cost=str(action.amount))
        elif action.kind == "accept_terms":
            if actor.role != "operator" or self.personas[action.target_id].role != "supplier":
                raise ValueError("Penerimaan penawaran hanya dari operator ke supplier")
            offers = [e for e in parents if e["kind"] == "offer_terms" and e["actor_id"] == action.target_id and e["target_id"] == actor.id]
            if not offers:
                raise ValueError("Penerimaan membutuhkan parent penawaran yang ditujukan ke operator")
            offer = offers[-1]
            if any(e["kind"] == "accept_terms" and offer["id"] in e["parent_event_ids"] for e in self.events):
                raise ValueError("Penawaran sudah diterima")
            latest = next((e for e in reversed(self.events) if e["kind"] == "offer_terms" and e["actor_id"] == action.target_id and e["target_id"] == actor.id), None)
            if not latest or latest["id"] != offer["id"]:
                raise ValueError("Penawaran telah digantikan revisi terbaru")
            next_values["variable_cost"] = offer["amount"]
            new_state["position"] = "terms_accepted"
        elif action.kind == "adjust_price":
            if actor.role != "operator" or action.amount is None:
                raise ValueError("Harga bisnis hanya dapat diubah operator dengan amount positif")
            # Never derive a matching strategy just from competitor behavior.
            if not self.shock or self.shock["kind"] != "competitor_price_cut" or self.shock["response_strategy"] != "match_price":
                raise ValueError("Perubahan harga membutuhkan strategi match_price yang dipilih pengguna")
            if self.environment["competitor_price"] is None or action.amount != Decimal(self.environment["competitor_price"]):
                raise ValueError("Harga harus sesuai parameter strategi scenario")
            next_values["selling_price"] = str(action.amount)
            new_state.update(position="price_adjusted", selling_price=str(action.amount))
        else:
            if action.amount is not None:
                raise ValueError("Aksi ini tidak menerima amount")
            new_state["position"] = action.kind
        new_state["version"] += 1
        event_id = f"{self.run_id}:event:{len(self.events) + 1}"
        new_state["memory"] = [*state["memory"], event_id][-50:]
        event = self._append({"kind": action.kind, "round": round_number, "actor_id": actor.id, "target_id": action.target_id, "visibility": "participants", "parent_event_ids": action.parent_event_ids, "amount": str(action.amount) if action.amount is not None else None, "rationale": action.rationale, "state_before": before, "state_after": new_state})
        self.states[actor.id] = new_state
        self.values = next_values
        edge_id = f"{actor.id}->{action.target_id}"
        previous = self.relationships.get(edge_id, {})
        self.relationships[edge_id] = {"source": actor.id, "target": action.target_id, "status": action.kind, "origin": "simulation", "event_ids": [*previous.get("event_ids", []), event["id"]]}
        return event

    def reject(self, raw: dict, reason: str, round_number: int) -> dict:
        return self._append({"kind": "action_rejected", "round": round_number, "actor_id": str(raw.get("actor_id", "unknown")), "target_id": str(raw.get("target_id", "unknown")), "visibility": "participants", "parent_event_ids": [], "rationale": reason[:1500], "state_unchanged": True})

    def snapshot(self) -> dict:
        return {"run_id": self.run_id, "states": deepcopy(self.states), "relationships": list(deepcopy(self.relationships).values()), "events": deepcopy(self.events), "environment": deepcopy(self.environment), "calculation": financials(self.values), "initial_calculation": financials(self.initial_values)}


def fixture_action(sim: BusinessSimulation, persona_id: str) -> BusinessAction | None:
    """Scripted adapter for tests/demo; deliberately never described as live AI."""
    persona = sim.personas[persona_id]
    operator = next((p for p in sim.personas.values() if p.role == "operator"), None)
    customer = next((p for p in sim.personas.values() if p.role == "customer"), None)
    supplier = next((p for p in sim.personas.values() if p.role == "supplier"), None)
    visible = sim.visible_events(persona_id)
    parents = [e["id"] for e in visible[-3:]]
    if persona.role == "supplier" and operator and sim.environment["supplier_cost"] is not None:
        kind, target, amount = "offer_terms", operator.id, sim.environment["supplier_cost"]
    elif persona.role == "operator" and supplier and any(e["kind"] == "offer_terms" for e in visible):
        if sim.shock and not sim.shock.get("expired") and sim.shock["response_strategy"] == "match_price" and sim.environment["competitor_price"] is not None:
            kind, target, amount = "adjust_price", (customer or supplier).id, sim.environment["competitor_price"]
        else:
            offers = [e for e in visible if e["kind"] == "offer_terms" and e["actor_id"] == supplier.id]
            latest = offers[-1]
            if any(e["kind"] == "accept_terms" and latest["id"] in e["parent_event_ids"] for e in sim.events):
                kind, target, amount = "request_information", supplier.id, None
            else:
                kind, target, amount, parents = "accept_terms", supplier.id, None, [latest["id"]]
    elif operator and persona.id != operator.id:
        kind, target, amount = "express_concern", operator.id, None
    elif customer:
        kind, target, amount = "request_information", customer.id, None
    else:
        return None
    return BusinessAction(actor_id=persona_id, target_id=target, kind=kind, expected_version=sim.states[persona_id]["version"], parent_event_ids=parents, amount=amount, rationale=f"Hipotesis fixture: {persona.goals[0]}. Respons ini membutuhkan validasi lapangan.")
