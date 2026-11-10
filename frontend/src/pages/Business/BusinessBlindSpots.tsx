import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { BusinessAnalysis } from "../../api/business";
import { PakarMascot } from "../../components/PakarMascot/PakarMascot";
import { BusinessResultIcon } from "./BusinessResultIcon";
import { BusinessText } from "./BusinessText";
import { friendlyText, previewText } from "./resultSummary";
import "./BusinessBlindSpots.css";

const severityLabels: Record<string, string> = { CRITICAL: "Kritis", HIGH: "Tinggi", MEDIUM: "Sedang", LOW: "Rendah" };
const categoryLabels: Record<string, string> = { document: "Dokumen", evidence: "Bukti & riset", stakeholder: "Stakeholder", interaction: "Interaksi", scenario: "Skenario" };
const confidenceLabels: Record<string, string> = { low: "Rendah", medium: "Sedang", high: "Tinggi" };
const mascots = { "Market Agent": "peb", "Finance Agent": "lumi", "Legal/Compliance Agent": "kubo", "Risk Agent": "noki" } as const;

export function BusinessBlindSpots({ analysis, onBack, onDiscussion }: { analysis: BusinessAnalysis; onBack: () => void; onDiscussion: () => void }) {
  const [params, setParams] = useSearchParams();
  const [severity, setSeverity] = useState("all");
  const [category, setCategory] = useState("all");
  const all = analysis.result.findings ?? [];
  const findings = all.filter(finding => (severity === "all" || finding.severity === severity) && (category === "all" || finding.category === category));
  const finding = findings.find(item => item.id === params.get("finding")) ?? findings[0];
  const selectFinding = (id: string) => setParams(previous => { const next = new URLSearchParams(previous); next.set("finding", id); return next; });
  const claims = analysis.input_snapshot.claims.filter(claim => finding?.claim_ids.includes(claim.id));
  const evidence = (analysis.result.evidence ?? []).filter(item => finding?.evidence_ids.includes(item.id));
  const events = (analysis.result.simulation?.events ?? []).filter(event => finding?.event_ids.includes(event.id) && !["action_rejected", "shock", "shock_expired"].includes(event.kind));
  const names = Object.fromEntries(analysis.input_snapshot.personas.map(persona => [persona.id, persona.name]));
  const mascot = finding ? mascots[finding.author as keyof typeof mascots] ?? "lumi" : "lumi";
  const needed = finding?.evidence_gaps.length ? finding.evidence_gaps : finding?.next_validation ? [finding.next_validation] : [];

  return <section className="business-blindspots" aria-label="Detail blind spot">
    <div className="blindspot-navigation"><button type="button" className="business-text-button" onClick={onBack}><BusinessResultIcon name="back" />Kembali ke ringkasan</button><span>Blind spots</span></div>
    <div className="blindspot-filters"><label>Temuan<select value={finding?.id ?? ""} onChange={event => selectFinding(event.target.value)} disabled={!findings.length}>{!findings.length && <option value="">Tidak ada temuan</option>}{findings.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><label>Prioritas<select value={severity} onChange={event => setSeverity(event.target.value)}><option value="all">Semua prioritas</option>{Object.entries(severityLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label><label>Kategori<select value={category} onChange={event => setCategory(event.target.value)}><option value="all">Semua kategori</option>{[...new Set(all.map(item => item.category))].map(key => <option key={key} value={key}>{categoryLabels[key] ?? key}</option>)}</select></label></div>
    {!finding ? <div className="blindspot-hero"><h2>Belum ada temuan untuk pilihan ini.</h2><p>Temuan akan muncul setelah analisis tersedia, atau coba ubah filter.</p></div> : <>
      <article className="blindspot-hero"><div className="blindspot-badges"><span className="blindspot-category">{categoryLabels[finding.category] ?? finding.category}</span><span className="blindspot-validation"><img src={`${import.meta.env.BASE_URL}figma/pakar/validation-dot.svg`} alt="" />{finding.status === "NEEDS_VALIDATION" ? "Belum divalidasi" : finding.status}</span></div><h2>{friendlyText(finding.title)}</h2><BusinessText value={friendlyText(finding.reasoning)} /><dl className="blindspot-metrics"><div><dt>Prioritas</dt><dd className={finding.severity === "HIGH" || finding.severity === "CRITICAL" ? "is-high" : ""}>{severityLabels[finding.severity] ?? finding.severity}</dd></div><div><dt>Keyakinan yang tercatat</dt><dd>{confidenceLabels[(finding.confidence ?? "").toLowerCase()] ?? finding.confidence ?? "Belum tercatat"}</dd></div><div><dt>Interaksi dirujuk</dt><dd>{events.length} pesan simulasi</dd></div></dl></article>
      <div className="blindspot-layout"><section className="blindspot-assumption"><h3>{claims.length ? "Asumsi yang ditinjau" : "Ide yang ditinjau"}</h3><div className="blindspot-author"><PakarMascot name={mascot} /><div><strong>{finding.author}</strong><span>Peninjau temuan</span></div></div>{claims.length ? claims.map(claim => <blockquote key={claim.id}>{claim.quote}</blockquote>) : <p>{previewText(analysis.input_snapshot.idea?.text ?? analysis.input_snapshot.context.decision_question, 450)}</p>}<p className="blindspot-assumption-note">{claims.length ? "Kutipan berasal dari input analisis. Isi proposal belum berarti sudah terbukti secara independen." : "Tidak ada kutipan asumsi dokumen yang ditautkan pada temuan ini."}</p></section>
        <section className="blindspot-sources"><h3>Bukti &amp; sumber</h3>{claims.map(claim => <article key={claim.id}><h4>{claim.source.document_id}</h4><p className="blindspot-source-locator">{claim.source.locator.page != null ? `Halaman ${claim.source.locator.page}` : claim.source.locator.paragraph != null ? `Paragraf ${claim.source.locator.paragraph}` : "Kutipan dokumen input"}</p><blockquote>{claim.quote}</blockquote></article>)}{evidence.map(item => <article key={item.id}><h4>{item.provider ?? "Sumber rujukan"}</h4><p className="blindspot-source-locator">{item.status}</p>{item.reason && <p>{item.reason}</p>}{item.url && /^https?:\/\//i.test(item.url) && <a href={item.url} target="_blank" rel="noreferrer">Buka sumber</a>}</article>)}{!claims.length && !evidence.length && <p className="blindspot-source-empty">Belum ada bukti dokumen atau sumber eksternal yang ditautkan untuk mendukung temuan ini.</p>}{events.slice(0, 3).map(event => <details key={event.id}><summary>{names[event.actor_id] ?? "Persona"} · Ronde {event.round} · Pesan simulasi</summary><BusinessText value={event.content ?? event.rationale} /></details>)}{events.length > 0 && <button type="button" className="business-text-button" onClick={onDiscussion}>Buka konteks diskusi<BusinessResultIcon name="arrow" /></button>}{(!evidence.length || needed.length > 0) && <p className="blindspot-source-warning"><img src={`${import.meta.env.BASE_URL}figma/pakar/evidence-warning.svg`} alt="" />{evidence.length ? "Periksa dukungan sumber dan kebutuhan validasi di bawah." : "Bukti independen belum ditautkan pada temuan ini."}</p>}</section>
        <section className="blindspot-needed"><h3>{finding.evidence_gaps.length ? "Bukti yang masih diperlukan" : "Validasi berikutnya"}</h3>{needed.length ? <ol>{needed.map((item, index) => <li key={`${index}:${item}`}><span aria-hidden="true">{index + 1}</span><p>{friendlyText(item)}</p></li>)}</ol> : <p>Langkah validasi belum dicatat pada temuan ini.</p>}{finding.owner_suggestion && <p className="blindspot-owner"><strong>Penanggung jawab yang disarankan:</strong> {finding.owner_suggestion}</p>}</section>
      </div>
    </>}
  </section>;
}
