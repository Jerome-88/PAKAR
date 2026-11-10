import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { activatePepsodentDemo } from "./demoWorkspace";
import { BusinessEvidence } from "./BusinessEvidence";
import { BusinessScenarioLab } from "./BusinessScenarioLab";
import { Link, useSearchParams } from "react-router-dom";
import { demoQueryKey, loadDemo } from "./demoData";
import { AppShell } from "../../components/AppShell/AppShell";
import { publicDemoOnly } from "../../config/publicDemo";
import { BusinessHomePage } from "./BusinessHomePage";
import { BusinessProjectListPage } from "./BusinessProjectListPage";
import { BusinessBlindSpots } from "./BusinessBlindSpots";
import { BusinessIntakePage, Notice } from "./BusinessPages";
import { BusinessOverview } from "./BusinessOverview";
import { BusinessResultIcon } from "./BusinessResultIcon";
import { BusinessResultTabs } from "./BusinessResultTabs";
import { BusinessProcessReplay } from "./BusinessProcessReplay";
import { BusinessAnalysisTrail, BusinessFinalReport, BusinessRunStatus } from "./BusinessOutcome";
import { SavedProjectConversation } from "./ProjectConversation";
import { SwarmDiscussion } from "./SwarmDiscussion";
import { analysisDateLabel, statusLabel } from "./businessFormatting";
import "./Business.css";
import "./BusinessReport.css";

export function BusinessDemoPage() {
  const [params, setParams] = useSearchParams();
  const view = params.get("view") ?? (params.get("step") === "result" ? "result" : publicDemoOnly ? "home" : "intake");
  const tab = ["summary", "swarm", "chat", "findings", "evidence", "scenario", "report", "audit"].includes(params.get("tab") ?? "") ? params.get("tab")! : "summary";
  const query = useQuery({ queryKey: demoQueryKey, queryFn: loadDemo, enabled: view !== "home" && view !== "projects", staleTime: Infinity, retry: false });
  useEffect(() => { if (view !== "home" && view !== "projects") activatePepsodentDemo(); }, [view]);
  const analysis = query.data;
  const events = analysis?.result.simulation?.events ?? [];
  const showView = (next: string) => { setParams({ view: next }); window.scrollTo({ top: 0, behavior: "instant" }); };
  const showTab = (next: string) => setParams({ view: "result", tab: next });

  if (view === "home") return <BusinessHomePage />;
  if (view === "projects") return <BusinessProjectListPage />;
  if (!analysis) return <AppShell title="Analisis bisnis" subtitle="Memuat contoh Pepsodent tersimpan."><div className="business-workspace">{query.isError ? <><Notice error>Contoh hasil belum dapat dimuat. Periksa koneksi, lalu coba lagi.</Notice><button type="button" className="button secondary" onClick={() => query.refetch()}>Muat ulang demo</button></> : <p role="status">Memuat contoh hasil...</p>}</div></AppShell>;
  if (view === "process") return <AppShell title="Proses analisis Pepsodent" subtitle="Dari ide, persona, hingga langkah validasi."><div className="business-workspace"><BusinessProcessReplay analysis={analysis} onResult={() => showView("result")} /></div></AppShell>;
  if (view === "intake") return <BusinessIntakePage savedDemo={{ analysis, publicBrief: analysis.demo?.public_brief ?? analysis.input_snapshot.information_policy?.public_brief ?? "", onStart: () => showView("process"), onWorkspace: () => showView("workspace") }} />;
  if (view === "workspace") return <AppShell title={analysis.input_snapshot.context.name} subtitle="Ruang ide dan sumber analisis." actions={<button type="button" className="button primary" onClick={() => showView("result")}>Lihat hasil analisis</button>}><div className="business-workspace"><SavedProjectConversation analysis={analysis} onSources={() => showView("intake")} /></div></AppShell>;

  return <AppShell title={analysis.input_snapshot.context.name} subtitle={analysisDateLabel(analysis.created_at)} actions={<Link className="business-result-back" to={publicDemoOnly ? "/" : "/business"}><BusinessResultIcon name="back" />Kembali ke awal</Link>}>
    <div className="business-workspace">
      <div className="business-run-header"><div><span className={`business-status ${analysis.status}`}>{statusLabel(analysis.status)}</span><span>{analysis.input_snapshot.personas.length} persona / {analysis.input_snapshot.config.rounds} ronde</span><span>AI asli tersimpan{analysis.demo?.model ? ` · ${analysis.demo.model}` : ""}</span></div><button type="button" className="business-text-button" onClick={() => showView("intake")}>Input contoh</button></div>
      <Notice>{analysis.demo?.quality_note ?? "Hasil simulasi perlu diperiksa dan divalidasi."}</Notice>
      <button type="button" className="business-text-button" onClick={() => showView("process")}>Putar proses demo dari awal</button>
      <BusinessRunStatus analysis={analysis} />
      <BusinessResultTabs value={tab} onChange={showTab} />
      {tab === "evidence" && <BusinessEvidence analysis={analysis} />}
      {tab === "scenario" && <BusinessScenarioLab analysis={analysis} />}
      {tab === "report" && <BusinessFinalReport analysis={analysis} onFinding={id => setParams({ view: "result", tab: "findings", finding: id })} />}
      {tab === "audit" && <BusinessAnalysisTrail analysis={analysis} />}
      {tab === "findings" && <BusinessBlindSpots analysis={analysis} onBack={() => showTab("summary")} onDiscussion={() => showTab("swarm")} />}
      {tab === "summary" && <BusinessOverview analysis={analysis} events={events} showTab={showTab} />}
      {tab === "swarm" && <><button type="button" className="business-text-button" onClick={() => showTab("summary")}>Kembali ke graf dan ringkasan</button><SwarmDiscussion compact events={events} personas={analysis.input_snapshot.personas} stances={analysis.result.simulation?.stances} openEvent={id => { document.getElementById(id)?.scrollIntoView({ block: "center" }); }} /></>}
      {tab === "chat" && <SavedProjectConversation analysis={analysis} onSources={() => showView("intake")} />}
    </div>
  </AppShell>;
}
