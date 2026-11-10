from copy import deepcopy

from app.business.agents import structured_findings
from app.business.contracts import BusinessAction
from app.business.intake import discover
from app.business.reporting import build_report, render_html
from app.business.simulation import BusinessSimulation


def data():
    context = {"name": 'Kedai <script>alert("unsafe")</script>', "industry": "Kopi", "region": "Bandung", "target_customer": "Mahasiswa", "decision_question": "Asumsi apa yang perlu divalidasi sebelum ekspansi?", "data_classification": "synthetic"}
    personas = [p for p in discover(context, []) if p["role"] in {"supplier", "operator"}]
    claims = [{"id": "claim-1", "quote": "Harga jual Rp30.000 per unit.", "normalized_text": "Harga jual Rp30.000 per unit.", "classification": "assumption", "variable": "selling_price", "value": "30000", "unit": "IDR/unit", "period": None, "review_status": "approved", "evidence_status": "UNAVAILABLE", "source": {"document_id": "doc-1", "locator": {"page": 2, "paragraph": 3}, "storage_key": "never-publish-this"}}]
    sim = BusinessSimulation("test-report", personas, {"selling_price": "30000", "variable_cost": "12000", "fixed_cost_monthly": "36000000", "volume_monthly": None})
    supplier = next(p["id"] for p in personas if p["role"] == "supplier")
    operator = next(p["id"] for p in personas if p["role"] == "operator")
    offer = sim.apply(BusinessAction(actor_id=supplier, target_id=operator, kind="offer_terms", expected_version=0, amount="12000", rationale="Tawaran sintetis"), 1)
    sim.apply(BusinessAction(actor_id=operator, target_id=supplier, kind="accept_terms", expected_version=0, parent_event_ids=[offer["id"]], rationale="Penerimaan sintetis"), 1)
    snapshot = {"context": context, "claims": claims, "personas": personas, "documents": [{"id": "doc-1", "name": "proposal.docx"}], "value_claim_ids": {"selling_price": "claim-1"}}
    evidence = [{"id": "external-1", "provider": "Untrusted <img src=x onerror=alert(1)>", "status": "UNAVAILABLE", "url": "javascript:alert(1)", "reason": "Belum ada sumber relevan"}]
    simulation = sim.snapshot()
    result = {"simulation": simulation, "findings": structured_findings(snapshot, simulation, evidence), "evidence": evidence, "disagreements": [{"author": "Market Agent", "summary": "Jangan simpulkan demand dari penerimaan penawaran supplier."}, {"author": "Finance Agent", "summary": "Break-even dapat dihitung, demand tetap belum diketahui."}], "limitations": [], "agent_runs": [], "provenance": {"execution_kind": "fixture"}}
    return snapshot, result


def test_report_preserves_disagreements_causal_sources_and_unknown_impact_without_mutating_registry():
    snapshot, result = data()
    before = deepcopy((snapshot, result))
    report = build_report(snapshot, result, analysis_id="analysis-test", status="partial")
    assert report["status"] == "partial"
    assert report["contradictions"] == result["disagreements"]
    interaction = next(f for f in report["findings"] if f["category"] == "interaction")
    assert [e["kind"] for e in interaction["interaction_chain"]] == ["offer_terms", "accept_terms"]
    assert all(f["estimated_impact"]["status"] == "UNKNOWN" for f in report["findings"])
    assert report["appendix"]["calculation"]["profit_monthly"] is None
    assert "halaman 2" in report["assumptions"][0]["source_label"]
    assert "never-publish-this" not in str(report)
    assert (snapshot, result) == before


def test_export_is_a_readable_escaped_document_with_all_sections_and_no_unsafe_links():
    snapshot, result = data()
    html = render_html(build_report(snapshot, result, analysis_id="analysis-test"))
    assert "<script>" not in html and "<img src=x" not in html
    assert "javascript:alert" not in html
    assert "&lt;script&gt;" in html and "&lt;img" in html
    assert "<pre>" not in html
    assert 'id="contradictions"' in html and "Finance Agent" in html
    assert "2.000" in html and "Belum diketahui" in html
    assert 'href="#event-test-report:event:1"' in html
    assert "@media print" in html
