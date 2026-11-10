"""Evidence-preserving report projection and portable HTML; no model calls."""
from __future__ import annotations

from copy import deepcopy
from .finding_checks import project_valid_findings
from decimal import Decimal
from html import escape
from urllib.parse import urlsplit


SECTIONS = [
    ("executive-summary", "Executive Summary"),
    ("assumption-register", "Assumption Register"),
    ("top-blind-spots", "Top Blind Spots"),
    ("evidence-table", "Evidence Table"),
    ("contradictions", "Contradictions"),
    ("scenario-impact", "Scenario Impact"),
    ("validation-tasks", "Recommended Validation Tasks"),
    ("limitations", "Limitations"),
]
PRIORITY = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
METRICS = {
    "contribution_margin": "Margin kontribusi (Rp/unit)",
    "break_even_units_monthly": "Break-even (unit/bulan)",
    "profit_monthly": "Profit kondisional (Rp/bulan)",
}
LABELS = {
    "question": "Pertanyaan", "answer": "Jawaban", "challenge": "Sanggahan", "clarification": "Klarifikasi", "proposal": "Usulan", "statement": "Pernyataan",
    "post_message": "Membuka diskusi", "reply_message": "Membalas pesan", "abstain": "Tidak menambah tanggapan",
    "support": "Mendukung", "oppose": "Menolak", "conditional": "Bersyarat", "undecided": "Belum memutuskan",
    "CRITICAL": "Kritis", "HIGH": "Tinggi", "MEDIUM": "Sedang", "LOW": "Rendah",
    "NEEDS_VALIDATION": "Perlu validasi", "SUPPORTED": "Didukung bukti", "CONFLICTING": "Bukti bertentangan",
    "VERIFIED": "Terverifikasi", "PARTIAL": "Dukungan sebagian", "UNAVAILABLE": "Belum tersedia", "STALE": "Perlu diperbarui",
    "document": "Dokumen", "evidence": "Evidence", "stakeholder": "Stakeholder", "interaction": "Interaksi", "scenario": "Scenario",
    "assumption": "Asumsi", "supplied_fact": "Fakta yang dipasok pengguna", "calculation": "Perhitungan", "opinion": "Pendapat", "forecast": "Proyeksi",
    "low": "Rendah", "medium": "Sedang", "high": "Tinggi", "approved": "Disetujui sebagai input", "pending": "Belum direview", "rejected": "Ditolak",
    "completed": "Selesai", "partial": "Selesai sebagian", "offer_terms": "Menawarkan syarat", "accept_terms": "Menerima penawaran", "adjust_price": "Menyesuaikan harga",
    "request_information": "Meminta informasi", "express_concern": "Menyampaikan kekhawatiran", "cooperate": "Mengusulkan kerja sama", "compete": "Merespons kompetisi",
    "shock": "Perubahan kondisi", "shock_expired": "Kondisi berakhir", "action_rejected": "Aksi ditolak",
}


def source_label(claim, documents):
    source = claim.get("source", {})
    locator = source.get("locator", {})
    parts = [documents.get(source.get("document_id"), "Dokumen sumber")]
    if locator.get("page") is not None:
        parts.append(f"halaman {locator['page']}")
    if locator.get("ordinal") is not None:
        parts.append(f"bagian {int(locator['ordinal']) + 1}")
    for key, label in (("paragraph", "paragraf"), ("table", "tabel"), ("row", "baris"), ("column", "kolom")):
        if locator.get(key) is not None:
            parts.append(f"{label} {locator[key]}")
    return " · ".join(parts)


