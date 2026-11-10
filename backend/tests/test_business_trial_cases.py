"""Exercise the actual example inputs through intake, jobs, report and scenarios.

Arithmetic expectations are independent conditional checks, not LLM quality scores.
All inference is fixture/local; no developer credentials or BPS calls are used.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from test_business_api import make_app, register, wait


ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "docs/evaluation/business-cases.v0.json").read_text(encoding="utf-8"))["cases"]
EXAMPLES = json.loads((ROOT / "frontend/src/pages/Business/businessExamples.json").read_text(encoding="utf-8"))
SCENARIOS = {
    "coffee-dki-v0": ({"kind": "competitor_price_cut", "magnitude_percent": 20, "response_strategy": "match_price"}, "3000"),
    "supplier-bandung-v0": ({"kind": "supplier_cost_increase", "magnitude_percent": 50}, "12000"),
    "services-dki-v0": ({"kind": "regulation_change", "description": "Asumsi peninjauan kewajiban operasional; bukan pernyataan hukum berlaku."}, "300"),
}


def prepare_case(client, case):
    response = client.post("/api/v1/business/projects", json=case["context"])
    assert response.status_code == 201, response.text
    project = response.json()
    base = f"/api/v1/business/projects/{project['id']}"
    response = client.post(base + "/documents", files=[("files", ("synthetic-trial.txt", case["proposal"].encode(), "text/plain"))])
    assert response.status_code == 201, response.text
    project = response.json()
    response = client.post(base + "/claims/approve", json={"expected_revision": project["revision"]})
    assert response.status_code == 200, response.text
    project = response.json()
    for role in case["roles_to_review"]:
        response = client.post(base + f"/personas?expected_revision={project['revision']}", json={"id": "server-assigned", "name": f"{role} sintetis", "role": role, "goals": ["Periksa asumsi pada dokumen; tidak mengarang demand nyata."], "reviewed": True})
        assert response.status_code == 201, response.text
        project = client.get(base).json()
    return project


def start_case(client, project):
    return client.post(f"/api/v1/business/projects/{project['id']}/analyses", json={"expected_revision": project["revision"], "engine": "fixture", "rounds": 2, "max_personas": 4})


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_examples_preserve_unknown_demand_source_trails_and_conditional_scenario_math(tmp_path, database_url, case):
    example = next(e for e in EXAMPLES if e["id"] == case["id"])
    assert example["context"] == case["context"] and example["proposal"] == case["proposal"]
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        # Fail instead of accidentally using an external source in this suite.
        app.state.business.evidence.retrieve = lambda *a, **k: (_ for _ in ()).throw(AssertionError("No external evidence calls allowed"))
        project = prepare_case(client, case)
        response = start_case(client, project)
        assert response.status_code == 202, response.text
        baseline = wait(client, response.json()["id"])
        assert baseline["status"] == "completed"
        calculation = baseline["result"]["simulation"]["calculation"]
        assert calculation["break_even_units_monthly"] == case["expected_calculations"]["baseline_break_even_units_monthly"]
        assert calculation["profit_monthly"] is None
        assert baseline["input_snapshot"]["values"]["volume_monthly"] is None
        assert baseline["result"]["provenance"]["execution_kind"] == "fixture"
        assert baseline["result"]["evidence"][0]["status"] == "UNAVAILABLE"
        report = client.get(f"/api/v1/business/analyses/{baseline['id']}/report").json()
        assert len(report["sections"]) == 8
        assert all(f["status"] == "NEEDS_VALIDATION" for f in report["findings"])
        assert all(c["quote"] and c["document_id"] and c["locator"] for c in report["assumptions"])
        assert any("Profit belum diketahui" in line for line in report["limitations"])
        shock, expected = SCENARIOS[case["id"]]
        response = client.post(f"/api/v1/business/analyses/{baseline['id']}/scenarios", json={"shock": {**shock, "effective_round": 2, "duration_rounds": 1, "region": case["context"]["region"]}})
        assert response.status_code == 202, response.text
        scenario = wait(client, response.json()["id"])
        assert scenario["status"] == "completed"
        comparison = client.get(f"/api/v1/business/analyses/{scenario['id']}/comparison").json()
        assert next(m for m in comparison["metrics"] if m["metric"] == "break_even_units_monthly")["after"] == expected
        assert next(m for m in comparison["metrics"] if m["metric"] == "profit_monthly")["status"] == "UNKNOWN"
        assert client.get(f"/api/v1/business/analyses/{baseline['id']}").json()["result"] == baseline["result"]


def test_missing_price_stays_unknown_in_report_instead_of_becoming_a_forecast(tmp_path, database_url):
    case = {**CASES[0], "proposal": "Pengelola kedai melayani customer.\nBiaya variabel Rp12.000 per unit.\nBiaya tetap Rp36.000.000 per bulan.\nHarga jual dan volume penjualan belum ditentukan."}
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        response = start_case(client, prepare_case(client, case))
        assert response.status_code == 202, response.text
        row = wait(client, response.json()["id"])
        assert row["status"] == "completed"
        calc = row["result"]["simulation"]["calculation"]
        assert calc["inputs"]["selling_price"] is None
        assert all(calc[k] is None for k in ("contribution_margin", "break_even_units_monthly", "profit_monthly"))
        report = client.get(f"/api/v1/business/analyses/{row['id']}/report").json()
        assert all(m["after"] is None for m in report["scenario"]["metrics"])


def test_conflicting_approved_prices_block_analysis_until_user_resolves_them(tmp_path, database_url):
    case = {**CASES[0], "proposal": CASES[0]["proposal"] + "\nHarga jual Rp25.000 per unit."}
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        project = prepare_case(client, case)
        response = start_case(client, project)
        assert response.status_code == 422, response.text
        assert "beberapa nilai aktif" in response.json()["error"]["message"]
        saved = client.get(f"/api/v1/business/projects/{project['id']}").json()
        assert saved["analyses"] == []
