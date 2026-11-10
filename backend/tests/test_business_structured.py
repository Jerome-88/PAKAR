from copy import deepcopy
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, ValidationError

from app.business.agents import BusinessLLM, validate_finding_references
from app.business.contracts import BusinessAction, Finding, Shock
from app.business.intake import discover
from app.business.simulation import BusinessSimulation
from app.business.structured import action_schema, provider_options, review_schema


def example():
    personas = discover({"industry": "F&B", "region": "Bandung", "target_customer": "Mahasiswa"}, [])[:3]
    return BusinessSimulation("schema-run", personas, {"selling_price": "30000", "variable_cost": "12000", "fixed_cost_monthly": "36000000"})


def test_turn_schema_rejects_stale_versions_and_out_of_scope_references():
    sim = example()
    actor, target = list(sim.personas)[:2]
    action = BusinessAction(actor_id=actor, target_id=target, kind="request_information", expected_version=0, rationale="Tanyakan syarat pasokan").model_dump(mode="json")
    validator = Draft202012Validator(action_schema(sim, actor))
    validator.validate(action)
    for changes in ({"expected_version": 1}, {"actor_id": target}, {"target_id": "private-project-persona"}, {"parent_event_ids": ["another-run:event:1"]}):
        with pytest.raises(ValidationError):
            validator.validate(action | changes)
    # The initial operator cannot offer supplier terms, accept a nonexistent
    # offer, or adjust prices without the user's matching-price scenario.
    for kind in ("offer_terms", "accept_terms", "adjust_price"):
        with pytest.raises(ValidationError):
            validator.validate(action | {"kind": kind})
    sim.reject({"actor_id": actor, "target_id": target}, "invalid proposal", 1)
    Draft202012Validator(action_schema(sim, actor)).validate(action)
    sim.apply(BusinessAction.model_validate(action), 1)
    updated = Draft202012Validator(action_schema(sim, actor))
    with pytest.raises(ValidationError):
        updated.validate(action)
    updated.validate(action | {"expected_version": 1})


def test_user_selected_matching_policy_is_exact_and_observe_does_not_change_price():
    sim = example()
    operator = next(p.id for p in sim.personas.values() if p.role == "operator")
    supplier = next(p.id for p in sim.personas.values() if p.role == "supplier")
    sim.inject(Shock(kind="competitor_price_cut", magnitude_percent=20, effective_round=2, region="Bandung", response_strategy="observe"), 2)
    assert "adjust_price" not in action_schema(sim, operator)["properties"]["kind"]["enum"]
    assert sim.snapshot()["calculation"]["break_even_units_monthly"] == "2000"

    matched = example()
    shock = matched.inject(Shock(kind="competitor_price_cut", magnitude_percent=20, effective_round=2, region="Bandung", response_strategy="match_price"), 2)
    schema = action_schema(matched, operator)
    action = {"actor_id": operator, "target_id": supplier, "kind": "adjust_price", "expected_version": 0, "amount": str(matched.environment["competitor_price"]), "parent_event_ids": [shock["id"]], "rationale": "Apply the user's explicitly selected matching policy"}
    Draft202012Validator(schema).validate(action)
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(action | {"kind": "request_information", "amount": None})
    matched.apply(BusinessAction.model_validate(action), 2)
    assert matched.snapshot()["calculation"]["break_even_units_monthly"] == "3000"
    assert sim.snapshot()["calculation"]["break_even_units_monthly"] == "2000"


def test_review_schema_cannot_promote_claims_or_invent_registry_ids():
    sim = example()
    snapshot = {"claims": [{"id": "approved-claim"}], "personas": [p.model_dump(mode="json") for p in sim.personas.values()]}
    result = sim.snapshot()
    schema = review_schema("Market Agent", snapshot, result, [])
    finding = Finding(id="candidate", title="Demand belum diuji", category="evidence", severity="HIGH", origin="document", author="Market Agent", claim_ids=["approved-claim"], reasoning="Belum ada validasi lapangan", evidence_gaps=["Riset customer"], next_validation="Wawancarai customer", owner_suggestion="Peneliti pasar").model_dump(mode="json")
    validator = Draft202012Validator(schema)
    validator.validate({"findings": [finding], "disagreements": []})
    validate_finding_references(finding, snapshot, result, [])
    for changes in ({"status": "SUPPORTED"}, {"author": "Finance Agent"}, {"claim_ids": ["claim-other-project"]}, {"event_ids": ["other-run:event:1"]}, {"evidence_ids": ["invented-bps-row"]}):
        with pytest.raises(ValidationError):
            validator.validate({"findings": [finding | changes], "disagreements": []})
    assert snapshot["claims"] == [{"id": "approved-claim"}]


