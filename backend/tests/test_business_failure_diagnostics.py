from types import SimpleNamespace

import pytest

from app.business.call_worker import safe_error


@pytest.mark.parametrize("status,body,kind", [(429, {"message": "rate limit"}, "rate_limit"), (402, {}, "credit_budget"), (401, {}, "authorization"), (400, {"message": "json_schema maxLength not supported"}, "schema_or_parameters"), (503, {}, "provider_unavailable")])
def test_provider_failures_are_classified_without_exporting_raw_messages_or_secrets(status, body, kind):
    class Error(Exception): pass
    error = Error("Do not export request headers or keys")
    error.status_code = status
    error.body = dict(body, private_key="test-secret-never-export", prompt="private request context")
    result = safe_error(error)
    assert result["status_code"] == status and result["failure_kind"] == kind
    assert "test-secret" not in str(result) and "private request" not in str(result)
    assert "message" not in result


def test_numeric_retry_after_is_preserved_without_exposing_other_headers():
    error = Exception("private error")
    error.response = SimpleNamespace(headers={"Retry-After": "30", "Authorization": "secret"})
    assert safe_error(error)["retry_after_seconds"] == 30
    error.response.headers["Retry-After"] = "secret-header-value"
    assert "retry_after_seconds" not in safe_error(error)
    assert "secret" not in str(safe_error(error))
