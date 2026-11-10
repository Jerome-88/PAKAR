import { useEffect, useMemo, useRef, useState } from "react";
import type { BusinessAnalysis, BusinessEvent } from "../../api/business";
import { BusinessText } from "./BusinessText";
import { BusinessResultIcon } from "./BusinessResultIcon";
import { discussionFindings, friendlyText, previewText, responseSummary } from "./resultSummary";

export function BusinessExecutiveSummary({ analysis, events, summary, customerOnly = false, showChat, onFinding }: { analysis: BusinessAnalysis; events: BusinessEvent[]; summary?: ReturnType<typeof responseSummary>; customerOnly?: boolean; showChat?: () => void; onFinding?: (id: string) => void }) {
  const [allFindings, setAllFindings] = useState(false);
  const section = useRef<HTMLElement>(null);
  const positions = useMemo(() => summary ?? responseSummary(events, analysis.input_snapshot.personas, analysis.result.simulation?.stances), [summary, events, analysis.input_snapshot.personas, analysis.result.simulation?.stances]);
  const findings = useMemo(() => discussionFindings(analysis.result.findings ?? [], events), [analysis.result.findings, events]);
  const active = ["queued", "running"].includes(analysis.status);
  const { counts, total } = positions;
  let headline = "Pendapat persona masih terbagi";
  if (!total || counts.unrecorded === total) headline = "Sikap persona belum tercatat";
  else if (counts.unrecorded >= total / 2) headline = "Sebagian persona belum menyampaikan sikap";
  else if (counts.undecided === total) headline = "Semua persona masih belum memutuskan";
  else if (counts.conditional > Math.max(counts.support, counts.oppose, counts.undecided)) headline = "Dukungan paling banyak masih bersyarat";
  else if (counts.support > Math.max(counts.oppose, counts.conditional, counts.undecided)) headline = "Lebih banyak persona yang mendukung";
  else if (counts.oppose > Math.max(counts.support, counts.conditional, counts.undecided)) headline = "Lebih banyak persona yang menolak";
  else if (counts.undecided > Math.max(counts.support, counts.oppose, counts.conditional)) headline = "Lebih banyak persona yang belum memutuskan";
  useEffect(() => {
    // A shared link may arrive before the async analysis response mounts this section.
    if (window.location.hash !== "#executive-summary") return;
    section.current?.scrollIntoView({ block: "start", behavior: "instant" });
    section.current?.focus({ preventScroll: true });
  }, []);
  return <section ref={section} id="executive-summary" className="overview-executive-summary" aria-labelledby="overview-executive-title" tabIndex={-1}>
    <div className="overview-executive-header"><h2 id="overview-executive-title">Executive Summary</h2>{showChat && <button type="button" className="business-summary-chat" onClick={showChat}>Diskusikan hasil ini<BusinessResultIcon name="arrow" /></button>}</div>
    <div className="overview-executive-layout"><div className="overview-heading"><div><h3>{headline}</h3><p>{active ? "Posisi sementara" : "Posisi terakhir"} · {total} {customerOnly ? "calon pembeli" : "persona"} simulasi.</p></div></div>
    <section className="overview-priorities" aria-labelledby="overview-priorities-title"><div className="overview-section-heading"><h3 id="overview-priorities-title">Prioritas validasi berikutnya</h3>{findings.length > 3 && <button className="business-text-button" type="button" aria-expanded={allFindings} onClick={() => setAllFindings(value => !value)}>{allFindings ? "Ringkas lagi" : `Lihat semua ${findings.length} poin`}</button>}</div>
      {!findings.length ? <p>{active ? "Poin penting akan muncul setelah diskusi diperiksa." : "Belum ada rangkuman kekurangan dari diskusi ini."}</p> : <ol role="list">{(allFindings ? findings : findings.slice(0, 3)).map(finding => <li key={finding.id}><h4>{friendlyText(finding.title)}</h4><p><strong>Saran:</strong> {previewText(finding.next_validation, 160)}</p><details><summary>Lihat alasan</summary><BusinessText value={friendlyText(finding.reasoning)} />{friendlyText(finding.next_validation).length > 160 && <BusinessText value={friendlyText(finding.next_validation)} />}</details>{onFinding && <button type="button" className="business-text-button" onClick={() => onFinding(finding.id)}>Tinjau blind spot<BusinessResultIcon name="arrow" /></button>}</li>)}</ol>}
    </section></div>
  </section>;
}
