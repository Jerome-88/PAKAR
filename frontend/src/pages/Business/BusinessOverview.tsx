import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { BusinessAnalysis, BusinessEvent, StanceValue } from "../../api/business";
import { BusinessExecutiveSummary } from "./BusinessExecutiveSummary";
import { BusinessResultGraph } from "./BusinessResultGraph";
import { SpecialistContributions } from "./SpecialistContributions";
import { responseSummary, stanceLabels } from "./resultSummary";
import "./BusinessOverview.css";
import "./BusinessTeam.css";

const categories: StanceValue[] = ["support", "oppose", "conditional", "undecided"];
type Group = StanceValue | "unrecorded" | "all";

export function BusinessOverview({ analysis, events, showTab, showFollowUp = true }: { analysis: BusinessAnalysis; events: BusinessEvent[]; showTab: (tab: string) => void; showFollowUp?: boolean }) {
  const [, setSearchParams] = useSearchParams();
  const openFinding = (id: string) => setSearchParams(previous => { const next = new URLSearchParams(previous); next.set("tab", "findings"); next.set("finding", id); return next; });
  const [scope, setScope] = useState("all");
  const [group, setGroup] = useState<Group>("all");
  const personas = analysis.input_snapshot.personas;
  const summary = useMemo(() => responseSummary(events, scope === "customers" ? personas.filter(p => p.role === "customer") : personas, analysis.result.simulation?.stances), [events, personas, scope, analysis.result.simulation?.stances]);
  const visible = useMemo(() => summary.people.filter(p => group === "all" || p.stance === group), [summary.people, group]);
  const { counts, total } = summary;

  return <section className="business-overview" aria-label="Ringkasan hasil">
    <div className="overview-positions" aria-label="Jumlah sikap persona">{categories.map(stance => <button type="button" key={stance} aria-label={`${counts[stance]} ${stanceLabels[stance]}`} aria-pressed={group === stance} onClick={() => setGroup(stance)}><strong>{counts[stance]}</strong><span>{stanceLabels[stance]}</span></button>)}</div>
    <div className="overview-scope"><button type="button" className="business-text-button" aria-pressed={group === "all"} onClick={() => setGroup("all")}>Semua persona ({total})</button>{personas.some(p => p.role === "customer") && <label><span>Kelompok persona</span><select value={scope} onChange={e => { setScope(e.target.value); setGroup("all"); }}><option value="all">Semua stakeholder</option><option value="customers">Calon pembeli saja</option></select></label>}</div>
    <p className={`overview-filter-status${group === "all" && !counts.unrecorded ? " visually-quiet" : ""}`} role="status">{group === "all" ? `${visible.length} persona dalam kelompok ini` : `${visible.length} persona · ${stanceLabels[group]}`}{counts.unrecorded > 0 && <> · <button type="button" className="business-text-button" aria-pressed={group === "unrecorded"} onClick={() => setGroup("unrecorded")}>{counts.unrecorded} persona belum memiliki catatan sikap.</button></>}</p>
    <BusinessResultGraph summaryId="executive-summary" key={`${scope}:${group}`} people={visible} events={events} claims={analysis.input_snapshot.claims} findings={analysis.result.findings} showDiscussion={() => showTab(analysis.input_snapshot.config.interaction_mode === "swarm" ? "swarm" : "timeline")} />
    <BusinessExecutiveSummary analysis={analysis} events={events} summary={summary} customerOnly={scope === "customers"} showChat={showFollowUp ? () => showTab("chat") : undefined} onFinding={openFinding} />
    <SpecialistContributions analysis={analysis} events={events} />
  </section>;
}
