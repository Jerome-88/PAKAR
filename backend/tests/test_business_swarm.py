from copy import deepcopy

import pytest

from app.business.contracts import QuickAnalysisInput, SwarmAction
from app.business.preparation import contextual_personas
from app.business.structured import swarm_action_schema
from app.business.swarm import SwarmSimulation, expand_customer_cohort, swarm_fixture_action

CONTEXT = {"name": "Kedai sintetis", "industry": "Kedai kopi", "region": "DKI Jakarta", "target_customer": "Pekerja kantor", "decision_question": "Apa yang perlu diuji sebelum ekspansi kedai?"}
VALUES = {"selling_price": "30000", "variable_cost": "12000", "fixed_cost_monthly": "36000000", "volume_monthly": None}


def make_sim():
    base = contextual_personas(CONTEXT, [{"id": "source", "quote": "Supplier memasok bahan; kompetitor menurunkan harga."}])
    personas = expand_customer_cohort(base, 4, 8)
    return SwarmSimulation("swarm-test", personas, VALUES, 50)


def action(sim, actor, **kwargs):
    values = {"actor_id": actor, "target_id": "all", "kind": "post_message", "expected_version": sim.states[actor]["version"], "rationale": "Hipotesis simulasi untuk diuji", "content": "Bagaimana kebutuhan pelanggan dibuktikan?", "stance": sim.states[actor]["stance"], "stance_reason": sim.states[actor]["stance_reason"]}
    return SwarmAction(**(values | kwargs))


def reply(sim, actor, parent, **kwargs):
    return action(sim, actor, kind="reply_message", target_id=parent["actor_id"], thread_id=parent["thread_id"], reply_to=parent["id"], visibility=parent["visibility"], parent_event_ids=[parent["id"]], **kwargs)


def test_cohort_has_distinct_ids_lenses_and_no_inferred_demographics():
    sim = make_sim()
    customers = [p for p in sim.personas.values() if p.role == "customer"]
    assert len(customers) == 4 and len({p.id for p in customers}) == 4
    assert len({p.goals[0] for p in customers}) == 4
    assert all(p.provenance["demographic_inference"] is False and not p.reviewed for p in customers)
    assert sim.snapshot()["calculation"]["profit_monthly"] is None


def test_reply_template_matches_visible_parent_without_inventing_message_content():
    sim = make_sim()
    operator = next(p.id for p in sim.personas.values() if p.role == "operator")
    customers = [p.id for p in sim.personas.values() if p.role == "customer"]
    root = sim.apply(action(sim, operator), 1)
    parent = sim.apply(reply(sim, customers[0], root), 1)
    context = sim.turn_context(customers[1])
    template = context["suggested_reply_template"]
    assert template == {"kind": "reply_message", "target_id": customers[0], "visibility": "public", "thread_id": root["thread_id"], "reply_to": parent["id"], "parent_event_ids": [parent["id"]]}
    assert "content" not in template and "stance" not in template
    accepted = sim.apply(action(sim, customers[1], **template), 1)
    assert accepted["reply_to"] == parent["id"] and accepted["target_id"] == customers[0]
    private = sim.apply(action(sim, operator, target_id=customers[0], visibility="participants"), 1)
    outsider = sim.turn_context(customers[2])
    assert outsider["suggested_reply_to"] != private["id"]
    assert private["id"] not in str(outsider["suggested_reply_template"])


def test_public_customer_discussion_records_reply_and_stance_causality_without_changing_finances():
    sim = make_sim()
    first, second = [p.id for p in sim.personas.values() if p.role == "customer"][:2]
    root = sim.apply(action(sim, first, stance="oppose", stance_reason="Harga perlu diuji"), 1)
    response = sim.apply(reply(sim, second, root, content="Perlu membandingkan manfaat sebelum memutuskan.", stance="conditional", stance_reason="Menunggu bukti manfaat", influenced_by_event_ids=[root["id"]]), 1)
    revised = sim.apply(reply(sim, first, response, stance="conditional", stance_reason="Pertanyaan manfaat perlu diuji lebih dulu", influenced_by_event_ids=[response["id"]]), 2)
    assert revised["thread_id"] == root["id"]
    assert len(sim.threads[root["id"]]["message_ids"]) == 3
    assert sim.states[first]["stance_history"][-1]["before"] == "oppose"
    assert sim.states[first]["stance_history"][-1]["influenced_by_event_ids"] == [response["id"]]
    assert sim.values == VALUES


def test_private_threads_do_not_leak_messages_states_or_references_to_other_customers():
    sim = make_sim()
    first, second, outsider = [p.id for p in sim.personas.values() if p.role == "customer"][:3]
    private = sim.apply(action(sim, first, target_id=second, visibility="participants", content="Kendala privat sintetis", stance="oppose", stance_reason="Kendala privat"), 1)
    assert private["id"] not in {e["id"] for e in sim.visible_events(outsider)}
    before = sim.snapshot()
    with pytest.raises(ValueError):
        sim.apply(reply(sim, outsider, private), 1)
    assert sim.snapshot() == before
    with pytest.raises(ValueError, match="privat"):
        sim.apply(action(sim, first, parent_event_ids=[private["id"]]), 2)
    # A later public statement contains a complete owner audit state, but the
    # prompt seen by others gets only public event metadata, not that state dump.
    public = sim.apply(action(sim, first, content="Saya masih butuh informasi publik.", stance_reason=""), 2)
    seen = next(e for e in sim.visible_events(outsider) if e["id"] == public["id"])
    assert "stance_history" not in seen["state_before"] and "memory" not in seen["state_after"]
    assert "Kendala privat" not in str(sim.turn_context(outsider))


