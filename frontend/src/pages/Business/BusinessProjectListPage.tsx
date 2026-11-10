import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { BusinessLayout } from "../../components/AppShell/BusinessLayout";
import { demoIntakePath, workspaceAnalysisPath, workspaceProjectPath } from "./demoWorkspace";
import { BusinessResultIcon } from "./BusinessResultIcon";
import { errorText, projectDate, statusLabel } from "./businessFormatting";
import { deleteBusinessProject } from "../../api/business";
import { demoProjectId } from "./demoWorkspace";
import { previewText } from "./resultSummary";
import { useBusinessProjects } from "./useBusinessProjects";
import "./BusinessHome.css";
import "./Business.css";
import "./BusinessProjects.css";

export function BusinessProjectListPage() {
  const query = useBusinessProjects();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [deleteNotice, setDeleteNotice] = useState("");
  const client = useQueryClient();
  const removal = useMutation({ mutationFn: deleteBusinessProject, onSuccess: (result, id) => {
    client.removeQueries({ predicate: query => query.queryKey[0] === "business" && (query.queryKey.includes(id) || (query.state.data as { project_id?: string } | undefined)?.project_id === id) });
    setConfirmDelete(null);
    setDeleteNotice(result.cleanup_pending ? "Project dihapus. Sebagian berkas server belum berhasil dibersihkan; hubungi pengelola." : "Project berhasil dihapus.");
  } });
  const projects = query.projects.filter(project => {
    const state = project.ongoing_analysis_count ? "running" : project.latest_analysis?.status ?? "draft";
    return `${project.context.name} ${project.context.decision_question}`.toLowerCase().includes(search.toLowerCase()) && (status === "all" || state === status);
  });
  return <BusinessLayout title="Project" subtitle="Semua ide, analisis, dan langkah berikutnya dalam satu ruang kerja." actions={<Link className="pakar-action pakar-action-outline" to={demoIntakePath}>Coba demo<BusinessResultIcon name="arrow" /></Link>}>
    <section className="pakar-projects" aria-label="Daftar project">
      {deleteNotice && <p role="status">{deleteNotice}</p>}
      {removal.isError && <p className="pakar-project-delete-error" role="alert">{errorText(removal.error)}</p>}
      <div className="pakar-project-controls"><label>Cari project<input type="search" placeholder="Cari nama atau ide bisnis…" value={search} onChange={event => setSearch(event.target.value)} /></label><label>Status<select value={status} onChange={event => setStatus(event.target.value)}><option value="all">Semua status</option><option value="draft">Belum dianalisis</option><option value="running">Berjalan</option><option value="completed">Selesai</option><option value="partial">Selesai sebagian</option><option value="failed">Gagal</option><option value="cancelled">Dibatalkan</option></select></label>{query.enabled && <button type="button" className="pakar-action pakar-action-outline" disabled={query.isFetching} onClick={() => query.refetch()}>{query.isFetching ? "Memuat…" : "Perbarui"}</button>}</div>
      {query.loading && <p className="pakar-home-state" role="status">Memuat project tersimpan…</p>}
      {(query.isError || query.connectionError) && <p className="pakar-home-state pakar-home-state-error" role="alert">{query.connectionError || "Project belum dapat dimuat. Periksa koneksi lalu tekan Perbarui."}</p>}
      {query.available && !query.projects.length && <div className="pakar-project-empty"><h2>Belum ada project yang dibuka.</h2><p>Tekan Coba demo untuk membuka dan menampilkan project Pepsodent di sini.</p><Link className="pakar-action pakar-action-coral" to={demoIntakePath}>Coba demo<BusinessResultIcon name="arrow" /></Link></div>}
      {query.available && !!query.projects.length && !projects.length && <p className="pakar-home-state">Tidak ada project yang sesuai dengan pencarian ini.</p>}
      <div className="pakar-project-grid">{projects.map(project => {
        const state = project.ongoing_analysis_count ? "running" : project.latest_analysis?.status ?? "draft";
        const needsValidation = (project.latest_analysis?.findings ?? []).filter(finding => finding.status === "NEEDS_VALIDATION" && finding.event_ids.length > 0).length;
        return <article className="pakar-project-card" key={project.id}><div className="pakar-project-card-heading"><span className={`business-status ${state}`}>{state === "draft" ? "Belum dianalisis" : statusLabel(state)}</span><span>{project.analysis_count} analisis</span></div><h2><Link to={workspaceProjectPath(project.id)}>{project.context.name}</Link></h2><p>{previewText(project.context.decision_question, 185)}</p><div className="pakar-project-meta"><span>Diperbarui {projectDate(project.activity_at)}</span>{needsValidation > 0 && <span className="pakar-tag pakar-tag-purple">{needsValidation} perlu validasi</span>}</div><div className="pakar-project-card-actions"><Link className="pakar-action pakar-action-outline" to={workspaceProjectPath(project.id)}>Buka project</Link>{project.latest_analysis && <Link className="pakar-action pakar-action-yellow" to={workspaceAnalysisPath(project.latest_analysis.id)}>Lihat hasil<BusinessResultIcon name="arrow" /></Link>}{project.id !== demoProjectId && <button type="button" className="pakar-action pakar-action-outline pakar-project-delete" disabled={removal.isPending || project.ongoing_analysis_count > 0} title={project.ongoing_analysis_count > 0 ? "Batalkan atau selesaikan analisis aktif terlebih dahulu" : undefined} onClick={() => { removal.reset(); setDeleteNotice(""); setConfirmDelete(project.id); }}>Hapus project</button>}</div>{confirmDelete === project.id && <div className="pakar-project-delete-confirm"><p>Hapus <strong>{project.context.name}</strong> beserta dokumen, chat, dan hasil analisisnya? Data tidak dapat dipulihkan dan akan hilang dari workspace bersama.</p><div className="pakar-project-card-actions"><button type="button" className="pakar-action pakar-action-coral" disabled={removal.isPending} onClick={() => removal.mutate(project.id)}>{removal.isPending ? "Menghapus..." : "Hapus permanen"}</button><button type="button" className="pakar-action pakar-action-outline" disabled={removal.isPending} onClick={() => { removal.reset(); setConfirmDelete(null); }}>Batal</button></div></div>}</article>;
      })}</div>
    </section>
  </BusinessLayout>;
}
