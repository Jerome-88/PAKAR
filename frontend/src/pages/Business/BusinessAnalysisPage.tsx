import { BusinessOverview } from "./BusinessOverview";
import { BusinessEvidence } from "./BusinessEvidence";
import { BusinessScenarioLab } from "./BusinessScenarioLab";
import { BusinessBlindSpots } from "./BusinessBlindSpots";
import { BusinessResultTabs } from "./BusinessResultTabs";
import { BusinessAnalysisTrail, BusinessRunStatus } from "./BusinessOutcome";
import { BusinessReport } from "./BusinessReport";
import { BusinessResultIcon } from "./BusinessResultIcon";
import { BusinessExecutiveSummary } from "./BusinessExecutiveSummary";
import { AnalysisConversation } from "./AnalysisConversation";
import { BusinessText } from "./BusinessText";
import { formatBusinessAmount } from "./resultSummary";
import { SwarmDiscussion } from "./SwarmDiscussion";
import { SpecialistContinuation } from "./SpecialistContinuation";
import { SpecialistReviewStatus } from "./SpecialistReviewStatus";
import { PersonaAvatar, AgentIdentity } from "../../components/PersonaAvatar/PersonaAvatar";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { AppShell } from "../../components/AppShell/AppShell";
import { businessExportUrl, businessKeys, cancelBusinessAnalysis, getBusinessAnalysis, getBusinessComparison, getBusinessEvents } from "../../api/business";
import type { BusinessAnalysis, BusinessEvent, BusinessFinding } from "../../api/business";
import { Notice } from "./BusinessPages";
import { analysisDateLabel, errorText, statusLabel } from "./businessFormatting";
import "./Business.css";
import { BusinessGraph } from "./BusinessGraph";

const amount = formatBusinessAmount;
const categoryLabel: Record<string, string> = { document: "Dokumen", evidence: "Evidence", stakeholder: "Stakeholder", interaction: "Interaksi", scenario: "Scenario" };
const severityLabel: Record<string, string> = { CRITICAL: "Kritis", HIGH: "Tinggi", MEDIUM: "Sedang", LOW: "Rendah" };
const stageLabel: Record<string, string> = { queued: "Menunggu worker", preparing: "Membuat persona dari dokumen", personas_ready: "Persona siap", evidence: "Pencarian evidence", simulation: "Interaksi stakeholder", interaction: "Interaksi stakeholder", validation: "Validasi specialist", report: "Penyusunan laporan", completed: "Analisis selesai", failed: "Analisis gagal", cancelled: "Analisis dibatalkan" };

function FindingDetail({ finding, analysis, openEvent }: { finding: BusinessFinding; analysis: BusinessAnalysis; openEvent: (id: string) => void }) {
  const claims = analysis.input_snapshot.claims.filter(c => finding.claim_ids.includes(c.id));
  const evidence = analysis.result.evidence?.filter(e => finding.evidence_ids.includes(e.id)) ?? [];
  return <article className="business-finding"><div className="business-row-heading"><div><span className={`business-severity ${finding.severity.toLowerCase()}`}>Prioritas {severityLabel[finding.severity]}</span><span>{categoryLabel[finding.category]}</span></div><span className="business-muted"><AgentIdentity name={finding.author} /></span></div><h3>{finding.title}</h3><BusinessText value={finding.reasoning} /><div className="business-finding-status"><strong>{finding.status === "NEEDS_VALIDATION" ? "Perlu validasi" : finding.status}</strong><span>Keyakinan: {finding.confidence} · Asal: {finding.origin === "simulation" ? "hipotesis simulasi" : finding.origin}</span></div>
    <details><summary>Buka sumber, rantai interaksi dan evidence gaps</summary>
      {claims.map(c => <blockquote key={c.id}>{c.quote}<footer>Claim {c.id} · {c.source.document_id}</footer></blockquote>)}
      {!!finding.event_ids.length && <div className="business-event-links"><strong>Interaksi penyebab</strong>{finding.event_ids.map(id => <button key={id} className="business-text-button" onClick={() => openEvent(id)}>{id}</button>)}</div>}
      {evidence.map(e => <p key={e.id}>{e.provider ?? e.id} · {e.status}{e.url && <> · <a href={e.url} target="_blank" rel="noreferrer">Buka sumber</a></>}<br />{e.reason}</p>)}
      {!!finding.evidence_gaps.length && <><h4>Yang belum diketahui</h4><ul>{finding.evidence_gaps.map(gap => <li key={gap}>{gap}</li>)}</ul></>}
      {!claims.length && !finding.event_ids.length && <p>Temuan ini mencatat asumsi yang belum tersedia, bukan klaim yang telah dibuktikan.</p>}
    </details><div className="business-validation-task"><strong>Tindakan validasi berikutnya</strong><p>{finding.next_validation}</p><span>Penanggung jawab yang disarankan: {finding.owner_suggestion}</span></div>
  </article>;
}

