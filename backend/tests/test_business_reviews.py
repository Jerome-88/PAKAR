import json
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier, Event, Lock
from types import SimpleNamespace

import pytest

from app.business.agents import BusinessLLM
from app.business.budget import BudgetExceeded, RunCancelled
from app.business.contracts import Finding
from app.business.reviews import ROLES, compact_context, run_paired_reviews, fit_groq_context, GROQ_INSTRUCTION
from app.business.agents import SYSTEM_PROMPT
from app.business.structured import response_format
from app.business.groq_limits import request_tokens


def example():
    snapshot = {"context": {"region": "DKI Jakarta"}, "personas": [{"id": "p1", "name": "Operator", "role": "operator"}],
                "claims": [{"id": "c1", "normalized_text": "Demand unknown", "quote": "Demand unknown", "evidence_status": "UNAVAILABLE", "source": {"locator": {"page": 1}}}]}
    simulation = {"id": "sim", "events": [{"id": "e1", "kind": "express_concern", "rationale": "Hypothesis", "parent_event_ids": []}], "calculation": {"id": "calc", "profit_monthly": None}}
    evidence = [{"id": "bps", "status": "PARTIAL", "claim_support": "NOT_ASSESSED", "value": "2764456", "unit": "Rupiah", "observations": {"raw": 2764456}}]
    seed = Finding(id="seed", author="Finance Agent", title="Missing demand", category="document", severity="HIGH", origin="document", reasoning="Demand is not measured", evidence_gaps=["Customer research"], next_validation="Interview customers", owner_suggestion="Analyst").model_dump(mode="json")
    return snapshot, simulation, evidence, [seed]


def candidate(role):
    return Finding(id="model-placeholder", author=role, title=role, category="evidence", severity="MEDIUM", origin="evidence", claim_ids=["c1"], evidence_ids=["bps"], reasoning="Contextual partial data is not customer demand", evidence_gaps=["Business validation"], next_validation="Check applicability", owner_suggestion="Analyst").model_dump(mode="json")


@pytest.mark.parametrize("ceiling", [6500, 7500])
def test_groq_review_fits_request_limit_without_changing_sources_or_reference_scope(monkeypatch, ceiling):
    monkeypatch.setenv("PAKAR_GROQ_REQUEST_TOKEN_LIMIT", str(ceiling))
    snapshot, simulation, evidence, peers = example()
    snapshot["claims"] = [{**deepcopy(snapshot["claims"][0]), "id": f"source-{i}", "quote": ("Evidence remains a hypothesis requiring validation. " * 20), "normalized_text": ("Evidence remains a hypothesis requiring validation. " * 20)} for i in range(35)]
    original = deepcopy((snapshot, simulation, evidence, peers))
    payload, schema = compact_context(ROLES[0], snapshot, simulation, evidence, peers)
    payload, schema = fit_groq_context(ROLES[0], snapshot, simulation, evidence, peers, payload, schema)
    messages = [{"role": "system", "content": SYSTEM_PROMPT + GROQ_INSTRUCTION}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}]
    assert request_tokens(messages, response_format("pakar_review", schema), 1800) <= ceiling
    assert payload["context_window"]["claims_supplied"] < 35
    assert payload["context_window"]["claims_total"] == 35
    assert {c["id"] for c in payload["claims"]} == set(schema["properties"]["findings"]["items"]["properties"]["claim_ids"]["items"]["enum"])
    assert (snapshot, simulation, evidence, peers) == original


def test_irreducible_groq_request_fails_each_role_once_without_dispatch(monkeypatch):
    snapshot, simulation, evidence, findings = example()
    monkeypatch.setenv("PAKAR_GROQ_REQUEST_TOKEN_LIMIT", "1000")
    class Model:
        cancelled = None
        settings = SimpleNamespace(llm_base_url="https://api.groq.com/openai/v1", llm_model="openai/gpt-oss-20b")
        def generate(self, *args, **kwargs):
            raise AssertionError("An oversized request must not be dispatched")
    result = run_paired_reviews(Model(), snapshot, simulation, evidence, findings, lambda: 100)
    assert len(result["failures"]) == 4
    assert {failure["role"] for failure in result["failures"]} == set(ROLES)


