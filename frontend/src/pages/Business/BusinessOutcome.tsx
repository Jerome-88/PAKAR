import { useRef } from "react";
import type { BusinessAnalysis } from "../../api/business";
import { BusinessText } from "./BusinessText";
import { formatBusinessAmount, friendlyText, previewText, responseSummary } from "./resultSummary";
import { statusLabel } from "./businessFormatting";
import "./BusinessOutcome.css";

type SavedMetadata = { demo?: { model?: string; specialists: { role: string; status: string }[]; quality_note?: string } };
const stopLabels: Record<string, string> = {
  runtime_provider_failure: "Diskusi berhenti karena error provider.",
  rounds_completed: "Seluruh ronde yang direncanakan selesai.",
  round_limit: "Seluruh ronde yang direncanakan selesai.",
  max_rounds: "Batas ronde yang direncanakan tercapai.",
  token_budget: "Diskusi berhenti pada batas token.",
  budget_exceeded: "Diskusi berhenti pada batas anggaran atau waktu.",
};
export function BusinessRunStatus({ analysis }: { analysis: BusinessAnalysis }) {
  const simulation = analysis.result.simulation;
  const events = simulation?.events.filter(event => ["post_message", "reply_message"].includes(event.kind)) ?? [];
  const rounds = new Set(events.map(event => event.round));
  const demo = (analysis as BusinessAnalysis & SavedMetadata).demo;
  const reviews = demo?.specialists ?? analysis.result.agent_runs?.filter(run => ["specialist", "inherited_specialist"].includes(run.phase ?? "")) ?? [];
  const completed = new Set(reviews.filter(run => run.status === "completed").map(run => run.role)).size;
  return <section className="business-outcome-status" aria-label="Kelengkapan analisis">
    <strong>{analysis.status === "partial" ? "Analisis selesai sebagian" : statusLabel(analysis.status)}</strong>
    <p>{events.length} pesan tersimpan · {rounds.size} dari {analysis.input_snapshot.config.rounds} ronde memiliki pesan · {completed}/4 review spesialis selesai.</p>
    <p>{stopLabels[simulation?.stop_reason ?? ""] ?? (analysis.status === "completed" ? "Proses selesai sesuai batas run. Periksa bukti dan asumsi sebelum mengambil keputusan." : "Periksa jejak analisis untuk mengetahui batas proses.")}{analysis.status === "partial" && " Review spesialis yang selesai tidak berarti seluruh diskusi sudah lengkap."}</p>
  </section>;
}