function Timeline({ events, names, compact = false }: { events: BusinessEvent[]; names: Record<string, string>; compact?: boolean }) {
  if (compact) return <section><h2>Diskusi stakeholder</h2><ol className="business-timeline">{events.filter(event => !["action_rejected", "shock", "shock_expired", "abstain"].includes(event.kind)).map(event => <li key={event.id} id={event.id} tabIndex={-1}><span className="business-timeline-round">Ronde {event.round}</span><div><strong className="persona-identity"><PersonaAvatar id={event.actor_id} size={32} />{names[event.actor_id] ?? "Peserta"}</strong>{event.target_id !== "all" && <p className="business-muted">Kepada {names[event.target_id] ?? "peserta"}</p>}<BusinessText value={event.content ?? event.rationale} /></div></li>)}</ol>{!events.length && <p>Belum ada diskusi yang tercatat.</p>}</section>;
  return <ol className="business-timeline">{events.map(event => <li key={event.id} id={event.id} tabIndex={-1}><div className="business-timeline-round">Ronde {event.round}<span>{event.sequence ?? event.kind}</span></div><div><div className="business-row-heading"><strong className="persona-identity"><PersonaAvatar id={event.actor_id === "environment" ? "pakar:system:environment" : event.actor_id} kind={event.actor_id === "environment" ? "agent" : "person"} size={28} /><span>{names[event.actor_id] ?? (event.actor_id === "environment" ? "Kondisi scenario" : event.actor_id)}</span></strong><span className="business-status">{event.kind}</span></div><p>{event.target_id !== "all" && <>Kepada {names[event.target_id] ?? event.target_id}. </>}{event.rationale}</p>{event.amount != null && <p>Nilai usulan/aksi: {amount(event.amount)} — kondisional, belum merupakan transaksi nyata.</p>}
      {event.state_after && <p className="business-state-change">State: {event.state_before?.position} → <strong>{event.state_after.position}</strong> · revisi {event.state_after.version}</p>}
      <details><summary>Jejak audit event</summary><p>{event.id} · simulated / hypothesis</p>{event.parent_event_ids.length ? <div className="business-event-links">{event.parent_event_ids.map(id => <a key={id} href={`#${id}`}>Parent: {id}</a>)}</div> : <p>Tidak merujuk event sebelumnya.</p>}<pre>{JSON.stringify(event, null, 2)}</pre></details>
    </div></li>)}</ol>;
}

