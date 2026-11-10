import { useState } from "react";
import { Link } from "react-router-dom";
import { BusinessLayout } from "../../components/AppShell/BusinessLayout";
import { PakarMascot } from "../../components/PakarMascot/PakarMascot";
import { publicDemoOnly } from "../../config/publicDemo";
import { useBusinessProjects } from "./useBusinessProjects";
import { workspaceAnalysisPath, workspaceProjectPath } from "./demoWorkspace";
import { projectDate, savedDemoResultPath } from "./BusinessProjectListPage";
import { friendlyText, previewText } from "./resultSummary";
import { statusLabel } from "./businessFormatting";
import { BusinessResultIcon } from "./BusinessResultIcon";
import "./BusinessHome.css";
import "./BusinessProjects.css";
import "./PakarTheme.css";

function DesignIcon({ name }: { name: "analysis" | "chat" | "arrow" }) {
  return <span className="pakar-design-icon" aria-hidden="true"><img src={`${import.meta.env.BASE_URL}figma/pakar/${name}.svg`} alt="" /></span>;
}
const priorityLabels: Record<string, string> = { CRITICAL: "Kritis", HIGH: "Tinggi", MEDIUM: "Sedang", LOW: "Rendah" };
const specialistLabels: Record<string, string> = { "Market Agent": "Market", "Finance Agent": "Finance", "Legal/Compliance Agent": "Legal / Compliance", "Risk Agent": "Risk" };
const specialistTones: Record<string, string> = { "Market Agent": "blue", "Finance Agent": "yellow", "Legal/Compliance Agent": "purple", "Risk Agent": "coral" };

