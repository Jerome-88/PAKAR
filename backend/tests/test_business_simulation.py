from copy import deepcopy
from decimal import Decimal

import pytest

from app.business.contracts import BusinessAction, Shock
from app.business.intake import discover
from app.business.simulation import BusinessSimulation, financials, fixture_action


CONTEXT = {"industry": "F&B", "region": "Jakarta", "target_customer": "Pekerja kantor"}
VALUES = {"selling_price": "30000", "variable_cost": "12000", "fixed_cost_monthly": "36000000", "volume_monthly": None}


def make_sim(run_id="test", values=None):
    return BusinessSimulation(run_id, discover(CONTEXT, []), values or VALUES)


def test_supplier_offer_requires_explicit_acceptance_and_preserves_causal_chain():
    sim = make_sim()
    shock = sim.inject(Shock(kind="supplier_cost_increase", magnitude_percent=50, region="Jakarta", effective_round=2), 2)
    offer = sim.apply(fixture_action(sim, "persona-supplier"), 2)
    assert sim.values["variable_cost"] == "12000"
    assert shock["id"] in offer["parent_event_ids"]
    accepted = sim.apply(fixture_action(sim, "persona-operator"), 2)
    assert offer["id"] in accepted["parent_event_ids"]
    assert sim.values["variable_cost"] == "18000.0"
    assert accepted["state_after"]["version"] == accepted["state_before"]["version"] + 1
    assert sim.snapshot()["calculation"]["break_even_units_monthly"] == "3000"
    assert accepted["evidence_status"] == "SYNTHETIC_HYPOTHESIS"


def test_private_interaction_cannot_be_used_as_customer_evidence():
    sim = make_sim()
    offer = sim.apply(fixture_action(sim, "persona-supplier"), 1)
    before = sim.snapshot()
    action = BusinessAction(actor_id="persona-customer", target_id="persona-operator", kind="express_concern", expected_version=0, parent_event_ids=[offer["id"]], rationale="Tidak boleh membaca pesan supplier privat")
    with pytest.raises(ValueError, match="Causal parent"):
        sim.apply(action, 1)
    assert sim.snapshot() == before


def test_private_cost_shock_is_not_shared_with_customer_persona():
    sim = make_sim()
    event = sim.inject(Shock(kind="supplier_cost_increase", magnitude_percent=50, region="Jakarta", effective_round=2), 2)
    assert event["id"] in {e["id"] for e in sim.visible_events("persona-supplier")}
    assert event["id"] not in {e["id"] for e in sim.visible_events("persona-customer")}
    assert "supplier_cost" not in sim.visible_environment("persona-customer")


def test_stale_version_wrong_role_and_foreign_run_events_do_not_mutate_state():
    sim = make_sim()
    action = fixture_action(sim, "persona-supplier")
    sim.apply(action, 1)
    before = sim.snapshot()
    with pytest.raises(ValueError, match="revision"):
        sim.apply(action, 1)
    with pytest.raises(ValueError, match="supplier"):
        sim.apply(action.model_copy(update={"actor_id": "persona-customer"}), 1)
    with pytest.raises(ValueError, match="Causal parent"):
        sim.apply(action.model_copy(update={"expected_version": 1, "parent_event_ids": ["other:run:1"]}), 1)
    assert sim.snapshot() == before


def test_competitor_price_cut_does_not_change_own_price_without_strategy():
    sim = make_sim()
    sim.inject(Shock(kind="competitor_price_cut", magnitude_percent=20, effective_round=2, region="Jakarta"), 2)
    assert sim.values["selling_price"] == "30000"
    assert Decimal(sim.environment["competitor_price"]) == 24000
    with pytest.raises(ValueError, match="strategi"):
        sim.apply(BusinessAction(actor_id="persona-operator", target_id="persona-customer", kind="adjust_price", expected_version=0, amount=24000, rationale="Menurunkan harga tanpa izin strategi"), 2)


def test_match_price_is_conditional_and_baseline_remains_immutable():
    baseline, scenario = make_sim("baseline"), make_sim("scenario")
    before = deepcopy(baseline.snapshot())
    scenario.inject(Shock(kind="competitor_price_cut", magnitude_percent=20, response_strategy="match_price", effective_round=2, region="Jakarta"), 2)
    scenario.apply(BusinessAction(actor_id="persona-operator", target_id="persona-customer", kind="adjust_price", expected_version=0, amount=Decimal("24000.0"), rationale="Respons match price dipilih pengguna"), 2)
    assert scenario.snapshot()["calculation"]["break_even_units_monthly"] == "3000"
    assert baseline.snapshot() == before


def test_calculator_keeps_missing_unknown_and_handles_non_positive_margin():
    assert financials({})["break_even_units_monthly"] is None
    assert financials(VALUES)["profit_monthly"] is None
    assert financials(dict(VALUES, variable_cost="30000"))["status"] == "NON_POSITIVE_MARGIN"
    assert financials(dict(VALUES, fixed_cost_monthly="36000001"))["break_even_units_monthly"] == "2001"
    with pytest.raises(ValueError):
        financials(dict(VALUES, variable_cost="NaN"))


def test_event_budget_does_not_publish_partial_state():
    sim = make_sim()
    sim.max_events = 1
    sim.apply(fixture_action(sim, "persona-supplier"), 1)
    before = sim.snapshot()
    with pytest.raises(ValueError, match="Batas event"):
        sim.apply(fixture_action(sim, "persona-operator"), 1)
    assert sim.snapshot() == before


def test_shock_expires_without_rewriting_past_decisions():
    sim = make_sim()
    sim.inject(Shock(kind="supplier_cost_increase", magnitude_percent=50, region="Jakarta", effective_round=2, duration_rounds=1), 2)
    sim.apply(fixture_action(sim, "persona-supplier"), 2)
    sim.apply(fixture_action(sim, "persona-operator"), 2)
    sim.expire_shock(3)
    assert sim.environment["supplier_cost"] == "12000"
    assert Decimal(sim.values["variable_cost"]) == 18000


def test_claim_extraction_never_treats_foreign_currency_or_liters_as_idr_units():
    from app.documents import ExtractedDocument, TextSegment
    from app.business.intake import extract_claims
    for text in ("Harga jual USD 20 per unit.", "Biaya tetap 30000 per bulan.", "Volume 100 liter per bulan."):
        extracted = ExtractedDocument(text, (TextSegment(text, 0, len(text)),))
        claim = extract_claims("doc-currency", extracted)[0]
        assert claim["value"] is None and claim["unit"] is None
    text = "Harga jual Rp30.000 per unit."
    claim = extract_claims("doc-idr", ExtractedDocument(text, (TextSegment(text, 0, len(text)),)))[0]
    assert claim["value"] == "30000" and claim["unit"] == "IDR/unit"