function Comparison({ analysis, openEvent }: { analysis: BusinessAnalysis; openEvent: (id: string) => void }) {
  const analysisId = analysis.id;
  const query = useQuery({ queryKey: ["business", "comparison", analysisId], queryFn: () => getBusinessComparison(analysisId) });
  const labels: Record<string, string> = { contribution_margin: "Margin kontribusi (Rp/unit)", break_even_units_monthly: "Break-even (unit/bulan)", profit_monthly: "Profit kondisional (Rp/bulan)" };
  const names = Object.fromEntries(analysis.input_snapshot.personas.map(p => [p.id, p.name]));
  const positions: Record<string, string> = { initial: "Posisi awal", terms_offered: "Mengusulkan syarat supplier", terms_accepted: "Menerima syarat supplier", price_adjusted: "Mengubah harga", express_concern: "Menyampaikan kekhawatiran", request_information: "Meminta informasi", cooperate: "Mengusulkan kerja sama", compete: "Merespons kompetisi" };
  const shock = analysis.input_snapshot.shock;
  const shocks: Record<string, string> = { supplier_cost_increase: "Kenaikan biaya supplier", competitor_price_cut: "Penurunan harga kompetitor", regulation_change: "Perubahan kondisi regulasi" };
  return <section><h2>Baseline dan scenario</h2>{query.isPending && <p role="status">Menghitung perbandingan…</p>}{query.isError && <Notice error>{errorText(query.error)}</Notice>}{query.data && <>
    <Notice>{query.data.notice}</Notice>
    {shock && <div className="business-scenario-context"><h3>Kondisi yang diuji</h3><p><strong>{shocks[shock.kind]}</strong>{shock.kind !== "regulation_change" ? ` ${amount(shock.magnitude_percent)}%` : ""} · {shock.region} · mulai ronde {shock.effective_round} selama {shock.duration_rounds} ronde.</p><p>Strategi: {shock.response_strategy === "match_price" ? "Uji operator menyamai harga pembanding kompetitor" : "Amati respons; harga sendiri tidak otomatis berubah"}.{shock.description && ` ${shock.description}`}</p></div>}
    <Link className="business-text-link" to={`/business/analyses/${query.data.baseline_id}`}>Buka baseline dan sumber aslinya</Link>
    <div className="business-table-wrap"><table className="business-table"><caption>Delta metrik kondisional pada input</caption><thead><tr><th>Metrik</th><th>Baseline</th><th>Scenario</th><th>Perubahan</th></tr></thead><tbody>{query.data.metrics.map(m => <tr key={m.metric}><th>{labels[m.metric] ?? m.metric}</th><td>{amount(m.before)}</td><td>{amount(m.after)}</td><td>{amount(m.delta)}</td></tr>)}</tbody></table></div>
    <h3>Posisi stakeholder dalam kedua run sintetis</h3><div className="business-state-list">{Object.entries(query.data.states_after).map(([id, state]) => <p key={id}><strong>{names[id] ?? "Stakeholder"}</strong><span>{positions[query.data!.states_before[id]?.position] ?? "Belum diketahui"} → {positions[state.position] ?? state.position.replaceAll("_", " ")}</span></p>)}</div>
    <h3>Kandidat finding baru ({query.data.new_findings.length})</h3>{query.data.new_findings.length ? query.data.new_findings.map(f => <FindingDetail key={f.id} finding={f} analysis={analysis} openEvent={openEvent} />) : <p>Tidak ada kategori temuan baru; periksa perubahan pada temuan lintas run.</p>}
    <h3>Temuan lintas run</h3><p>Ringkasan yang sama tidak membuktikan risiko atau evidence-nya tetap sama.</p>{query.data.shared_findings.map(pair => <details className="business-comparison-finding" key={`${pair.after.title}-${pair.after.category}`}><summary>{pair.after.title} · {pair.before.reasoning === pair.after.reasoning && pair.before.severity === pair.after.severity ? "ringkasan tidak berubah" : "ringkasan atau prioritas berubah"}</summary><h4>Baseline · {severityLabel[pair.before.severity]}</h4><p>{pair.before.reasoning}</p><Link to={`/business/analyses/${query.data!.baseline_id}`}>Periksa sumber temuan baseline</Link><h4>Scenario</h4><FindingDetail finding={pair.after} analysis={analysis} openEvent={openEvent} /></details>)}
  </>}</section>;
}