def build_report(snapshot, result, *, analysis_id=None, baseline=None, status=None, created_at=None):
    result = project_valid_findings(result)
    if baseline:
        baseline = dict(baseline, result=project_valid_findings(baseline["result"]))
    simulation = result["simulation"]
    documents = {d["id"]: d["name"] for d in snapshot.get("documents", [])}
    claims = []
    for claim in snapshot["claims"]:
        value = {k: deepcopy(claim.get(k)) for k in ("id", "quote", "normalized_text", "classification", "variable", "value", "unit", "period", "region", "review_status", "evidence_status")}
        if claim.get("input_acceptance"):
            value.update(input_acceptance=claim["input_acceptance"], human_reviewed=claim.get("human_reviewed", False))
        value.update(source_label=source_label(claim, documents), document_id=claim.get("source", {}).get("document_id"), locator=deepcopy(claim.get("source", {}).get("locator", {})))
        claims.append(value)
    claim_map = {c["id"]: c for c in claims}
    personas = snapshot["personas"]
    names = {p["id"]: p["name"] for p in personas}
    names.update(environment="Kondisi scenario", all="Seluruh stakeholder")
    events = [{**deepcopy(e), "actor_name": names.get(e["actor_id"], e["actor_id"]), "target_name": names.get(e["target_id"], e["target_id"])} for e in simulation["events"]]
    event_map = {e["id"]: e for e in events}
    evidence = deepcopy(result.get("evidence", []))
    evidence_map = {e["id"]: e for e in evidence}
    findings = []
    for original in sorted(result.get("findings", []), key=lambda f: PRIORITY.get(f["severity"], 99)):
        finding = deepcopy(original)
        visited, pending = set(), list(finding["event_ids"])
        while pending:
            event_id = pending.pop()
            if event_id in visited or event_id not in event_map:
                continue
            visited.add(event_id)
            pending.extend(event_map[event_id].get("parent_event_ids", []))
        finding["affected_assumptions"] = [claim_map[i] for i in finding["claim_ids"] if i in claim_map]
        finding["supporting_evidence"] = [evidence_map[i] for i in finding["evidence_ids"] if i in evidence_map]
        finding["interaction_chain"] = [e for e in events if e["id"] in visited]
        finding["estimated_impact"] = {"status": "UNKNOWN", "explanation": "Besaran dampak temuan ini belum dapat dihitung. Metrik usaha bukan estimasi kerugian akibat risiko."}
        finding["has_related_calculation"] = simulation["calculation"]["id"] in finding["calculation_ids"]
        findings.append(finding)
    for row in evidence:
        row["related_claim_ids"] = sorted({i for f in findings if row["id"] in f["evidence_ids"] for i in f["claim_ids"] if i in claim_map})
    calculation = deepcopy(simulation["calculation"])
    previous = baseline["result"].get("simulation", {}) if baseline else {}
    metrics = []
    for key, label in METRICS.items():
        before = previous.get("calculation", {}).get(key)
        after = calculation.get(key)
        delta = format(Decimal(str(after)) - Decimal(str(before)), "f") if before is not None and after is not None else None
        metrics.append({"metric": key, "label": label, "before": before, "after": after, "delta": delta, "status": "COMPUTED_CONDITIONAL_ON_INPUTS" if after is not None else "UNKNOWN"})
    old_findings = baseline["result"].get("findings", []) if baseline else []
    signatures = {(f["title"], f["category"]) for f in old_findings}
    state_changes = [{"id": key, "name": names.get(key, key), "before": previous.get("states", {}).get(key), "after": value} for key, value in simulation.get("states", {}).items()] if baseline else []
    disagreements = deepcopy(result.get("disagreements", []))
    if simulation.get("interaction_mode") == "swarm-v1":
        expressed = [(names.get(key, key), state["stance"]) for key, state in simulation.get("stances", {}).items() if state["stance"] != "undecided"]
        if len({stance for _, stance in expressed}) > 1:
            disagreements.append({"author": "Jejak diskusi swarm", "summary": "Posisi sintetis peserta masih berbeda: " + "; ".join(f"{name}: {stance}" for name, stance in expressed) + ". Ini bukan distribusi opini customer nyata atau voting kelayakan."})
    tasks = [{"id": "task-" + f["id"], "finding_id": f["id"], "title": f["title"], "priority": f["severity"], "action": f["next_validation"], "owner": f["owner_suggestion"], "evidence_gaps": f["evidence_gaps"], "status": "PROPOSED"} for f in findings]
    limitations = list(dict.fromkeys([*result.get("limitations", []), "Persetujuan input dan kesepakatan persona tidak memverifikasi fakta pasar.", "Perbedaan pendapat dipertahankan; jumlah agen yang sepakat bukan bukti independen.", "Skor kelayakan numerik belum tersedia; prioritas temuan tidak menyatakan probabilitas keberhasilan."]))
    if simulation.get("interaction_mode") == "swarm-v1":
        limitations.append("Kelompok customer memakai sudut pandang sintetis, tanpa klaim demografi atau proporsi pasar. Perubahan sikap adalah keluaran model/fixture, bukan pengukuran perilaku nyata.")
    if calculation.get("profit_monthly") is None:
        limitations.append("Profit belum diketahui karena input harga, biaya atau volume yang diperlukan belum lengkap.")
    high_priority = sum(f["severity"] in {"HIGH", "CRITICAL"} for f in findings)
    unavailable = sum(e.get("status") == "UNAVAILABLE" for e in evidence)
    incomplete = status not in (None, "completed") or simulation.get("stop_reason") not in (None, "round_limit", "discussion_quiet")
    if incomplete:
        headline = "Kesimpulan sementara: analisis belum lengkap"
        takeaway = "Gunakan temuan yang sudah tersedia sebagai bahan pemeriksaan awal. Selesaikan bagian analisis yang terhenti sebelum mengambil keputusan lanjutan."
    elif not findings:
        headline = "Belum cukup dasar untuk menentukan kelayakan"
        takeaway = "Belum ada temuan yang cukup untuk menyimpulkan ide ini layak atau bebas risiko. Periksa kelengkapan informasi dan uji asumsi utamanya terlebih dahulu."
    elif high_priority:
        headline = "Tangani risiko utama sebelum melanjutkan rencana"
        takeaway = "Ada persoalan penting yang perlu diselesaikan sebelum rencana diperluas. Prioritaskan validasi di bawah; hasil ini belum membuktikan bisnis akan berhasil atau gagal."
    else:
        headline = "Uji asumsi utama sebelum memperluas rencana"
        takeaway = "Gunakan uji terbatas untuk memeriksa temuan berikut sebelum menambah komitmen biaya atau skala usaha. Respons persona merupakan simulasi, bukan bukti permintaan pasar."
    reasons = [{"finding_id": f["id"], "title": f["title"], "text": f["reasoning"]} for f in findings[:3]]
    actions = list(dict.fromkeys(t["action"] for t in tasks if t["action"].strip()))[:3]
    if incomplete:
        actions = ["Periksa alasan analisis terhenti dan selesaikan bagian yang belum berjalan.", *actions[:2]]
    if not actions:
        actions = ["Lengkapi informasi utama dan lakukan validasi langsung dengan calon pengguna sebelum mengambil keputusan."]
    summary = {
        "decision_question": snapshot["context"]["decision_question"],
        "text": takeaway,
        "conclusion": {"headline": headline, "reasons": reasons, "actions": actions, "incomplete": incomplete},
        "finding_count": len(findings), "high_priority_count": high_priority, "disagreement_count": len(disagreements),
        "unavailable_evidence_count": unavailable, "top_finding_ids": [f["id"] for f in findings[:3]],
        "validation_status": "NEEDS_VALIDATION", "next_action": tasks[0]["action"] if tasks else "Review kelengkapan asumsi dan sumber; tidak adanya temuan belum membuktikan tidak adanya risiko.",
    }
    shock = deepcopy(snapshot.get("shock"))
    scenario = {"is_scenario": bool(shock), "baseline_id": baseline["id"] if baseline else None, "shock": shock, "metrics": metrics, "state_changes": state_changes,
                "new_finding_ids": [f["id"] for f in findings if (f["title"], f["category"]) not in signatures] if baseline else [],
                "comparison_available": bool(baseline), "notice": "Delta mengikuti input dan strategi yang dipilih. Respons stakeholder adalah hipotesis sintetis; perubahan volume pasar tetap belum diketahui." if shock else "Ini baseline. Buat scenario terpisah untuk menguji perubahan kondisi dan membandingkan hasilnya."}
    return {"version": "pakar-report-v2", "title": "Laporan analisis bisnis — " + snapshot["context"]["name"], "analysis_id": analysis_id,
            "status": status or "completed", "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
            "context": deepcopy(snapshot["context"]), "sections": [{"id": key, "title": title} for key, title in SECTIONS],
            "summary": summary, "assumptions": claims, "findings": findings, "evidence": evidence, "contradictions": disagreements,
            "scenario": scenario, "validation_tasks": tasks, "limitations": limitations,
            "appendix": {"personas": deepcopy(personas), "events": events, "relationships": deepcopy(simulation.get("relationships", [])), "threads": deepcopy(simulation.get("threads", [])), "stances": deepcopy(simulation.get("stances", {})),
                         "discussion_quality": deepcopy(simulation.get("discussion_quality")), "calculation": calculation, "provenance": deepcopy(result.get("provenance", {})), "agent_runs": deepcopy(result.get("agent_runs", [])), "action_validation": deepcopy(result.get("action_validation", {}))}}