def test_two_review_waves_keep_peer_scope_and_merge_order_when_finance_finishes_first():
    snapshot, simulation, evidence, findings = example()
    before = deepcopy((snapshot, simulation, evidence))
    barrier, lock = Barrier(2), Lock()
    active, peak, contexts = [0], [0], {}
    class Model:
        cancelled = None
        def generate(self, role, instruction, payload, **kwargs):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
                contexts[role] = deepcopy(payload)
            barrier.wait(timeout=2)
            if role in (ROLES[0], ROLES[2]): time.sleep(0.03)
            with lock: active[0] -= 1
            assert kwargs["max_output_tokens"] == 1100
            return {"findings": [candidate(role)], "disagreements": ["A peer hypothesis still needs validation"]}
    result = run_paired_reviews(Model(), snapshot, simulation, evidence, findings, lambda: 100)
    assert not result["failures"] and peak[0] == 2
    assert [f["author"] for f in findings[1:]] == list(ROLES)
    assert len({f["id"] for f in findings}) == 5
    assert contexts[ROLES[0]]["peer_findings"] == contexts[ROLES[1]]["peer_findings"]
    assert len(contexts[ROLES[2]]["peer_findings"]) == 3
    assert contexts[ROLES[2]]["peer_findings"] == contexts[ROLES[3]]["peer_findings"]
    assert [d["author"] for d in result["disagreements"]] == list(ROLES)
    assert (snapshot, simulation, evidence) == before


@pytest.mark.parametrize("invalid", ["foreign_ref", "wrong_role", "overlong", "too_many"])
def test_invalid_first_wave_result_is_not_merged_and_risk_still_runs(invalid):
    snapshot, simulation, evidence, findings = example()
    budgets = []
    class Model:
        cancelled = None
        def generate(self, role, instruction, payload, **kwargs):
            budgets.append(kwargs["call_seconds"])
            finding = candidate(role)
            if role == ROLES[0]:
                if invalid == "foreign_ref": finding["claim_ids"] = ["other-project"]
                if invalid == "wrong_role": finding["author"] = ROLES[3]
                if invalid == "overlong": finding["reasoning"] = "x" * 901
                if invalid == "too_many": return {"findings": [finding, finding], "disagreements": []}
            return {"findings": [finding], "disagreements": []}
    result = run_paired_reviews(Model(), snapshot, simulation, evidence, findings, lambda: 20)
    assert [f["role"] for f in result["failures"]] == [ROLES[0]]
    assert [f["author"] for f in findings[1:]] == list(ROLES[1:])
    assert sorted(budgets) == [10, 10, 20, 20]


def test_compact_context_preserves_values_uncertainty_and_causal_ids_with_explicit_window():
    snapshot, simulation, evidence, findings = example()
    snapshot["claims"] += [{"id": f"later-{i}", "normalized_text": "supplied hypothesis"} for i in range(40)]
    payload, schema = compact_context(ROLES[3], snapshot, simulation, evidence, findings)
    assert payload["claims"][0]["quote"] == snapshot["claims"][0]["quote"]
    assert payload["evidence"][0]["value"] == "2764456"
    assert payload["evidence"][0]["claim_support"] == "NOT_ASSESSED"
    assert "observations" not in payload["evidence"][0]
    assert payload["events"][0]["parent_event_ids"] == []
    ids = schema["properties"]["findings"]["items"]["properties"]["claim_ids"]["items"]["enum"]
    assert len(ids) == 35 and "later-39" not in ids
    assert payload["context_window"]["claims_total"] == 41


def test_cancelled_review_propagates_without_promoting_other_partial_outputs():
    snapshot, simulation, evidence, findings = example()
    class Model:
        cancelled = None
        def generate(self, *a, **k): raise RunCancelled("cancelled")
    with pytest.raises(RunCancelled):
        run_paired_reviews(Model(), snapshot, simulation, evidence, findings, lambda: 20)


def test_concurrent_llm_admission_cannot_spend_one_token_remainder_twice(monkeypatch):
    entered, release = Event(), Event()
    calls = []
    def complete(*args, **kwargs):
        calls.append(args)
        entered.set()
        assert release.wait(2)
        return {"usage": None, "content": '{"findings":[],"disagreements":[]}', "finish_reason": "stop"}
    monkeypatch.setattr("app.business.agents.call_worker", complete)
    settings = SimpleNamespace(llm_api_key="local-only", llm_model="local", llm_base_url="http://127.0.0.1:1", llm_structured_outputs=False, provider_timeout_seconds=10)
    llm = BusinessLLM(settings, max_tokens=3000)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(llm.generate, ROLES[0], "review", {})
        assert entered.wait(2)
        try:
            with pytest.raises(BudgetExceeded):
                pool.submit(llm.generate, ROLES[1], "review", {}).result(timeout=2)
        finally: release.set()
        first.result(timeout=2)
    assert len(calls) == 1 and llm.tokens <= 3000


