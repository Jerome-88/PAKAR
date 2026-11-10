import pytest

from app.config import Settings
from app.business.structured import provider_options
from app.oasis_direct import DirectOasisEngine
from app.business.groq_limits import complete, retry_delay, is_groq_reasoning_model
from types import SimpleNamespace
from app.llm_access import require_allowed_llm_endpoint


@pytest.mark.parametrize("endpoint", [None, "https://openrouter.ai/api/v1", "https://api.groq.com.example/v1", "http://api.groq.com/openai/v1", "https://user@api.groq.com/v1", "https://api.groq.com:444/v1"])
def test_groq_lock_blocks_other_endpoints_before_dispatch(monkeypatch, tmp_path, endpoint):
    monkeypatch.setenv("PAKAR_ALLOWED_LLM_HOSTS", "api.groq.com")
    with pytest.raises(ValueError, match="endpoint blocked"):
        require_allowed_llm_endpoint(endpoint)
    with pytest.raises(ValueError, match="endpoint blocked"):
        Settings.load({"TESTING": True, "LLM_BASE_URL": endpoint})
    monkeypatch.setenv("LLM_BASE_URL", endpoint or "")
    with pytest.raises(ValueError, match="endpoint blocked"):
        DirectOasisEngine(tmp_path, tmp_path / "data")._environment()


def test_groq_lock_accepts_official_https_only(monkeypatch):
    monkeypatch.setenv("PAKAR_ALLOWED_LLM_HOSTS", "api.groq.com")
    require_allowed_llm_endpoint("https://api.groq.com/openai/v1")


def test_provider_diagnostics_never_publish_response_text_or_credentials():
    from app.business.groq_limits import failure_details
    error = SimpleNamespace(status_code=400, body={"error": "private-key-and-generated-output violates maxItems"})
    assert failure_details(error) == {"status_code": 400, "failure_terms": ["maxitems"]}


def test_groq_analysis_defaults_allow_throttled_runs_but_keep_explicit_limits():
    from app.business.service import BusinessService
    from app.business.contracts import QuickAnalysisInput
    service = object.__new__(BusinessService)
    service.settings = SimpleNamespace(llm_base_url="https://api.groq.com/openai/v1")
    payload = {"expected_revision": 1}
    assert service.analysis_options(payload, QuickAnalysisInput)["max_seconds"] == 900
    assert service.analysis_options(payload, QuickAnalysisInput)["max_tokens"] == 180000
    explicit = service.analysis_options(payload | {"max_seconds": 60, "max_tokens": 8000}, QuickAnalysisInput)
    assert (explicit["max_seconds"], explicit["max_tokens"]) == (60, 8000)
    assert service.analysis_options(payload | {"engine": "fixture"}, QuickAnalysisInput)["max_seconds"] == 300
    service.settings = SimpleNamespace(llm_base_url="https://openrouter.ai/api/v1")
    assert service.analysis_options(payload, QuickAnalysisInput)["max_tokens"] == 300000
    assert service.analysis_options(payload, QuickAnalysisInput)["max_cost_usd"] == "0.10"
    assert service.analysis_options(payload, QuickAnalysisInput)["max_seconds"] == 900
    assert service.analysis_options(payload | {"max_tokens": 8000, "max_cost_usd": "0.01"}, QuickAnalysisInput)["max_tokens"] == 8000
    assert payload == {"expected_revision": 1}


@pytest.mark.parametrize("route_name,schema_name", [("start", "AnalysisInput"), ("quick_start", "QuickAnalysisInput")])
def test_api_preserves_unset_limits_for_groq_defaults(monkeypatch, route_name, schema_name):
    from app.business import api, contracts
    from app.business.service import BusinessService
    schema = getattr(contracts, schema_name)
    business = object.__new__(BusinessService)
    business.settings = SimpleNamespace(llm_base_url="https://api.groq.com/openai/v1")
    def normalize(project, owner, payload, key):
        return business.analysis_options(payload, schema)
    monkeypatch.setattr(api, "owner", lambda _: "owner")
    monkeypatch.setattr(api, "service", lambda _: SimpleNamespace(**{route_name: normalize}))
    route = getattr(api, route_name)
    result = route(None, "project", schema(expected_revision=1), "key")
    assert (result["max_seconds"], result["max_tokens"]) == (900, 180000)
    result = route(None, "project", schema(expected_revision=1, max_seconds=60, max_tokens=8000), "key")
    assert (result["max_seconds"], result["max_tokens"]) == (60, 8000)