export function BusinessFinalReport({ analysis, onFinding }: { analysis: BusinessAnalysis; onFinding: (id: string) => void }) {
  const content = useRef<HTMLDivElement>(null);
  const severity: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
  const findings = [...analysis.result.findings ?? []].sort((a, b) => (severity[a.severity] ?? 4) - (severity[b.severity] ?? 4));
  const summary = responseSummary(analysis.result.simulation?.events ?? [], analysis.input_snapshot.personas, analysis.result.simulation?.stances);
  const calculation = analysis.result.simulation?.calculation;
  const stopReason = analysis.result.simulation?.stop_reason;
  const incomplete = analysis.status !== "completed" || (!!stopReason && !["round_limit", "discussion_quiet", "rounds_completed", "max_rounds"].includes(stopReason));
  const highPriority = findings.some(finding => ["HIGH", "CRITICAL"].includes(finding.severity));
  const headline = incomplete ? "Kesimpulan sementara: analisis belum lengkap" : !findings.length ? "Belum cukup dasar untuk menentukan kelayakan" : highPriority ? "Tangani risiko utama sebelum melanjutkan rencana" : "Uji asumsi utama sebelum memperluas rencana";
  const takeaway = incomplete ? "Gunakan temuan yang sudah tersedia sebagai bahan pemeriksaan awal. Selesaikan bagian analisis yang terhenti sebelum mengambil keputusan lanjutan." : !findings.length ? "Belum ada temuan yang cukup untuk menyimpulkan ide ini layak atau bebas risiko. Periksa kelengkapan informasi dan uji asumsi utamanya terlebih dahulu." : highPriority ? "Ada persoalan penting yang perlu diselesaikan sebelum rencana diperluas. Prioritaskan validasi di bawah; hasil ini belum membuktikan bisnis akan berhasil atau gagal." : "Gunakan uji terbatas untuk memeriksa temuan berikut sebelum menambah komitmen biaya atau skala usaha. Respons persona merupakan simulasi, bukan bukti permintaan pasar.";
  const actions = [...new Set(findings.map(finding => friendlyText(finding.next_validation)).filter(Boolean))].slice(0, 3);
  if (incomplete) actions.splice(0, 0, "Periksa alasan analisis terhenti dan selesaikan bagian yang belum berjalan.");
  if (!actions.length) actions.push("Lengkapi informasi utama dan lakukan validasi langsung dengan calon pengguna sebelum mengambil keputusan.");

  const download = () => {
    if (!content.current) return;
    const markup = `<!doctype html><html lang="id"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Laporan PAKAR</title><style>body{font:16px/1.6 system-ui;margin:40px auto;padding:0 24px;max-width:900px;color:#252525}article,section{margin:24px 0}h1,h2,h3{line-height:1.3}button{display:none}dl{display:grid;gap:8px}dd{margin:0}blockquote{margin:12px 0;padding:12px;background:#f6f6f6}</style><body>${content.current.innerHTML}</body></html>`;
    const url = URL.createObjectURL(new Blob([markup], { type: "text/html;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url; link.download = `pakar-report-${analysis.id.replace(/[^a-zA-Z0-9_-]/g, "")}.html`;
    link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <section className="business-outcome-report"><div className="business-row-heading"><h2>Final Report</h2><button type="button" className="button secondary" onClick={download}>Unduh laporan HTML</button></div>
    <div ref={content}>
      <h2>{analysis.input_snapshot.context.name}</h2>
      <section aria-label="Ringkasan keputusan"><h3>Executive Summary</h3><h4 className="business-outcome-takeaway">{headline}</h4><p>{takeaway}</p>
        {!!findings.length && <><h4>Alasan utama</h4><ul>{findings.slice(0, 3).map(finding => <li key={finding.id}><strong>{friendlyText(finding.title)}</strong><p>{previewText(finding.reasoning, 320)}</p><button type="button" className="business-text-button" onClick={() => onFinding(finding.id)}>Lihat dasar temuan</button></li>)}</ul></>}
        <h4>Langkah berikutnya</h4><ol>{actions.slice(0, 3).map(action => <li key={action}>{action}</li>)}</ol>
        <p>{incomplete ? "Analisis belum lengkap; kesimpulan ini bersifat sementara." : "Ringkasan berdasarkan input dan temuan run ini; asumsi tetap perlu diuji langsung."}</p>
        <details><summary>Lihat konteks dan kelengkapan analisis</summary><p>{analysis.input_snapshot.context.decision_question}</p><BusinessRunStatus analysis={analysis} /><p>{summary.counts.support} mendukung, {summary.counts.conditional} bersyarat, {summary.counts.oppose} menolak, {summary.counts.undecided} belum memutuskan, dan {summary.counts.unrecorded} belum tercatat dari {summary.total} persona sintetis. Jumlah ini bukan hasil survei konsumen.</p></details>
      </section>
      <section><details><summary>Sumber dan asumsi input</summary>{analysis.input_snapshot.claims.length ? analysis.input_snapshot.claims.map(claim => <blockquote key={claim.id}><BusinessText value={claim.quote} /><footer>{analysis.input_snapshot.documents?.find(document => document.id === claim.source.document_id)?.name ?? "Dokumen input"} · {claim.classification} · {claim.evidence_status}</footer></blockquote>) : <p>Tidak ada kutipan sumber yang dipublikasikan pada hasil ini.</p>}{(analysis.result.evidence ?? []).map(evidence => <p key={evidence.id}>{evidence.provider} · {evidence.status}: {evidence.reason}</p>)}</details></section>
      <section><details><summary>Perhitungan kondisional</summary>{calculation && Object.keys(calculation.formulas).length > 0 ? <><dl>{Object.entries(calculation.inputs).map(([key, value]) => <div key={key}><dt>{friendlyText(key)}</dt><dd>{formatBusinessAmount(value)}</dd></div>)}</dl>{Object.entries(calculation.formulas).map(([key, formula]) => <p key={key}>{friendlyText(key)}: <code>{formula}</code> = {formatBusinessAmount(calculation[key as "contribution_margin" | "break_even_units_monthly" | "profit_monthly"])}</p>)}<p>Perhitungan mengikuti asumsi tersimpan; hasil bukan bukti penjualan, laba aktual, atau ramalan permintaan.</p></> : <p>Input dan formula perhitungan belum tersedia pada hasil ini.</p>}</details></section>
      <section><details><summary>Semua temuan dan tugas validasi ({findings.length})</summary>{findings.length ? <ol>{findings.map(finding => <li key={finding.id}><article><h4>{friendlyText(finding.title)}</h4><p>{finding.author} · {finding.severity} · Perlu validasi</p><BusinessText value={friendlyText(finding.reasoning)} /><p><strong>Tindakan berikutnya:</strong></p><BusinessText value={friendlyText(finding.next_validation) || "Periksa asumsi dan sumber bersama reviewer yang sesuai."} /><p><strong>Penanggung jawab yang disarankan:</strong> {finding.owner_suggestion || "Belum ditentukan"}</p><p>{finding.event_ids.length} referensi pesan · {finding.claim_ids.length} referensi klaim · {finding.evidence_ids.length} referensi evidence</p><button type="button" className="business-text-button" onClick={() => onFinding(finding.id)}>Tinjau temuan dan sumber</button></article></li>)}</ol> : <p>Belum ada temuan tersimpan. Ini tidak membuktikan bahwa ide bebas risiko.</p>}</details></section>
      <section><h3>Batas penggunaan</h3><p>Persona dan respons merupakan simulasi AI. Input asumsi, termasuk angka ilustratif, belum menjadi bukti independen. Tugas validasi di atas belum dilaksanakan oleh sistem.</p><p>Run: {analysis.id} · Dibuat: {analysis.created_at}</p></section>
    </div>
  </section>;
}

export function BusinessAnalysisTrail({ analysis }: { analysis: BusinessAnalysis }) {
  const demo = (analysis as BusinessAnalysis & SavedMetadata).demo;
  const runs = demo?.specialists ?? analysis.result.agent_runs?.filter(run => ["specialist", "inherited_specialist"].includes(run.phase ?? "")) ?? [];
  return <section className="business-outcome-trail"><h2>Analysis Trail</h2><BusinessRunStatus analysis={analysis} />
    <dl><dt>Run</dt><dd>{analysis.id}</dd><dt>Model</dt><dd>{analysis.result.provenance?.model ?? demo?.model ?? "Belum tersedia"}</dd><dt>Revisi input</dt><dd>{analysis.input_snapshot.revision}</dd><dt>Alasan berhenti yang tercatat</dt><dd>{analysis.result.simulation?.stop_reason ?? analysis.result.stop_reason ?? "Belum tersedia"}</dd></dl>
    <h3>Pemeriksaan spesialis</h3>{runs.length ? runs.map((run, index) => <p key={`${run.role}:${index}`}>{run.role} · {statusLabel(run.status ?? "not_run")}</p>) : <p>Belum ada status pemeriksaan tersimpan.</p>}
    <details><summary>Penggunaan dan biaya yang tercatat</summary><pre>{JSON.stringify(analysis.result.usage ?? analysis.result.simulation?.usage ?? {}, null, 2)}</pre><p>Biaya hanya diketahui jika dilaporkan provider. Reservasi anggaran bukan tagihan akhir.</p></details>
  </section>;
}