export function BusinessAnalysisPage() {
  const { analysisId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab") ?? "summary";
  const initialTab = ["summary", "chat", "swarm", "findings", "timeline", "evidence", "scenario", "report", "audit"].includes(requestedTab) ? requestedTab : "summary";
  const [chatOpened, setChatOpened] = useState(initialTab === "chat" ? analysisId : null);
  const tab = initialTab;
  const setTab = (next: string) => {
    if (next === "chat" || tab === "chat") setChatOpened(analysisId);
    setSearchParams(previous => { const updated = new URLSearchParams(previous); updated.set("tab", next); return updated; });
  };
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: businessKeys.analysis(analysisId), queryFn: () => getBusinessAnalysis(analysisId), refetchInterval: q => ["queued", "running"].includes(q.state.data?.status ?? "queued") ? 1500 : false });
  const analysis = query.data;
  const active = !analysis || ["queued", "running"].includes(analysis.status);
  const logs = useQuery({ queryKey: ["business", "events", analysisId], queryFn: () => getBusinessEvents(analysisId), enabled: !!analysis, refetchInterval: active ? 1500 : false });
  const cancel = useMutation({ mutationFn: () => cancelBusinessAnalysis(analysisId), onSuccess: () => queryClient.invalidateQueries({ queryKey: businessKeys.analysis(analysisId) }) });
  const names = Object.fromEntries(analysis?.input_snapshot.personas.map(p => [p.id, p.name]) ?? []);
  const events = analysis?.result.simulation?.events ?? logs.data?.items.flatMap(log => log.payload.event ? [log.payload.event] : []) ?? [];
  const swarm = analysis?.input_snapshot.config.interaction_mode === "swarm" || analysis?.result.simulation?.interaction_mode === "swarm-v1";
  const visibleTab = tab;
  const openEvent = (id: string) => { setTab("timeline"); window.setTimeout(() => { const element = document.getElementById(id); element?.scrollIntoView({ behavior: "smooth", block: "center" }); element?.focus({ preventScroll: true }); }, 100); };
  return <AppShell title={analysis?.input_snapshot.context.name ?? "Analisis bisnis"} subtitle={analysis ? analysisDateLabel(analysis.created_at) : "Memuat hasil analisis…"} actions={analysis && <Link className="business-result-back" to="/business"><BusinessResultIcon name="back" />Kembali ke awal</Link>}>
    <div className="business-workspace">{query.isPending && <p role="status">Memuat analisis…</p>}{query.isError && <Notice error>{errorText(query.error)}</Notice>}
      {analysis && <>
        <div className="business-run-header"><div><span className={`business-status ${analysis.status}`}>{statusLabel(analysis.status)}</span><span>{analysis.input_snapshot.personas.length} persona · {analysis.input_snapshot.config.rounds} ronde</span><span>{analysis.input_snapshot.config.engine === "fixture" ? "Demo tanpa AI" : "Simulasi AI"}</span></div>{active ? <button className="button secondary" disabled={cancel.isPending} onClick={() => cancel.mutate()}>Batalkan run</button> : analysis.result.report && <a className="business-result-export" aria-label="Unduh laporan HTML" href={businessExportUrl(analysis.id)}><BusinessResultIcon name="download" /><span>Unduh</span></a>}</div>
        {analysis.status === "partial" && <Notice>{analysis.result.recovery ? "Hasil parsial dipulihkan dari pesan tersimpan. Review specialist AI belum tersedia; temuan tetap perlu diperiksa." : "Hasil belum lengkap. Angka dan alasan di bawah berasal dari diskusi yang tersimpan; periksa status proses sebelum memakainya."}</Notice>}
        {!analysis.input_snapshot.information_policy && analysis.input_snapshot.config.engine === "oasis" && <Notice>Hasil lama ini belum memakai pembatasan brief stakeholder. Buat analisis baru untuk memisahkan data internal dari informasi yang dibagikan.</Notice>}
        {analysis.result.error && <Notice error>{analysis.result.error}</Notice>}{cancel.isError && <Notice error>{errorText(cancel.error)}</Notice>}
        {active && <section className="business-live" aria-live="polite"><h2>{stageLabel[analysis.stage] ?? "Menyiapkan analisis"}</h2><p>Event tersimpan selama run. Anda dapat meninggalkan halaman dan kembali ke analisis yang sama.</p><ol>{logs.data?.items.filter(log => log.payload.message).slice(-4).map(log => <li key={log.sequence}>{log.payload.message}</li>)}</ol><p>{events.length} event sudah tercatat.</p></section>}
        <BusinessResultTabs value={tab} onChange={setTab} />
        {!active && <BusinessRunStatus analysis={analysis} />}
        {visibleTab === "report" && <BusinessReport analysis={analysis} openEvent={openEvent} />}
        {visibleTab === "summary" && <BusinessOverview key={analysis.id} analysis={analysis} events={events} showTab={setTab} />}
        {(visibleTab === "chat" || chatOpened === analysis.id) && <div hidden={visibleTab !== "chat"}><AnalysisConversation key={analysis.id} analysis={analysis} /></div>}
        {visibleTab === "swarm" && (swarm ? <SwarmDiscussion compact events={events} personas={analysis.input_snapshot.personas} stances={analysis.result.simulation?.stances} openEvent={openEvent} /> : <Timeline compact events={events} names={names} />)}
        {visibleTab === "findings" && <BusinessBlindSpots analysis={analysis} onBack={() => setTab("summary")} onDiscussion={() => setTab("swarm")} />}
        {visibleTab === "timeline" && <><BusinessGraph analysis={analysis} openEvent={openEvent} /><BusinessExecutiveSummary analysis={analysis} events={events} showChat={() => setTab("chat")} /><h2>Interaksi dan perubahan state</h2><p>Penawaran, penerimaan, dan respons dicatat terpisah. Jejak ini menjelaskan asal hipotesis; bukan transaksi nyata.</p>{!events.length ? <p>Belum ada interaksi yang tercatat.</p> : <Timeline events={events} names={names} />}</>}
        {visibleTab === "evidence" && <BusinessEvidence analysis={analysis} />}
        {visibleTab === "scenario" && (active || !analysis.result.simulation ? <Notice>Selesaikan analisis sebelum menjalankan atau membandingkan scenario.</Notice> : analysis.baseline_id ? <Comparison analysis={analysis} openEvent={openEvent} /> : <BusinessScenarioLab key={analysis.id} analysis={analysis} allowAI />)}
        {visibleTab === "audit" && <BusinessAnalysisTrail analysis={analysis} />}
        {analysis.status === "partial" && <section className="business-result-recovery"><SpecialistContinuation key={analysis.id} analysis={analysis} /><SpecialistReviewStatus analysis={analysis} /></section>}
      </>}
    </div>
  </AppShell>;
}