def test_new_scenario_uses_current_model_without_relabeling_baseline():
    from copy import deepcopy
    from app.business.service import BusinessService
    from app.business.information import POLICY
    baseline = {"id": "baseline", "project_id": "project", "baseline_id": None, "status": "completed",
                "result": {"simulation": {"events": []}}, "input_snapshot": {
                    "config": {"engine": "oasis", "rounds": 4}, "context": {"region": "Jakarta"},
                    "information_policy": {"version": POLICY}, "model": "old-model", "limitations": []}}
    # Use the same policy discriminator as frozen production snapshots.
    from app.business.information import freeze
    freeze(baseline["input_snapshot"], "Public test concept")
    original = deepcopy(baseline)
    service = object.__new__(BusinessService)
    service.settings = SimpleNamespace(llm_model="openai/gpt-oss-20b", llm_structured_outputs=True)
    service.analysis_view = lambda *_: baseline
    service.repository = SimpleNamespace(enqueue=lambda project, owner, snapshot, key, source: {"input_snapshot": snapshot})
    service._spawn = lambda _: None
    result = service.scenario("baseline", "owner", {"effective_round": 2, "region": "Jakarta"})
    assert result["input_snapshot"]["model"] == "openai/gpt-oss-20b"
    assert result["input_snapshot"]["response_mode"] == "json_schema"
    assert baseline == original


@pytest.mark.parametrize("operation", ["llm_completion", "openrouter_credit"])
def test_worker_blocks_paid_provider_without_network(monkeypatch, operation):
    import io
    import json
    from app.business import call_worker
    monkeypatch.setenv("PAKAR_ALLOWED_LLM_HOSTS", "api.groq.com")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"operation": operation, "payload": {"base_url": "https://openrouter.ai/api/v1"}})))
    output = io.StringIO()
    monkeypatch.setattr("sys.stdout", output)
    call_worker.main()
    result = json.loads(output.getvalue())
    assert result["ok"] is False
    assert result["error_type"] == "ValueError"


@pytest.fixture(autouse=True)
def prevent_loading_developer_env(monkeypatch):
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)


def test_groq_endpoint_selects_free_ai_key_instead_of_old_provider_key(monkeypatch):
    monkeypatch.setenv("FREE_AI_KEY", "test-groq-key")
    monkeypatch.setenv("LLM_API_KEY", "test-old-provider-key")
    settings = Settings.load({"TESTING": True, "LLM_BASE_URL": "https://api.groq.com/openai/v1"})
    assert settings.llm_api_key == "test-groq-key"
    # Groq must not receive OpenRouter routing/pricing parameters.
    monkeypatch.setenv("PAKAR_OPENROUTER_MAX_PRICE", "invalid-unrelated-config")
    assert provider_options(settings.llm_base_url) == {}


def test_free_key_never_overrides_other_endpoints_or_explicit_key(monkeypatch):
    monkeypatch.setenv("FREE_AI_KEY", "test-groq-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-fallback")
    monkeypatch.setenv("OPENAI_KEY", "test-openai-legacy-fallback")
    monkeypatch.setenv("LLM_API_KEY", "test-original-key")
    for endpoint in ("https://openrouter.ai/api/v1", "https://api.openai.com/v1", "https://api.groq.com.example/v1"):
        assert Settings.load({"TESTING": True, "LLM_BASE_URL": endpoint}).llm_api_key == "test-original-key"
    assert Settings.load({"TESTING": True, "LLM_BASE_URL": "https://api.groq.com/openai/v1", "LLM_API_KEY": "explicit-key"}).llm_api_key == "explicit-key"


