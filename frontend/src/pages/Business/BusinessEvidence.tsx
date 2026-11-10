import { useId, useState } from "react";
import type { BusinessAnalysis, BusinessClaim } from "../../api/business";
import { PakarMascot } from "../../components/PakarMascot/PakarMascot";
import { BusinessText } from "./BusinessText";
import { discussionFindings, formatBusinessAmount, friendlyText, previewText } from "./resultSummary";
import "./BusinessEvidence.css";

type AuditSource = { key: string; title: string; claims: BusinessClaim[]; related: string; period: string; region: string; status?: string; reason: string; url?: string | null };
const statusLabels: Record<string, string> = { VERIFIED: "Dukungan terverifikasi", PARTIAL: "Dukungan sebagian", CONFLICTING: "Dukungan bertentangan", UNAVAILABLE: "Bukti belum tersedia", STALE: "Data perlu diperbarui", NEEDS_VALIDATION: "Perlu validasi" };
const calculationLabels: Record<string, string> = { contribution_margin: "Margin kontribusi", break_even_units_monthly: "Unit untuk balik modal per bulan", profit_monthly: "Laba bulanan" };

function AuditStatus({ status }: { status?: string }) {
  if (!status) return null;
  const partial = status === "PARTIAL" || status === "STALE";
  return <span className={`evidence-audit-status${status === "VERIFIED" ? " is-verified" : partial ? " is-partial" : " is-missing"}`}>
    {status !== "VERIFIED" && <img src={`${import.meta.env.BASE_URL}figma/pakar/${partial ? "evidence-partial-dot.svg" : "evidence-gap-dot.svg"}`} alt="" />}{statusLabels[status] ?? status}
  </span>;
}

