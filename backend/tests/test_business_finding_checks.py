import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.business.agents import validate_finding_references
from app.business.contracts import Finding
from app.business.finding_checks import arithmetic_issues, project_valid_findings
from app.business.tables import business_analyses
from test_business_api import create_project, make_app, prepare, register, wait


@pytest.mark.parametrize("text,bad", [
    ("Pendapatan per unit (Rp30,000) di bawah biaya variabel (Rp12,000).", True),
    ("Revenue Rp30.000 below variable cost Rp12.000", True),
    ("Revenue Rp30.000 above variable cost Rp12.000", False),
    ("Revenue Rp1.200 less than variable cost Rp1.200", True),
    ("Rp1,25 lebih besar dari Rp2,50", True),
    ("Tidak benar bahwa Rp30.000 di bawah Rp12.000", False),
    ("Jika harga Rp30.000 di bawah biaya Rp12.000, periksa asumsi.", False),
    ("Biaya Rp30.000/bulan di bawah Rp12.000/unit", False),
    ("Rp30.000 berbeda dari USD 3, di bawah Rp12.000", False),
    ("Bandingkan Rp30.000,0 di bawah Rp12.000", False),
])
def test_explicit_comparison_guard_is_narrow_and_respects_units_negation_and_formatting(text, bad):
    assert bool(arithmetic_issues({"reasoning": text})) is bad


def invalid_finding():
    return Finding(id="bad-arithmetic", author="Market Agent", title="Incorrect loss on every unit", category="document", severity="HIGH", origin="simulation", reasoning="Pendapatan per unit (Rp30,000) di bawah biaya variabel (Rp12,000).", calculation_ids=["calc"], evidence_gaps=["Review input"], next_validation="Check input", owner_suggestion="Analyst").model_dump(mode="json")


def test_new_findings_cannot_pass_reference_validation_with_false_explicit_arithmetic():
    finding = invalid_finding()
    with pytest.raises(ValueError, match="aritmetika"):
        validate_finding_references(finding, {"claims": [], "personas": []}, {"events": [], "calculation": {"id": "calc"}}, [])


def test_read_projection_is_idempotent_and_preserves_raw_registry():
    invalid = invalid_finding()
    valid = dict(invalid, id="valid", reasoning="Demand remains unknown")
    raw = {"findings": [invalid, valid], "limitations": [], "provenance": {}, "disagreements": [{"author": "Risk Agent", "summary": "bad-arithmetic: Incorrect loss on every unit"}, {"author": "Finance Agent", "summary": "bad-arithmetic-2: unrelated"}]}
    before = deepcopy(raw)
    result = project_valid_findings(raw)
    assert raw == before and [f["id"] for f in result["findings"]] == ["valid"]
    assert result["finding_validation"]["rejected"][0]["id"] == "bad-arithmetic"
    assert result["disagreements"][0]["held_finding_ids"] == ["bad-arithmetic"]
    assert "bukan dukungan temuan" in result["disagreements"][0]["summary"]
    assert "held_finding_ids" not in result["disagreements"][1]
    assert project_valid_findings(result) == result


def test_existing_bad_registry_is_held_from_api_report_and_export_without_rewriting_baseline(tmp_path, database_url):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        project = prepare(client, create_project(client))
        response = client.post(f"/api/v1/business/projects/{project['id']}/analyses", json={"expected_revision": project["revision"], "engine": "fixture", "rounds": 2})
        row = wait(client, response.json()["id"])
        raw = deepcopy(row["result"])
        bad = invalid_finding()
        bad["calculation_ids"] = [raw["simulation"]["calculation"]["id"]]
        raw["findings"].append(bad)
        with app.state.repository.engine.begin() as db:
            db.execute(update(business_analyses).where(business_analyses.c.id == row["id"]).values(result=raw))
        before = json.dumps(raw, sort_keys=True)
        base = f"/api/v1/business/analyses/{row['id']}"
        view = client.get(base).json()
        assert all(f["id"] != bad["id"] for f in view["result"]["findings"])
        assert view["result"]["finding_validation"]["rejected"][0]["id"] == bad["id"]
        assert all(f["id"] != bad["id"] for f in client.get(base + "/findings").json()["items"])
        report = client.get(base + "/report").json()
        assert len(report["sections"]) == 8 and all(f["id"] != bad["id"] for f in report["findings"])
        assert any("bad-arithmetic" in line for line in report["limitations"])
        exported = client.get(base + "/export").text
        assert bad["title"] not in exported and "bad-arithmetic" in exported
        with app.state.repository.engine.connect() as db:
            saved = db.execute(select(business_analyses.c.result).where(business_analyses.c.id == row["id"])).scalar_one()
        assert json.dumps(saved, sort_keys=True) == before