def test_standard_groq_configuration_still_works_without_alias(monkeypatch):
    monkeypatch.setenv("FREE_AI_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "test-standard-groq-key")
    assert Settings.load({"TESTING": True, "LLM_BASE_URL": "https://api.groq.com/openai/v1"}).llm_api_key == "test-standard-groq-key"


def test_oasis_child_gets_groq_key_without_mutating_parent_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("FREE_AI_KEY", "test-groq-key")
    monkeypatch.setenv("LLM_API_KEY", "test-old-provider-key")
    environment = DirectOasisEngine(tmp_path, tmp_path / "data")._environment()
    assert environment["LLM_API_KEY"] == "test-groq-key"
    assert environment["LLM_MODEL_NAME"] == "openai/gpt-oss-20b"
    import os
    assert os.environ["LLM_API_KEY"] == "test-old-provider-key"


@pytest.mark.parametrize("status,endpoint,attempt,header,expected", [
    (429, "https://api.groq.com/openai/v1", 0, "2.5", 3.0),
    (429, "https://api.groq.com/openai/v1", 3, "2", None),
    (500, "https://api.groq.com/openai/v1", 0, "2", None),
    (429, "https://openrouter.ai/api/v1", 0, "2", None),
    (429, "https://api.groq.com/openai/v1", 0, "nan", None),
    (429, "https://api.groq.com/openai/v1", 0, "90", None),
])
def test_only_bounded_groq_rate_rejections_are_waited(status, endpoint, attempt, header, expected):
    error = SimpleNamespace(status_code=status, response=SimpleNamespace(headers={"retry-after": header}))
    assert retry_delay(error, endpoint, attempt) == expected


def test_rejected_request_wait_does_not_repeat_successful_generation(monkeypatch):
    from app.business import groq_limits
    sleeps = []
    monkeypatch.setattr(groq_limits.time, "sleep", sleeps.append)
    class RateRejected(Exception):
        status_code = 429
        response = SimpleNamespace(headers={"retry-after": "2"})
    calls = []
    def operation():
        calls.append(1)
        if len(calls) == 1:
            raise RateRejected()
        return {"accepted": True}
    assert complete(operation, "https://api.groq.com/openai/v1") == {"accepted": True}
    assert len(calls) == 2
    assert sleeps == [2.5]


def test_groq_reasoning_options_do_not_change_other_models_or_providers():
    assert is_groq_reasoning_model("https://api.groq.com/openai/v1", "openai/gpt-oss-20b")
    assert not is_groq_reasoning_model("https://openrouter.ai/api/v1", "openai/gpt-oss-20b")
    assert not is_groq_reasoning_model("https://api.groq.com/openai/v1", "another-model")


def test_async_wait_preserves_cancellation_and_does_not_retry_success(monkeypatch):
    import asyncio
    from app.business import groq_limits
    waits, calls = [], []
    async def sleep(delay):
        waits.append(delay)
    monkeypatch.setattr(groq_limits.asyncio, "sleep", sleep)
    class RateRejected(Exception):
        status_code = 429
        response = SimpleNamespace(headers={"retry-after": "1"})
    async def operation():
        calls.append(1)
        if len(calls) == 1:
            raise RateRejected()
        return "completed"
    assert asyncio.run(groq_limits.complete_async(operation, "https://api.groq.com/openai/v1")) == "completed"
    assert len(calls) == 2 and waits == [1.5]
    async def cancelled():
        raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(groq_limits.complete_async(cancelled, "https://api.groq.com/openai/v1"))
    assert waits == [1.5]


@pytest.mark.parametrize("standard_key,legacy_key,expected", [
    ("test-openai-standard", "test-openai-legacy", "test-openai-standard"),
    ("", "test-openai-legacy", "test-openai-legacy"),
])
def test_openai_key_aliases_are_fallbacks_only(monkeypatch, standard_key, legacy_key, expected):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", standard_key)
    monkeypatch.setenv("OPENAI_KEY", legacy_key)
    assert Settings.load({"TESTING": True, "LLM_BASE_URL": "https://api.openai.com/v1"}).llm_api_key == expected
