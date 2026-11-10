"""Export the synthetic Pepsodent archive without documents or operational data.

This is a public, read-only example of a previously recorded live run. No API
calls, generated messages, stance edits, or changes to the source archive.
"""

import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "backend/data/demo/pepsodent-groq-10p-2r-2026-11-08/analysis.json"
TARGET = ROOT / "frontend/public/demos/pepsodent.json"


def export(source_path=SOURCE, target_path=TARGET, public_document_ids=()):
    source = json.loads(source_path.read_text(encoding="utf-8"))
    snapshot = source["input_snapshot"]
    simulation = source["result"]["simulation"]
    if snapshot["context"]["data_classification"] != "synthetic":
        raise ValueError("Only the reviewed synthetic example may be published")
    if any(event.get("visibility") != "public" for event in simulation["events"] if event.get("kind") in {"post_message", "reply_message"}):
        raise ValueError("The public demo must contain public discussion only")
    allowed = set(public_document_ids)
    if not allowed <= {document["id"] for document in snapshot.get("documents", [])}:
        raise ValueError("Public document allowlist contains an unknown document")
    public_claims = [claim for claim in snapshot["claims"] if claim.get("source", {}).get("document_id") in allowed]
    public_claim_ids = {claim["id"] for claim in public_claims}
    public_documents = [document for document in snapshot.get("documents", []) if document["id"] in allowed]
    publish_calculation = bool(allowed) and bool(snapshot.get("value_claim_ids")) and set(snapshot["value_claim_ids"].values()) <= public_claim_ids

    def fields(item, names):
        return {name: item[name] for name in names.split() if name in item}

    personas = []
    for persona in snapshot["personas"]:
        public = fields(persona, "id name role stakeholder_type active reviewed revision")
        public.update({key: [] for key in ("goals", "motivations", "constraints", "knowledge", "interests", "relationships")})
        public.update(provenance={}, discovery_rationale="")
        if persona.get("provenance", {}).get("information_scope") == "external_public_brief_only":
            for key in ("goals", "interests", "constraints"):
                public[key] = list(persona.get(key, []))
        personas.append(public)
    events = [fields(event, "id sequence kind round actor_id target_id rationale amount parent_event_ids visibility content thread_id reply_to dialogue_act stance_update") for event in simulation["events"] if event.get("visibility") == "public" and event.get("kind") in {"post_message", "reply_message"}]
    findings = []
    for finding in source["result"]["findings"]:
        public = fields(finding, "id title category severity status origin author persona_ids event_ids reasoning confidence next_validation owner_suggestion")
        public.update({key: [] for key in ("claim_ids", "evidence_ids", "calculation_ids", "evidence_gaps")})
        public["claim_ids"] = [key for key in finding.get("claim_ids", []) if key in public_claim_ids]
        if publish_calculation:
            public["calculation_ids"] = list(finding.get("calculation_ids", []))
        findings.append(public)

    reviews = {entry["role"]: entry["status"] for entry in source["result"].get("agent_runs", []) if entry.get("phase") in ("specialist", "inherited_specialist") and entry.get("role")}
    demo = {
        "id": "demo_pepsodent_" + source["id"], "project_id": "demo_pepsodent", "baseline_id": None,
        **fields(source, "status stage created_at"),
        "input_snapshot": {
            "revision": snapshot["revision"], "context": snapshot["context"],
            "config": fields(snapshot["config"], "engine rounds interaction_mode customer_count"),
            "personas": personas, "claims": public_claims, "documents": public_documents,
            **({"idea": fields(snapshot["idea"], "id idea_id title version text")} if snapshot.get("idea") else {}),
        },
        "demo": {
            "source_analysis_id": source["id"],
            "public_brief": snapshot.get("information_policy", {}).get("public_brief", ""),
            "source_note": "Studi kasus sintetis. Hanya input yang dipilih untuk publikasi yang ditampilkan; angka contoh merupakan asumsi ilustratif, bukan data perusahaan atau hasil riset." if allowed else "Run memakai studi kasus sintetis Pepsodent Premium di Indonesia. Demo hanya menampilkan ide, brief publik, dan hasilnya; dokumen internal tidak dipublikasikan.",
            "quality_note": "Sebagian respons masih berulang. Gunakan hasil simulasi ini untuk menentukan hal yang perlu diuji, bukan sebagai keputusan pasar." if simulation.get("discussion_quality", {}).get("limited_exchange") else "Hasil ini adalah hipotesis simulasi untuk divalidasi, bukan keputusan pasar.",
            "specialists": [{"role": role, "status": reviews.get(role, "not_run")} for role in ("Market Agent", "Finance Agent", "Legal/Compliance Agent", "Risk Agent")],
            "model": snapshot.get("model"),
        },
        "result": {
            "findings": findings,
            "simulation": {
                "events": events, "states": {}, "stances": simulation["stances"],
                "stop_reason": simulation["stop_reason"], "usage": {},
                "interaction_mode": simulation["interaction_mode"],
                "calculation": {
                    "contribution_margin": None, "break_even_units_monthly": None,
                    "profit_monthly": None, "inputs": {}, "formulas": {},
                    "missing_inputs": ["Financial inputs are omitted from this public demo"],
                    "status": "not_included_in_public_demo",
                },
            },
        },
    }
    if publish_calculation:
        demo["result"]["simulation"]["calculation"] = simulation["calculation"]
    if source["status"] == "partial":
        demo["demo"]["quality_note"] = f"Analisis parsial: {len(events)} pesan tersimpan; alasan berhenti {simulation['stop_reason']}. Review spesialis yang selesai tidak berarti diskusi lengkap. Hasil merupakan hipotesis untuk divalidasi."
    elif source["status"] == "completed":
        complete = sum(status == "completed" for status in reviews.values())
        demo["demo"]["quality_note"] = f"Simulasi AI tersimpan: {len(events)} pesan dari {len(personas)} persona, {snapshot['config']['rounds']} ronde, {complete}/4 review spesialis selesai. Respons sintetis dan angka ilustratif bukan hasil riset pasar atau data perusahaan; gunakan untuk menentukan validasi berikutnya."
    if discussion_quality := simulation.get("discussion_quality"):
        demo["result"]["simulation"]["discussion_quality"] = discussion_quality
        repeated = len(discussion_quality.get("near_duplicate_event_ids", []))
        unanswered = len(discussion_quality.get("questions_without_recipient_reply", []))
        if repeated or unanswered:
            demo["demo"]["quality_note"] += f" Catatan struktur: {repeated} pesan terdeteksi sangat mirip; {unanswered} pertanyaan belum mendapat balasan penerimanya."
    if result_usage := source["result"].get("usage"):
        # Summary only: never publish raw provider requests or internal prompts.
        demo["result"]["usage"] = {key: result_usage[key] for key in ("cost", "cost_status", "actual_tokens", "call_count", "calls_with_reported_cost", "reported_cost_subtotal", "spending") if key in result_usage}
    demo["result"]["provenance"] = fields(source["result"].get("provenance", {}), "execution_kind model input_revision seed prompt_version")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(demo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Public demo: {len(personas)} personas, {len(events)} recorded messages")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--public-document-id", action="append", default=[])
    args = parser.parse_args()
    export(args.source, args.target, args.public_document_id)