def test_cross_thread_reply_and_visibility_changes_are_rejected_atomically():
    sim = make_sim()
    first, second = list(sim.personas)[:2]
    one = sim.apply(action(sim, first), 1)
    two = sim.apply(action(sim, second), 1)
    before = sim.snapshot()
    with pytest.raises(ValueError, match="thread yang sama"):
        sim.apply(reply(sim, first, two, **{}).model_copy(update={"thread_id": one["thread_id"]}), 2)
    with pytest.raises(ValueError, match="akses thread"):
        sim.apply(reply(sim, first, two).model_copy(update={"visibility": "participants"}), 2)
    assert sim.snapshot() == before


def test_stance_changes_need_reasons_and_visible_external_influence():
    sim = make_sim()
    first, second = list(sim.personas)[:2]
    initial = sim.apply(action(sim, first, stance="oppose", stance_reason="Perlu bukti"), 1)
    response = sim.apply(reply(sim, second, initial), 1)
    before = sim.snapshot()
    with pytest.raises(ValueError, match="alasan"):
        sim.apply(reply(sim, first, response, stance="support", stance_reason=""), 2)
    with pytest.raises(ValueError, match="alasan"):
        sim.apply(reply(sim, first, response, stance="support", stance_reason="Mengubah posisi"), 2)
    with pytest.raises(ValueError, match="sendiri"):
        sim.apply(action(sim, first, parent_event_ids=[initial["id"]], influenced_by_event_ids=[initial["id"]]), 2)
    assert sim.snapshot() == before


def test_opinions_cannot_change_financial_inputs_but_valid_business_negotiation_can():
    sim = make_sim()
    supplier = next(p.id for p in sim.personas.values() if p.role == "supplier")
    operator = next(p.id for p in sim.personas.values() if p.role == "operator")
    before = sim.snapshot()
    with pytest.raises(ValueError, match="keuangan"):
        sim.apply(action(sim, supplier, amount="15000"), 1)
    assert sim.snapshot() == before
    offered = sim.apply(action(sim, supplier, kind="offer_terms", target_id=operator, amount="15000", content="", visibility="participants"), 1)
    sim.apply(action(sim, operator, kind="accept_terms", target_id=supplier, parent_event_ids=[offered["id"]], content="", visibility="participants"), 2)
    assert sim.snapshot()["calculation"]["break_even_units_monthly"] == "2400"
    assert sim.snapshot()["calculation"]["profit_monthly"] is None


def test_turn_schema_only_offers_visible_message_and_thread_references():
    sim = make_sim()
    first, second, outsider = list(sim.personas)[:3]
    secret = sim.apply(action(sim, first, target_id=second, visibility="participants"), 1)
    public = sim.apply(action(sim, second), 1)
    props = swarm_action_schema(sim, outsider)["properties"]
    assert secret["id"] not in props["reply_to"]["enum"]
    assert public["id"] in props["reply_to"]["enum"]
    assert props["amount"] == {"type": "null"}  # outsider is a customer here


def test_fixture_discussion_reuses_threads_and_keeps_multiple_stances():
    sim = make_sim()
    for round_number in range(1, 4):
        for actor in sim.turn_order():
            sim.apply(swarm_fixture_action(sim, actor, round_number), round_number)
    result = sim.snapshot()
    assert any(e["kind"] == "reply_message" and sim.personas[e["actor_id"]].role == "customer" and sim.personas[e["target_id"]].role == "customer" for e in result["events"])
    assert any(h["before"] == "oppose" and h["after"] == "conditional" for s in result["stances"].values() for h in s["stance_history"])
    assert all(p["visibility"] == "public" for p in result["threads"])
    assert len({s["stance"] for s in result["stances"].values()}) >= 2
    assert result["calculation"]["profit_monthly"] is None


def test_default_swarm_configuration_fits_cohort_and_rejects_impossible_limits():
    config = QuickAnalysisInput(expected_revision=1)
    assert config.interaction_mode == "swarm" and config.customer_count == 4 and config.rounds == 3
    with pytest.raises(ValueError):
        QuickAnalysisInput(expected_revision=1, customer_count=6, max_personas=4)


def test_quiet_round_waits_for_both_start_and_expiry_of_scheduled_shocks():
    from app.business.swarm import is_quiet_round
    sim = make_sim()
    for actor in sim.turn_order():
        sim.apply(action(sim, actor, kind="abstain", content=""), 1)
    assert is_quiet_round(sim, 0, 1, 5)
    assert not is_quiet_round(sim, 0, 1, 5, {"effective_round": 2, "duration_rounds": 2})
    assert not is_quiet_round(sim, 0, 3, 5, {"effective_round": 2, "duration_rounds": 2})
    assert is_quiet_round(sim, 0, 4, 5, {"effective_round": 2, "duration_rounds": 2})