@pytest.mark.parametrize("configured,frozen,structured", [(True, None, True), (False, None, False), (False, "json_schema", True), (True, "json_object", False)])
def test_adapter_sends_selected_schema_mode_and_keeps_reported_cost(monkeypatch, configured, frozen, structured):
    captured = {}
    def complete(operation, payload, timeout, **kwargs):
        captured.update(deepcopy(payload["request"]))
        return {"id": "local", "model": "mistralai/mistral-nemo", "usage": {"total_tokens": 20, "cost": 0.000001},
                "finish_reason": "stop", "content": '{"findings":[],"disagreements":[]}'}
    monkeypatch.setattr("app.business.agents.call_worker", complete)
    settings = SimpleNamespace(llm_api_key="test-only", llm_model="mistralai/mistral-nemo", llm_base_url="https://openrouter.ai/api/v1", llm_structured_outputs=configured, provider_timeout_seconds=30)
    llm = BusinessLLM(settings, response_mode=frozen)
    llm.generate("Market Agent", "Review only supplied IDs", {}, response_schema={"type": "object", "properties": {}, "additionalProperties": False})
    assert captured["response_format"]["type"] == ("json_schema" if structured else "json_object")
    assert ("extra_body" in captured) is structured
    assert llm.calls[0]["cost"] == 0.000001
    assert provider_options("https://example.com/openrouter.ai") == {}


def test_provider_price_cap_has_explicit_units_and_cannot_silently_fall_back(monkeypatch):
    monkeypatch.setenv("PAKAR_OPENROUTER_MAX_PRICE", '{"prompt":0.03,"completion":0.03,"request":0}')
    options = provider_options("https://openrouter.ai/api/v1")["extra_body"]["provider"]
    assert options["max_price"] == {"prompt": 0.03, "completion": 0.03, "request": 0}
    assert options["allow_fallbacks"] is False
    routed = provider_options("https://openrouter.ai/api/v1", sort="latency")["extra_body"]["provider"]
    assert routed["sort"] == "latency" and routed["max_price"] == options["max_price"]
    monkeypatch.setenv("PAKAR_OPENROUTER_MAX_PRICE", '{"prompt":NaN,"completion":0.03}')
    with pytest.raises(ValueError):
        provider_options("https://openrouter.ai/api/v1")


def test_qwen_bounded_json_disables_reasoning_without_losing_price_route(monkeypatch):
    monkeypatch.setenv("PAKAR_OPENROUTER_PROVIDER_ORDER", '["primeintellect/fp8"]')
    monkeypatch.setenv("PAKAR_OPENROUTER_MAX_PRICE", '{"prompt":0.012,"completion":0.113,"request":0}')
    body = provider_options("https://openrouter.ai/api/v1", model="qwen/qwen3.6-35b-a3b")["extra_body"]
    assert body["reasoning"] == {"enabled": False}
    assert body["provider"]["order"] == ["primeintellect/fp8"]
    assert body["provider"]["allow_fallbacks"] is False
    assert body["provider"]["require_parameters"] is True
    assert body["provider"]["max_price"]["completion"] == 0.113
    assert "reasoning" not in provider_options("https://openrouter.ai/api/v1", model="openai/gpt-oss-20b")["extra_body"]
    assert provider_options("http://127.0.0.1/v1", model="qwen/qwen3.6-35b-a3b") == {}


def test_specialist_process_limit_caps_slow_sync_sdk_at_sixty_seconds(monkeypatch):
    captured = []
    def complete(operation, payload, timeout, **kwargs):
        captured.append(timeout)
        return {"usage": None, "finish_reason": "stop", "content": '{"findings":[],"disagreements":[]}'}
    monkeypatch.setattr("app.business.agents.call_worker", complete)
    settings = SimpleNamespace(llm_api_key="test-only", llm_model="local", llm_base_url="http://127.0.0.1:1/v1", llm_structured_outputs=False, provider_timeout_seconds=120)
    BusinessLLM(settings, max_seconds=300).generate("Risk Agent", "local-test", {})
    assert captured == [60]


def test_explicit_provider_route_preserves_caps_and_blocks_fallbacks(monkeypatch):
    monkeypatch.setenv("PAKAR_OPENROUTER_PROVIDER_ORDER", '["Parasail"]')
    monkeypatch.setenv("PAKAR_OPENROUTER_MAX_PRICE", '{"prompt":0.03,"completion":0.03,"request":0}')
    routed = provider_options("https://openrouter.ai/api/v1", sort="latency")["extra_body"]["provider"]
    assert routed["order"] == ["Parasail"] and routed["allow_fallbacks"] is False
    assert routed["require_parameters"] is True and routed["max_price"]["completion"] == 0.03
    assert provider_options("http://127.0.0.1:1/v1") == {}
    for invalid in ('[]', '{}', '[""]', '[4]', 'null'):
        monkeypatch.setenv("PAKAR_OPENROUTER_PROVIDER_ORDER", invalid)
        with pytest.raises(ValueError):
            provider_options("https://openrouter.ai/api/v1")
