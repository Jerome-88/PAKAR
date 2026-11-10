import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.business.budget import BudgetExceeded
from app.business.evidence import BPSEvidence


INDICATOR = {"region": "DKI Jakarta", "domain": "3100", "variable": "144", "period_code": "124", "period_label": "2024", "unit": "Rupiah",
             "selection": {"vervar": "9", "turvar": "163", "turtahun": "0"}}
PAYLOAD = {"status": "OK", "var": [{"val": 144, "unit": "Rupiah", "label": "Pengeluaran per kapita per bulan"}],
           "vervar": [{"val": 9, "label": "Jumlah"}], "turvar": [{"val": 163, "label": "Jumlah"}],
           "tahun": [{"val": 124, "label": "2024"}], "turtahun": [{"val": 0, "label": "Tahunan"}], "datacontent": {"91441631240": 2764456}}


def configure(monkeypatch, indicators=None, payload=None):
    monkeypatch.setenv("BPS_API_KEY", "test-bps-secret")
    monkeypatch.setenv("PAKAR_BPS_INDICATORS", json.dumps(indicators or [INDICATOR]))
    requests = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return json.dumps(payload or PAYLOAD).encode()[:size]
    def open_request(request, **kwargs):
        requests.append(request)
        return Response()
    monkeypatch.setattr("app.business.evidence.build_opener", lambda *args: SimpleNamespace(open=open_request))
    return requests


def test_explicit_bps_dimensions_keep_historical_context_partial_with_raw_scale(monkeypatch):
    calls = configure(monkeypatch)
    source = BPSEvidence()
    evidence = source.retrieve("DKI Jakarta")[0]
    assert evidence["value"] == "2764456" and evidence["status"] == "PARTIAL"
    assert evidence["claim_support"] == "NOT_ASSESSED"
    assert evidence["interpretation"]["multiplier"] == 1
    assert evidence["freshness"]["status"] == "historical"
    assert evidence["selected_observation"]["labels"]["tahun"] == "2024"
    assert evidence["source_sha256"]
    assert "test-bps-secret" not in json.dumps(evidence)
    assert source.retrieve("DKI Jakarta")[0]["cache_hit"]
    assert source.retrieve("Jakarta")[0]["status"] == "UNAVAILABLE"
    assert source.retrieve("Bandung")[0]["status"] == "UNAVAILABLE"
    assert len(calls) == 1


@pytest.mark.parametrize("field,change", [("tahun", [{"val": 124, "label": "2023"}]), ("var", [{"val": 144, "unit": "Ribu Rupiah"}]), ("datacontent", {"91441631240": "NaN"}), ("turvar", []), ("datacontent", {})])
def test_mismatched_units_periods_missing_dimensions_or_nonfinite_values_do_not_become_evidence(monkeypatch, field, change):
    payload = deepcopy(PAYLOAD)
    payload[field] = change
    configure(monkeypatch, payload=payload)
    result = BPSEvidence().retrieve("DKI Jakarta")[0]
    assert result["status"] == "UNAVAILABLE" and result["value"] is None


def test_cache_includes_geography_and_curated_interpretation_and_limits_matching_sources(monkeypatch):
    entries = [dict(INDICATOR, region="Other province") for _ in range(4)] + [INDICATOR]
    calls = configure(monkeypatch, entries)
    source = BPSEvidence()
    assert source.retrieve("DKI Jakarta")[0]["value"] == "2764456"
    monkeypatch.setenv("PAKAR_BPS_INDICATORS", json.dumps([dict(INDICATOR, unit="Ribu Rupiah")]))
    result = source.retrieve("DKI Jakarta")[0]
    assert result["status"] == "UNAVAILABLE" and not result.get("cache_hit")
    assert len(calls) == 2


def test_bps_budget_exhaustion_is_not_swallowed_as_a_retriable_source_outage(monkeypatch):
    configure(monkeypatch)
    def expired(): raise BudgetExceeded("deadline")
    with pytest.raises(BudgetExceeded):
        BPSEvidence().retrieve("DKI Jakarta", deadline=SimpleNamespace(remaining=expired))


def test_invalid_catalog_and_credential_bearing_source_link_are_safe(monkeypatch):
    configure(monkeypatch, [dict(INDICATOR, source_url="https://webapi.bps.go.id/key/test-bps-secret")])
    assert "test-bps-secret" not in BPSEvidence().retrieve("DKI Jakarta")[0]["url"]
    monkeypatch.setenv("PAKAR_BPS_INDICATORS", '{"region":"DKI Jakarta"}')
    assert BPSEvidence().retrieve("DKI Jakarta")[0]["status"] == "UNAVAILABLE"


@pytest.mark.parametrize("published,expected", [("2794485", "CONFLICTING"), ("2764456", "PARTIAL")])
def test_publication_comparison_keeps_both_values_and_never_verifies_business_claim(monkeypatch, published, expected):
    comparison = {"region": "DKI Jakarta", "period_label": "2024", "unit": "Rupiah", "selection": INDICATOR["selection"],
        "source_url": "https://jakarta.bps.go.id/id/publication/2025/05/28/official.html", "source_sha256": "a" * 64,
        "value": published, "table": "2.1", "pdf_page": 31}
    configure(monkeypatch, [dict(INDICATOR, publication_comparison=comparison)])
    row = BPSEvidence().retrieve("DKI Jakarta")[0]
    assert row["status"] == expected and row["claim_support"] == "NOT_ASSESSED"
    assert row["selected_observation"]["raw_value"] == 2764456
    assert row["reconciliation"]["api_value"] == "2764456"
    assert row["reconciliation"]["publication_value"] == published
    assert row["value"] == (None if expected == "CONFLICTING" else "2764456")


def test_publication_scope_mismatch_cannot_silently_replace_an_observation(monkeypatch):
    configure(monkeypatch, [dict(INDICATOR, publication_comparison={"selection": INDICATOR["selection"], "region": "Bandung"})])
    row = BPSEvidence().retrieve("DKI Jakarta")[0]
    assert row["status"] == "UNAVAILABLE" and row["value"] is None