def test_serial_transport_retains_frozen_waves_and_divides_time_for_queued_roles():
    snapshot, simulation, evidence, findings = example()
    snapshot["config"] = {"review_concurrency": 1}
    budgets = []
    class Model:
        cancelled = None
        def generate(self, role, instruction, payload, **kwargs):
            budgets.append(kwargs["call_seconds"])
            return {"findings": [], "disagreements": []}
    result = run_paired_reviews(Model(), snapshot, simulation, evidence, findings, lambda: 20)
    assert not result["failures"] and budgets == [5, 5, 10, 10]


def test_expired_explicit_resume_does_not_mark_inherited_roles_as_failed():
    snapshot, simulation, evidence, findings = example()
    snapshot["review_roles"] = [ROLES[0], ROLES[2]]
    def expired():
        raise BudgetExceeded("No work time remains")
    model = SimpleNamespace(cancelled=None)
    result = run_paired_reviews(model, snapshot, simulation, evidence, findings, expired)
    assert [failure["role"] for failure in result["failures"]] == [ROLES[0], ROLES[2]]
    assert result["waves"] == []


def test_reactive_context_compacts_exact_duplicates_without_changing_source_registry():
    snapshot, simulation, evidence, findings = example()
    simulation["discussion_policy"] = "reactive-v2"
    event = simulation["events"][0]
    event.update(content="Hypothesis", stance_update={"reason": "Needs evidence"}, state_after={"version": 1, "stance": "conditional", "stance_reason": "Needs evidence"})
    before = deepcopy((snapshot, simulation))
    context, schema = compact_context(ROLES[0], snapshot, simulation, evidence, findings)
    assert context["claims"][0]["quote"] == snapshot["claims"][0]["quote"]
    assert "normalized_text" not in context["claims"][0]
    assert context["events"][0]["content"] == "Hypothesis" and "rationale" not in context["events"][0]
    assert context["events"][0]["stance_update"]["reason"] == "Needs evidence"
    assert "state_after" not in context["events"][0]
    assert (snapshot, simulation) == before


def test_reactive_reviews_shrink_context_before_bounded_admission_and_keep_source_ids(monkeypatch):
    snapshot, simulation, evidence, findings = example()
    simulation["discussion_policy"] = "reactive-v2"
    simulation["events"] = [{"id": f"event-{i}", "kind": "post_message", "rationale": "Distinct scenario discussion " + str(i) + " x" * 600, "parent_event_ids": []} for i in range(12)]
    original = deepcopy(simulation)
    contexts = []
    def completion(operation, payload, timeout, **kwargs):
        contexts.append(json.loads(payload["request"]["messages"][-1]["content"]))
        return {"usage": {"total_tokens": 200}, "content": '{"findings":[],"disagreements":[]}', "finish_reason": "stop"}
    monkeypatch.setattr("app.business.agents.call_worker", completion)
    settings = SimpleNamespace(llm_api_key="local-only", llm_model="local", llm_base_url="http://127.0.0.1:1", llm_structured_outputs=True, provider_timeout_seconds=10)
    llm = BusinessLLM(settings, max_tokens=12000)
    snapshot["config"] = {"review_concurrency": 1}
    result = run_paired_reviews(llm, snapshot, simulation, evidence, findings, lambda: 30)
    assert not result["failures"] and len(contexts) == 4
    assert any(context["context_window"].get("budget_window") for context in contexts)
    assert all(context["context_window"]["events_supplied"] < 12 for context in contexts)
    assert all(event["id"] in {e["id"] for e in original["events"]} for context in contexts for event in context["events"])
    assert simulation == original and llm.tokens == 800


def test_serial_review_packs_next_request_after_settlement_with_frozen_peer_wave():
    snapshot, simulation, evidence, findings = example()
    snapshot["config"] = {"review_concurrency": 1}
    simulation["discussion_policy"] = "reactive-v2"
    seen = []
    class Model:
        cancelled = None
        structured_outputs = True
        limit = 60000
        tokens = 0
        lock = Lock()
        def generate(self, role, instruction, payload, **kwargs):
            with self.lock:
                self.tokens = self.limit
            time.sleep(0.02)
            seen.append((role, payload["context_window"].get("budget_window", False), deepcopy(payload["peer_findings"])))
            with self.lock:
                self.tokens = 1000
            return {"findings": [], "disagreements": []}
    result = run_paired_reviews(Model(), snapshot, simulation, evidence, findings, lambda: 30)
    assert not result["failures"] and [x[0] for x in seen] == list(ROLES)
    assert not any(x[1] for x in seen), "An unsettled earlier reservation must not unnecessarily shrink the next request"
    assert seen[0][2] == seen[1][2]