export function BusinessHomePage() {
  const query = useBusinessProjects();
  const [selectedProject, setSelectedProject] = useState("");
  const [showAll, setShowAll] = useState(false);
  const projects = query.projects;
  const chosen = projects.find(project => project.id === selectedProject) ?? projects.find(project => project.latest_analysis) ?? projects[0];
  const latest = chosen?.latest_analysis;
  const priority: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
  const findings = projects.flatMap(project => (project.latest_analysis?.findings ?? []).filter(finding => finding.status === "NEEDS_VALIDATION" && finding.event_ids.length > 0).map(finding => ({ project, finding, analysisId: project.latest_analysis!.id }))).sort((a, b) => (priority[a.finding.severity] ?? 4) - (priority[b.finding.severity] ?? 4));
  const metrics = [
    { label: "Total project", value: projects.length, detail: `${projects.reduce((sum, project) => sum + project.analysis_count, 0)} analisis tersimpan` },
    { label: "Analisis selesai", value: projects.reduce((sum, project) => sum + project.completed_analysis_count, 0), detail: "run berstatus selesai" },
    { label: "Sedang berjalan", value: projects.reduce((sum, project) => sum + project.ongoing_analysis_count, 0), detail: "analisis aktif atau antre" },
    { label: "Perlu validasi", value: findings.length, detail: "temuan dari hasil terbaru" },
  ];
  const findingsPath = (analysisId: string, findingId: string) => workspaceAnalysisPath(analysisId, "findings", findingId);
  const projectPath = publicDemoOnly ? "/?view=projects" : "/business/projects";
  return <BusinessLayout home><div className="pakar-home"><main className="pakar-home-main">
    <div className="pakar-home-heading"><div><h1>Overview</h1><p>Ringkasan seluruh project, analisis, dan langkah berikutnya.</p></div><nav className="pakar-home-start" aria-label="Mulai menggunakan PAKAR"><Link className="pakar-action pakar-action-outline" to={savedDemoResultPath}>Coba demo<DesignIcon name="arrow" /></Link>{!publicDemoOnly && <Link className="pakar-action pakar-action-coral" to="/business/new">Analisis ide sendiri<BusinessResultIcon name="zoomIn" /></Link>}</nav></div>
    <section className="pakar-home-stats" aria-label="Ringkasan semua project">{metrics.map(metric => <article className="pakar-stat" key={metric.label}><div className="pakar-stat-label"><DesignIcon name="analysis" /><div><h2>{metric.label}</h2><span>Seluruh project tersimpan</span></div></div><strong>{query.available ? metric.value : "—"}</strong><p>{query.available ? metric.detail : "Data belum tersedia"}</p></article>)}</section>
    {query.loading && <p className="pakar-home-state" role="status">Memuat ringkasan project…</p>}
    {(query.isError || query.connectionError) && <div className="pakar-home-state pakar-home-state-error" role="alert"><p>{query.connectionError || "Ringkasan belum dapat dimuat. Periksa koneksi lalu coba lagi."}</p>{query.enabled && <button className="pakar-action pakar-action-outline" type="button" onClick={() => query.refetch()}>Muat ulang</button>}</div>}
    {!query.loading && !query.available && !query.isError && !query.connectionError && <div className="pakar-project-empty"><h2>{publicDemoOnly ? "Jelajahi contoh hasil PAKAR." : "Buka ruang kerja project Anda."}</h2><p>{publicDemoOnly ? "Demo publik tidak terhubung ke daftar project aplikasi utama." : "Data project ditampilkan setelah ruang kerja tersambung."}</p><Link className="pakar-action pakar-action-yellow" to={publicDemoOnly ? savedDemoResultPath : projectPath}>{publicDemoOnly ? "Coba demo" : "Buka Project"}<DesignIcon name="arrow" /></Link></div>}
    {query.available && !projects.length && <div className="pakar-project-empty"><PakarMascot name="lumi" /><h2>Belum ada project yang dibuka.</h2><p>Tekan Coba demo untuk membuka hasil Pepsodent. Project akan muncul di sini setelah demo dibuka.</p><Link className="pakar-action pakar-action-coral" to={savedDemoResultPath}>Coba demo<BusinessResultIcon name="arrow" /></Link></div>}
    {query.available && chosen && <>
      <div className="pakar-home-context"><label className="pakar-overview-project-picker"><strong>Project yang ditinjau</strong><select value={chosen.id} onChange={event => setSelectedProject(event.target.value)}>{projects.map(project => <option key={project.id} value={project.id}>{project.context.name}</option>)}</select></label><Link to={projectPath}>Lihat semua project<DesignIcon name="arrow" /></Link></div>
      <div className="pakar-home-review"><section className="pakar-latest" aria-labelledby="pakar-latest-title"><div className="pakar-card-label"><span>{latest ? "ANALISIS TERBARU" : "PROJECT TERSIMPAN"}</span><span className={`business-status ${latest?.status ?? "draft"}`}>{latest ? statusLabel(latest.status) : "Belum dianalisis"}</span></div><h2 id="pakar-latest-title">{chosen.context.name}</h2><p className="pakar-latest-description">{previewText(chosen.context.decision_question, 250)}</p><div className="pakar-analysis-note"><div className="pakar-companion"><PakarMascot name="lumi" /><div><strong>Ringkasan project</strong><span>Diperbarui {projectDate(chosen.activity_at)}</span></div></div><p>{chosen.analysis_count} analisis tersimpan{chosen.ongoing_analysis_count > 0 ? ` · ${chosen.ongoing_analysis_count} sedang berjalan.` : "."} {findings.filter(row => row.project.id === chosen.id).length} temuan dari hasil terbaru perlu divalidasi.</p></div><div className="pakar-latest-actions"><Link className="pakar-action pakar-action-outline" to={workspaceProjectPath(chosen.id)}>Buka project<DesignIcon name="chat" /></Link>{latest && <Link className="pakar-action pakar-action-yellow" to={workspaceAnalysisPath(latest.id)}>Lihat graf<DesignIcon name="arrow" /></Link>}</div></section>
        <aside className="pakar-next" aria-labelledby="pakar-next-title"><div className="pakar-card-label"><h2 id="pakar-next-title">LANGKAH BERIKUTNYA</h2><span className="pakar-tag pakar-tag-purple">{findings.length} saran</span></div><div className="pakar-companion"><PakarMascot name="noki" /><div><strong>Validasi lintas project</strong><span>Dari analisis terbaru tiap project</span></div></div><ol className="pakar-next-list">{findings.slice(0, 2).map(({ project, finding, analysisId }) => <li key={`${analysisId}:${finding.id}`}><Link className="pakar-overview-task" to={findingsPath(analysisId, finding.id)}><span className="pakar-tag pakar-tag-purple">{project.context.name}</span><p>{previewText(finding.next_validation || finding.title, 140)}</p><small>{finding.owner_suggestion || "Penanggung jawab belum ditentukan"}</small></Link></li>)}</ol>{!findings.length && <p className="pakar-empty-findings">Belum ada temuan diskusi yang menunggu validasi pada hasil terbaru.</p>}<a className="pakar-action pakar-action-purple" href="#overview-findings">Lihat temuan lintas project<DesignIcon name="arrow" /></a></aside>
      </div>
      <section className="pakar-home-findings" id="overview-findings" aria-labelledby="pakar-findings-title"><div className="pakar-findings-heading"><h2 id="pakar-findings-title">Hal yang perlu diperhatikan</h2><span className="pakar-tag pakar-tag-coral">{findings.length} temuan</span></div><p className="pakar-findings-guide">Temuan yang belum divalidasi dari analisis terbaru setiap project. Prioritas menunjukkan potensi dampak, bukan kepastian kejadian.</p><div className="pakar-finding-grid">{(showAll ? findings : findings.slice(0, 3)).map(({ project, finding, analysisId }) => <article className="pakar-finding-card" key={`${analysisId}:${finding.id}`}><span className={`pakar-tag pakar-tag-${specialistTones[finding.author] ?? "purple"}`}>{specialistLabels[finding.author] ?? finding.author}</span><p className="pakar-overview-finding-project">{project.context.name}</p><h3>{friendlyText(finding.title)}</h3><p className={`pakar-finding-priority priority-${finding.severity.toLowerCase()}`}>Prioritas: <strong>{priorityLabels[finding.severity] ?? finding.severity}</strong></p><div className="pakar-finding-next"><span>LANGKAH BERIKUTNYA</span><p>{previewText(finding.next_validation, 170)}</p></div><Link className="pakar-action pakar-action-outline pakar-overview-review" to={findingsPath(analysisId, finding.id)}>Tinjau temuan<DesignIcon name="arrow" /></Link></article>)}</div>{!findings.length && <p className="pakar-empty-findings">Temuan dari diskusi akan muncul di sini setelah analisis tersedia.</p>}{findings.length > 3 && <button type="button" className="pakar-action pakar-action-outline pakar-overview-more" aria-expanded={showAll} onClick={() => setShowAll(value => !value)}>{showAll ? "Tampilkan lebih sedikit" : `Lihat semua ${findings.length} temuan`}</button>}</section>
    </>}
  </main><footer className="pakar-home-footer"><span>PAKAR · Ruang diskusi untuk keputusan bisnis.</span><Link to={projectPath}>Buka Project</Link></footer></div></BusinessLayout>;
}