export function BusinessEvidence({ analysis }: { analysis: BusinessAnalysis }) {
  const [section, setSection] = useState<"sources" | "calculations">("sources");
  const id = useId();
  const calculation = analysis.result.simulation?.calculation;
  const formulas = Object.entries(calculation?.formulas ?? {});
  const findings = analysis.result.findings ?? [];
  const groups = new Map<string, BusinessClaim[]>();
  for (const claim of analysis.input_snapshot.claims) {
    const key = claim.source.document_id;
    groups.set(key, [...(groups.get(key) ?? []), claim]);
  }
  const sources: AuditSource[] = [...groups].map(([key, claims]) => ({
    key, title: analysis.input_snapshot.documents?.find(document => document.id === key)?.name ?? key,
    claims, related: previewText(claims[0].normalized_text || claims[0].quote, 155),
    period: [...new Set(claims.map(claim => claim.period).filter(Boolean))].join(" · ") || "Periode sumber belum tercatat",
    region: [...new Set(claims.map(claim => claim.region).filter(Boolean))].join(" · ") || "Cakupan sumber belum tercatat",
    status: "NEEDS_VALIDATION",
    reason: claims.every(claim => ["assumption", "forecast", "opinion"].includes(claim.classification))
      ? "Sumber ini berisi asumsi atau proyeksi input. Angka ilustratif bukan harga, biaya, atau hasil riset Pepsodent yang terverifikasi."
      : "Klaim berasal dari dokumen input. Keberadaan dokumen belum membuktikan klaimnya secara independen.",
  }));
  for (const item of analysis.result.evidence ?? []) {
    const related = findings.filter(finding => finding.evidence_ids.includes(item.id));
    sources.push({ key: item.id, title: item.provider ?? "Sumber pendukung", claims: [],
      related: related.length ? related.map(finding => finding.title).join(" · ") : "Kaitan dengan klaim belum tercatat",
      period: item.observed_period || "Periode sumber belum tercatat", region: item.region || "Cakupan sumber belum tercatat",
      status: item.status, reason: item.reason || "Penjelasan dukungan sumber belum tercatat.", url: item.url });
  }
  const gaps = discussionFindings(findings, analysis.result.simulation?.events ?? []).filter(finding => finding.status === "NEEDS_VALIDATION" || finding.evidence_gaps.length > 0);

  return <section className="business-evidence-page" aria-label="Evidence & Calculations">
    <div className="evidence-section-switch" role="tablist" aria-label="Bagian evidence dan perhitungan" onKeyDown={event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === "Home" ? "sources" : event.key === "End" ? "calculations" : section === "sources" ? "calculations" : "sources";
      setSection(next);
      event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next === "sources" ? 0 : 1]?.focus();
    }}>
      <button type="button" role="tab" id={`${id}-sources-tab`} aria-controls={`${id}-sources`} aria-selected={section === "sources"} tabIndex={section === "sources" ? 0 : -1} onClick={() => setSection("sources")}><img className="evidence-section-document" src={`${import.meta.env.BASE_URL}figma/pakar/evidence-reference.svg`} alt="" /><span><strong>Section A:</strong> Evidence &amp; Reference Audit ({sources.length})</span></button>
      <button type="button" role="tab" id={`${id}-calculations-tab`} aria-controls={`${id}-calculations`} aria-selected={section === "calculations"} tabIndex={section === "calculations" ? 0 : -1} onClick={() => setSection("calculations")}><img className="evidence-section-formula" src={`${import.meta.env.BASE_URL}figma/pakar/evidence-formula.svg`} alt="" /><span><strong>Section B:</strong> Formulas &amp; Transparent Calculations ({formulas.length})</span></button>
    </div>
    <div role="tabpanel" id={`${id}-sources`} aria-labelledby={`${id}-sources-tab`} hidden={section !== "sources"}>
      {!sources.length && <div className="evidence-audit-empty"><h2>Belum ada sumber yang ditampilkan.</h2><p>Hasil ini belum memuat kutipan dokumen atau sumber eksternal pada data yang ditampilkan. Catatan validasi di bawah berasal dari temuan simulasi, bukan bukti independen.</p></div>}
      <div className="evidence-audit-grid">{sources.map((source, index) => {
        const related = findings.find(finding => finding.evidence_ids.includes(source.key) || source.claims.some(claim => finding.claim_ids.includes(claim.id)));
        const unavailable = source.status === "UNAVAILABLE" || source.status === "CONFLICTING";
        const operations = related?.author === "Risk Agent";
        return <article className="evidence-audit-card" key={source.key}>
          <div className="evidence-audit-badges"><span className="evidence-source-number">S{String(index + 1).padStart(2, "0")}</span><AuditStatus status={source.status} /></div>
          <h2>{source.title}</h2>
          {!unavailable && <dl className="evidence-audit-metadata"><div><dt>Klaim terkait</dt><dd>{source.related}</dd></div><div><dt>Periode cakupan</dt><dd>{source.period}</dd></div><div><dt>Wilayah / segmentasi</dt><dd>{source.region}</dd></div></dl>}
          <div className={`evidence-audit-note${unavailable ? " is-gap" : operations ? " is-operations" : " is-research"}`}>
            {unavailable ? <h3>Mengapa dukungan sumber ini belum cukup?</h3> : <div className="evidence-note-author"><PakarMascot name={operations ? "noki" : "kubo"} /><div><h3>{related ? related.author : "Data & batas dukungan"}</h3><span>{operations ? "Noki" : "Kubo"}</span></div></div>}
            <BusinessText value={source.reason} />
            {related && related.reasoning !== source.reason && <BusinessText value={friendlyText(related.reasoning)} />}
          </div>
          {source.claims.length > 0 && <details className="evidence-audit-excerpts"><summary>Lihat {source.claims.length} kutipan sumber</summary>{source.claims.map(claim => <blockquote key={claim.id}><BusinessText value={claim.quote} /><footer>{claim.source.locator.page != null ? `Halaman ${claim.source.locator.page}` : claim.source.locator.paragraph != null ? `Paragraf ${claim.source.locator.paragraph}` : "Kutipan input analisis"}</footer></blockquote>)}</details>}
          {source.url && /^https?:\/\//i.test(source.url) && <a className="evidence-source-link" href={source.url} target="_blank" rel="noreferrer">Buka sumber asli</a>}
        </article>;
      })}</div>
      {gaps.length > 0 && <section className="evidence-gap-section" aria-labelledby={`${id}-gaps-title`}><div className="evidence-gap-heading"><h2 id={`${id}-gaps-title`}>Catatan validasi yang tersimpan</h2><p>Catatan ini menjelaskan hal yang masih perlu dibuktikan.</p></div><div className="evidence-audit-grid">{gaps.map((finding, index) => <article className="evidence-audit-card" key={finding.id}><div className="evidence-audit-badges"><span className="evidence-source-number">G{String(index + 1).padStart(2, "0")}</span><AuditStatus status="NEEDS_VALIDATION" /></div><h2>{friendlyText(finding.title)}</h2><div className="evidence-audit-note is-gap"><h3>Yang belum terkonfirmasi</h3><BusinessText value={friendlyText(finding.reasoning)} /></div>{finding.evidence_gaps.length > 0 && <ul className="evidence-gap-list">{finding.evidence_gaps.map((gap, i) => <li key={`${i}:${gap}`}>{friendlyText(gap)}</li>)}</ul>}{finding.next_validation && <div className="evidence-audit-validation"><h3>Validasi berikutnya</h3><BusinessText value={friendlyText(finding.next_validation)} /></div>}</article>)}</div></section>}
    </div>
    <div role="tabpanel" id={`${id}-calculations`} aria-labelledby={`${id}-calculations-tab`} hidden={section !== "calculations"}>
      <div className="evidence-audit-grid">{formulas.map(([key, formula], index) => <article className="evidence-audit-card evidence-formula-card" key={key}><span className="evidence-source-number">C{String(index + 1).padStart(2, "0")}</span><h2>{calculationLabels[key] ?? friendlyText(key)}</h2><div className="evidence-formula-expression"><h3>Formula tersimpan</h3><code>{formula}</code></div><div className="evidence-formula-result"><span>Hasil pada input analisis</span><strong>{formatBusinessAmount(calculation?.[key as "contribution_margin" | "break_even_units_monthly" | "profit_monthly"])}</strong></div></article>)}</div>
      {!formulas.length && <div className="evidence-audit-empty"><h2>Formula belum tersedia pada hasil ini.</h2><p>Formula dan angka hanya ditampilkan jika tersimpan dalam analisis.</p></div>}
      {calculation && <section className="evidence-calculation-snapshot"><h2>Ringkasan perhitungan</h2><dl className="evidence-calculation-results">{(["contribution_margin", "break_even_units_monthly", "profit_monthly"] as const).map(key => <div key={key}><dt>{calculationLabels[key]}</dt><dd>{formatBusinessAmount(calculation[key])}</dd></div>)}</dl>{Object.keys(calculation.inputs).length > 0 && <details><summary>Input perhitungan</summary><dl className="evidence-calculation-inputs">{Object.entries(calculation.inputs).map(([key, value]) => <div key={key}><dt>{friendlyText(key)}</dt><dd>{formatBusinessAmount(value)}</dd></div>)}</dl></details>}{calculation.status === "not_included_in_public_demo" ? <p>Input dan perhitungan finansial tidak disertakan dalam demo publik ini.</p> : calculation.missing_inputs.length > 0 && <p>Input yang masih dibutuhkan: {calculation.missing_inputs.map(friendlyText).join(", ")}</p>}<p>Hasil bersifat kondisional pada input tersimpan. Nilai yang belum diketahui tidak diperlakukan sebagai nol.</p></section>}
    </div>
  </section>;
}

const plannedTitles: Record<string, string> = { scenario: "Scenario Lab", report: "Final Report", audit: "Analysis Trail" };
export function BusinessPlannedTab({ tab }: { tab: string }) {
  return <section className="business-planned-tab"><h2>{plannedTitles[tab] ?? "Menu project"}</h2><p>Bagian ini disiapkan untuk pengembangan berikutnya.</p></section>;
}