def number(value):
    if value is None:
        return "Belum diketahui"
    text = format(Decimal(str(value)), ",f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.translate(str.maketrans(",.", ".,"))


def safe_url(value):
    try:
        url = urlsplit(value or "")
        return value if url.scheme in {"http", "https"} and url.hostname and not url.username and not url.password else None
    except ValueError:
        return None


def render_html(report):
    def e(value):
        return escape(str(value if value is not None else "Belum diketahui"), quote=True)

    def label(value):
        return e(LABELS.get(value, value))

    def items(values):
        return "<ul>" + "".join(f"<li>{e(v)}</li>" for v in values) + "</ul>" if values else "<p>Belum ada catatan.</p>"

    def table(headers, rows, scroll_label=None):
        attrs = f' role="region" tabindex="0" aria-label="{e(scroll_label)}"' if scroll_label else ''
        return f'<div class="table-wrap"{attrs}><table><thead><tr>' + "".join(f"<th>{e(h)}</th>" for h in headers) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows) + "</tbody></table></div>"

    def heading(key):
        title = dict(SECTIONS)[key]
        return f'<section id="{key}"><h2>{title}</h2>'

    def metric_table(metrics, comparison=False):
        if comparison:
            return '<p class="scroll-hint">Geser tabel untuk melihat kolom Delta. Gunakan tombol panah saat tabel difokuskan.</p>' + table(["Metrik kondisional", "Baseline", "Scenario", "Delta"], [[e(m["label"]), e(number(m["before"])), e(number(m["after"])), e(number(m["delta"]))] for m in metrics], scroll_label="Perbandingan metrik kondisional; geser untuk melihat kolom Delta")
        return table(["Metrik kondisional", "Nilai"], [[e(m["label"]), e(number(m["after"]))] for m in metrics])

    css = """*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:#161616;background:#fff;font:16px/1.65 'IBM Plex Sans',Arial,sans-serif}main{max-width:1040px;margin:auto;padding:48px 32px}h1{font-size:36px;line-height:1.2;font-weight:400}h2{font-size:25px;font-weight:500;margin:0 0 20px}h3{font-size:19px;margin:24px 0 10px}p{max-width:75ch}a{color:#0043ce;text-underline-offset:3px}a:focus-visible{outline:2px solid #0f62fe;outline-offset:3px}nav{padding:20px 0;border-block:1px solid #dcdcdc}nav ul{columns:2;padding-left:22px}section{padding:32px 0;border-bottom:1px solid #dcdcdc;scroll-margin-top:20px}.notice{background:#edf5ff;color:#002d9c;padding:16px 20px}.meta{color:#525252;font-size:14px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}th,td{padding:14px 12px;text-align:left;vertical-align:top;border-bottom:1px solid #dcdcdc;overflow-wrap:anywhere}th{background:#f4f4f4;font-weight:600}blockquote{margin:16px 0;padding:16px;background:#f4f4f4}article{padding:12px 0 24px;border-bottom:1px solid #e0e0e0}dl{display:grid;grid-template-columns:minmax(100px,190px) 1fr;gap:8px 20px}dt{font-weight:600}dd{margin:0;overflow-wrap:anywhere}.finding-ref{font-size:13px;color:#525252}.task{margin-block:24px}.avoid-break{break-inside:avoid}footer{margin-top:32px;font-size:13px;color:#525252}@media(max-width:640px){main{padding:24px 18px}h1{font-size:28px}nav ul{columns:1}dl{grid-template-columns:1fr;gap:4px}dd{margin-bottom:12px}th,td{padding:10px 8px}table{min-width:520px}}@media print{@page{size:A4;margin:16mm}body{font-size:11pt}main{max-width:none;padding:0}nav{display:none}h1{font-size:25pt}h2{font-size:18pt}h2,h3{break-after:avoid}tr,blockquote,.task{break-inside:avoid}thead{display:table-header-group}.table-wrap{overflow:visible}table{min-width:0}section{padding:18px 0}a{color:inherit}footer{font-size:9pt}}"""
    css += '.scroll-hint{display:none}.table-wrap:focus-visible{outline:2px solid #0f62fe;outline-offset:3px}@media(max-width:640px){.scroll-hint{display:block;font-size:14px;color:#525252}}@media print{.scroll-hint{display:none}}'
    out = [f'<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(report["title"])}</title><style>{css}</style></head><body><main>',
           f'<header><h1>{e(report["title"])}</h1><p>{e(report["context"]["industry"])} · {e(report["context"]["region"])}</p><p class="meta">Run {e(report["analysis_id"])} · {label(report["status"])} · {e(report["created_at"])}</p><p class="notice">Hipotesis untuk divalidasi. Laporan ini tidak menyatakan kelayakan bisnis atau memprediksi keberhasilan pasar.</p></header>',
           '<nav aria-label="Daftar isi laporan"><ul>' + ''.join(f'<li><a href="#{key}">{title}</a></li>' for key, title in SECTIONS) + '</ul></nav>']
    summary = report["summary"]
    conclusion = summary.get("conclusion", {})
    out += [heading("executive-summary"), f'<h3>{e(conclusion.get("headline", "Kesimpulan awal"))}</h3><p>{e(summary["text"])}</p>']
    if conclusion.get("reasons"):
        out.append('<h3>Alasan utama</h3><ul>' + ''.join(f'<li><strong>{e(r["title"])}</strong><p>{e(r["text"])}</p></li>' for r in conclusion["reasons"]) + '</ul>')
    out.append('<h3>Langkah berikutnya</h3><ol>' + ''.join(f'<li>{e(action)}</li>' for action in conclusion.get("actions", [summary["next_action"]])) + '</ol>')
    out += [f'<details><summary>Lihat konteks dan perhitungan</summary><p>{e(summary["decision_question"])}</p>', metric_table(report["scenario"]["metrics"]), '</details></section>']
    out += [heading("assumption-register"), '<p>Penerimaan asumsi menetapkan input analisis, bukan kebenaran eksternal.</p>', table(["Asumsi / klaim", "Klasifikasi & nilai", "Status", "Jejak sumber"], [[f'<strong>{e(c["normalized_text"])}</strong><blockquote>{e(c["quote"])}</blockquote>', f'{label(c["classification"])}<br>{e(number(c["value"]))} {e(c["unit"] or "")}<br>{e(c["period"] or "Periode belum diketahui")}', f'{label(c["review_status"])}<br>{label(c["evidence_status"])}', f'{e(c["source_label"])}<br><span class="finding-ref">{e(c["id"])}</span>'] for c in report["assumptions"]]), '</section>']
    out.append(heading("top-blind-spots"))
    for f in report["findings"]:
        out += [f'<article id="finding-{e(f["id"])}"><h3>{e(f["title"])}</h3><p class="meta">{label(f["severity"])} · {label(f["category"])} · {e(f["author"])} · {label(f["status"])}</p><p>{e(f["reasoning"])}</p><p>Keyakinan: {label(f["confidence"])}. {e(f["estimated_impact"]["explanation"])}</p>']
        for claim in f["affected_assumptions"]:
            out.append(f'<blockquote>{e(claim["quote"])}<br><small>{e(claim["source_label"])}</small></blockquote>')
        if f["interaction_chain"]:
            out.append('<h4>Rangkaian interaksi yang dirujuk</h4><ol>' + ''.join(f'<li><a href="#event-{e(event["id"])}">Ronde {event["round"]}: {e(event["actor_name"])} → {e(event["target_name"])}</a> — {label(event["kind"])}. {e(event["rationale"])}</li>' for event in f["interaction_chain"]) + '</ol>')
        for row in f["supporting_evidence"]:
            out.append(f'<p>Evidence {e(row["id"])}: {label(row["status"])}</p>')
        out += ['<h4>Evidence gaps</h4>', items(f["evidence_gaps"]), f'<p><strong>Validasi berikutnya:</strong> {e(f["next_validation"])}<br>Penanggung jawab: {e(f["owner_suggestion"])}</p></article>']
    if not report["findings"]:
        out.append('<p>Belum ada temuan tercatat. Ini bukan bukti bahwa bisnis bebas risiko.</p>')
    out.append('</section>' + heading("evidence-table"))
    evidence_rows = []
    for row in report["evidence"]:
        url = safe_url(row.get("url"))
        link = f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">Buka sumber</a>' if url else 'Sumber belum tersedia'
        evidence_rows.append([f'{e(row.get("provider") or row["id"])}<br>{link}<br>{e(row["id"])}', label(row.get("status", "UNAVAILABLE")), f'{e(row.get("region"))}<br>{e(row.get("observed_period"))}<br>{e(row.get("unit"))}', f'{e(row.get("value"))}<br>{e(row.get("reason") or "Relevansi terhadap klaim tetap perlu diperiksa")}', e(row.get("retrieved_at"))])
    out += ['<p>Sumber resmi tetap perlu dicocokkan dengan wilayah, periode, satuan, dan arti klaim.</p>', table(["Sumber", "Dukungan", "Wilayah / periode / satuan", "Nilai & keterbatasan", "Waktu pengambilan"], evidence_rows) if evidence_rows else '<p>Belum ada evidence eksternal tersedia.</p>', '</section>', heading("contradictions")]
    if report["contradictions"]:
        out += [f'<article><h3>{e(d["author"])}</h3><p>{e(d["summary"])}</p></article>' for d in report["contradictions"]]
    else:
        out.append('<p>Tidak ada perbedaan pendapat yang tercatat. Ini tidak membuktikan adanya konsensus atau kelengkapan pemeriksaan.</p>')
    out += ['<p>Perbedaan kesimpulan tidak diselesaikan lewat suara mayoritas; bukti dan ketidakpastian tetap ditampilkan.</p></section>', heading("scenario-impact"), f'<p>{e(report["scenario"]["notice"])}</p>']
    scenario = report["scenario"]
    if scenario["shock"]:
        shock = scenario["shock"]
        out.append(f'<p>Kondisi: {e(shock["kind"])} · {e(number(shock["magnitude_percent"]))}% · {e(shock["region"])} · mulai ronde {shock["effective_round"]}, durasi {shock["duration_rounds"]} ronde. Strategi: {e(shock["response_strategy"])}</p><p>{e(shock.get("description", ""))}</p>')
    out.append(metric_table(scenario["metrics"], scenario["comparison_available"]))
    if scenario["state_changes"]:
        out.append(table(["Stakeholder", "Posisi baseline", "Posisi scenario"], [[e(s["name"]), label((s["before"] or {}).get("position", "Belum diketahui")), label(s["after"]["position"])] for s in scenario["state_changes"]]))
        out.append(f'<p>{len(scenario["new_finding_ids"])} kandidat temuan baru dibanding baseline. Kesamaan judul tidak membuktikan risiko tetap sama.</p>')
    out += ['</section>', heading("validation-tasks")]
    for task in report["validation_tasks"]:
        out.append(f'<article class="task"><h3>{e(task["title"])}</h3><p>{label(task["priority"])} · Tugas yang diusulkan, belum dilaksanakan</p><p>{e(task["action"])}</p><p>Penanggung jawab yang disarankan: {e(task["owner"])}</p><a href="#finding-{e(task["finding_id"])}">Periksa temuan dan buktinya</a></article>')
    if not report["validation_tasks"]:
        out.append('<p>Belum ada tugas spesifik. Review kelengkapan asumsi dan sumber sebelum mengambil keputusan.</p>')
    out += ['</section>', heading("limitations"), items(report["limitations"]), '</section>', '<section id="interaction-appendix"><h2>Lampiran: stakeholder dan jejak interaksi</h2><p>Semua respons persona merupakan hipotesis sintetis.</p>']
    out.append(table(["Stakeholder", "Peran", "Tujuan & kendala"], [[e(p["name"]), e(p["role"]), items(p["goals"]) + items(p["constraints"])] for p in report["appendix"]["personas"]]))
    names = {p["id"]: p["name"] for p in report["appendix"]["personas"]}
    quality = report["appendix"].get("discussion_quality")
    if quality:
        out.append('<h3>Struktur dan batas diskusi</h3>')
        out.append(table(["Indikator", "Tercatat"], [["Pasangan saling membalas dua arah", e(quality["reciprocal_pairs"])], ["Balasan antarcustomer", e(quality["customer_peer_replies"])], ["Pesan sangat mirip", e(len(quality["near_duplicate_event_ids"]))], ["Pertanyaan tanpa balasan penerima", e(len(quality["questions_without_recipient_reply"]))]]))
        out.append(items(quality["warnings"]) + '<p>' + e(quality["notice"]) + '</p>')
    out.append(table(["Dari", "Kepada", "Posisi relasi", "Interaksi pendukung"], [[e(names.get(r["source"], r["source"])), e(names.get(r["target"], r["target"])), label(r["status"]), ', '.join(f'<a href="#event-{e(i)}">{e(i)}</a>' for i in r["event_ids"]) or 'Relasi awal, masih hipotesis'] for r in report["appendix"]["relationships"]]))
    if report["appendix"].get("threads"):
        roots = {event["id"]: event for event in report["appendix"]["events"]}
        out.append('<h3>Thread diskusi</h3>')
        out.append(table(["Thread", "Akses", "Pesan"], [[f'<a href="#event-{e(thread["root_event_id"])}">{e(roots[thread["root_event_id"]]["rationale"][:120])}</a>', 'Publik untuk peserta' if thread["visibility"] == 'public' else 'Privat antarpartisipan', e(len(thread["message_ids"]))] for thread in report["appendix"]["threads"]]))
    for event in report["appendix"]["events"]:
        out.append(f'<article id="event-{e(event["id"])}"><h3>Ronde {event["round"]}: {e(event["actor_name"])} → {e(event["target_name"])}</h3><p>{label(event["kind"])} · hipotesis simulasi</p><p>{e(event["rationale"])}</p>')
        if event.get("dialogue_act"):
            out.append(f'<p>Jenis tanggapan: {label(event["dialogue_act"])}</p>')
        if event.get("dispatch", {}).get("trigger_event_id"):
            out.append(f'<p><a href="#event-{e(event["dispatch"]["trigger_event_id"])}">Giliran dipicu pertanyaan atau sanggahan ini</a></p>')
        if event.get("thread_id"):
            out.append(f'<p>Thread: <a href="#event-{e(event["thread_id"])}">Periksa awal diskusi</a>. Akses: {e(event["visibility"])}.</p>')
        if event.get("reply_to"):
            out.append(f'<p><a href="#event-{e(event["reply_to"])}">Membalas pesan sebelumnya</a></p>')
        if event.get("stance_update"):
            update = event["stance_update"]
            out.append(f'<p>Sikap: {label(update["before"])} &rarr; {label(update["after"])}. {e(update["reason"])}</p>')
        if event.get("amount") is not None:
            out.append(f'<p>Nilai aksi: {e(number(event["amount"]))} — bukan transaksi nyata.</p>')
        if event.get("state_after"):
            out.append(f'<p>Posisi: {label(event["state_before"]["position"])} → {label(event["state_after"]["position"])}; revisi {event["state_after"]["version"]}.</p>')
        out.append('<p class="finding-ref">' + e(event["id"]) + '</p>')
        out.append('<p>Parent: ' + (', '.join(f'<a href="#event-{e(i)}">{e(i)}</a>' for i in event["parent_event_ids"]) or 'Tidak merujuk event sebelumnya') + '</p></article>')
    if report["appendix"].get("stances"):
        out.append('<h3>Posisi dan perubahan sikap sintetis</h3><p>Ini bukan survei pasar atau voting kelayakan.</p>')
        for key, state in report["appendix"]["stances"].items():
            out.append(f'<h4>{e(names.get(key, key))}: {label(state["stance"])}</h4><p>{e(state["stance_reason"])}</p>')
            for change in state["stance_history"]:
                out.append(f'<p>Ronde {change["round"]}: {label(change["before"])} &rarr; {label(change["after"])}. {e(change["reason"])} <a href="#event-{e(change["event_id"])}">Periksa interaksi</a></p>')
    calc = report["appendix"]["calculation"]
    out += ['</section><section><h2>Lampiran: calculation trail</h2>', table(["Input", "Nilai"], [[e(key), e(number(value))] for key, value in calc["inputs"].items()]), table(["Metrik", "Formula"], [[e(key), e(value)] for key, value in calc["formulas"].items()]), '<h3>Input yang belum lengkap</h3>', items(calc["missing_inputs"]), '</section><section><h2>Lampiran: provenance dan pemeriksaan agen</h2>', table(["Atribut", "Nilai"], [[e(k), e(v)] for k, v in report["appendix"]["provenance"].items()]), table(["Agen", "Jenis pemeriksaan", "Status / token"], [[e(r["role"]), e(r.get("execution_kind") or r.get("tool") or "Review specialist"), f'{e(r.get("status") or "Respons diterima; lihat temuan tervalidasi")} · {e(r.get("tokens"))} token'] for r in report["appendix"]["agent_runs"]]), '</section><footer>PAKAR · Laporan disusun dari registry analisis tersimpan. Temuan memerlukan validasi manusia dan sumber yang sesuai.</footer></main></body></html>']
    return '\n'.join(out)
