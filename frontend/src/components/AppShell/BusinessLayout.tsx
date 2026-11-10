import { useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Brand } from "../Header/Header";
import { PakarMascot } from "../PakarMascot/PakarMascot";
import { useAuth } from "../../auth/useAuth";
import { authStorageKey } from "../../auth/storageNamespace";
import { publicDemoOnly } from "../../config/publicDemo";
import { useBusinessProjects } from "../../pages/Business/useBusinessProjects";
import { demoProjectId, workspaceProjectPath } from "../../pages/Business/demoWorkspace";
import "../../pages/Business/PakarTheme.css";
import "./BusinessLayout.css";

function SidebarIcon({ name }: { name: "collapse" | "plus" | "overview" | "project" | "chevron" }) {
  return <span className="pakar-sidebar-icon" aria-hidden="true"><img src={`${import.meta.env.BASE_URL}figma/pakar/sidebar-${name}.svg`} alt="" /></span>;
}

type BusinessLayoutProps = { home?: boolean; title?: string; subtitle?: string; actions?: ReactNode; children: ReactNode };

export function BusinessLayout({ home = false, title, subtitle, actions, children }: BusinessLayoutProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const projectQuery = useBusinessProjects();
  const sidebarKey = authStorageKey("business-sidebar-collapsed");
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(sidebarKey) === "true"; } catch { return false; }
  });
  const [expanded, setExpanded] = useState(true);
  const [logoutError, setLogoutError] = useState("");
  const homePath = publicDemoOnly ? "/" : "/business";
  const projectsPath = publicDemoOnly ? "/?view=projects" : "/business/projects";
  const projectList = location.pathname === "/business/projects" || (publicDemoOnly && new URLSearchParams(location.search).get("view") === "projects");
  const inDemo = !projectList && (location.pathname === "/business/demo" || (publicDemoOnly && !home));
  const hasActiveAnalysis = !home && (inDemo || /^\/business\/(analyses|projects)\//.test(location.pathname));
  const activeName = title ?? "Analisis aktif";
  const activePath = `${location.pathname}${location.search}${location.hash}`;
  const currentProject = projectQuery.projects.find(project => (inDemo && project.id === demoProjectId) || location.pathname === `/business/projects/${project.id}` || location.pathname === `/business/analyses/${project.latest_analysis?.id}`);
  const toggle = () => setCollapsed(current => {
    const next = !current;
    try { localStorage.setItem(sidebarKey, String(next)); } catch { /* Keep the preference in memory. */ }
    return next;
  });
  const newAnalysis = publicDemoOnly ? <span className="pakar-sidebar-new is-unavailable" aria-disabled="true" title="Analisis baru tersedia di aplikasi utama"><span className="pakar-sidebar-label">Analisis baru</span><SidebarIcon name="plus" /></span> : <Link className="pakar-sidebar-new" to="/business/new" aria-label="Analisis baru" title="Analisis baru"><span className="pakar-sidebar-label">Analisis baru</span><SidebarIcon name="plus" /></Link>;

  return <div className={`app-shell-business pakar-business-layout${collapsed ? " is-collapsed" : ""}`}>
    <aside className="pakar-sidebar" aria-label="Navigasi ruang bisnis">
      <div className="pakar-sidebar-head"><Brand workspace to={homePath} /><button className="pakar-sidebar-collapse" type="button" onClick={toggle} aria-expanded={!collapsed} aria-controls="pakar-business-sidebar-nav" aria-label={collapsed ? "Perluas sidebar" : "Ciutkan sidebar"} title={collapsed ? "Perluas sidebar" : "Ciutkan sidebar"}><SidebarIcon name="collapse" /></button></div>
      <nav className="pakar-sidebar-nav" id="pakar-business-sidebar-nav" aria-label="Navigasi utama PAKAR">
        {newAnalysis}
        <Link className={`pakar-sidebar-link${home ? " is-active" : ""}`} to={homePath} aria-current={home ? "page" : undefined} aria-label="Overview" title="Overview"><SidebarIcon name="overview" /><span className="pakar-sidebar-label">Overview</span></Link>
        <div className="pakar-sidebar-project-menu"><Link className={`pakar-sidebar-link${projectList || hasActiveAnalysis ? " is-active" : ""}`} to={projectsPath} aria-current={projectList ? "page" : undefined} aria-label="Project" title="Project"><SidebarIcon name="project" /><span className="pakar-sidebar-label">Project</span></Link>{!collapsed && <button className="pakar-sidebar-project-toggle" type="button" aria-label={expanded ? "Tutup daftar project" : "Buka daftar project"} aria-expanded={expanded} aria-controls="pakar-project-shortcuts" onClick={() => setExpanded(value => !value)}><span className={`pakar-sidebar-chevron${expanded ? " is-open" : ""}`}><SidebarIcon name="chevron" /></span></button>}</div>
        {!collapsed && expanded && (!!projectQuery.projects.length || hasActiveAnalysis) && <div className="pakar-sidebar-analysis pakar-sidebar-projects" id="pakar-project-shortcuts">{projectQuery.projects.slice(0, 6).map(project => <Link key={project.id} className={currentProject?.id === project.id ? "is-current" : ""} to={workspaceProjectPath(project.id)} aria-current={currentProject?.id === project.id ? "page" : undefined} title={project.context.name}>{project.context.name}</Link>)}{hasActiveAnalysis && !currentProject && <Link className="is-current" to={activePath} aria-current="page" title={activeName}>{activeName}</Link>}{projectQuery.projects.length > 6 && <Link to={projectsPath}>Lihat semua project</Link>}</div>}
      </nav>
      <div className="pakar-sidebar-footer"><PakarMascot name="noki" /><div className="pakar-sidebar-label"><strong>{user && !user.shared ? user.name : "Workspace PAKAR"}</strong><span>{user && !user.shared ? "Ruang analisis bisnis" : "Ruang kerja bersama"}</span></div></div>
    </aside>
    <div className="pakar-business-content">
      <header className="pakar-mobile-header"><div><Brand workspace to={homePath} />{newAnalysis}</div><nav aria-label="Navigasi bisnis seluler"><Link to={homePath} aria-current={home ? "page" : undefined}>Overview</Link><Link to={projectsPath} aria-current={projectList ? "page" : undefined}>Project</Link>{hasActiveAnalysis && <Link className="pakar-mobile-current" to={activePath} aria-current="page" title={activeName}>{activeName}</Link>}</nav></header>
      {user && !user.shared && <div className="pakar-business-account"><span>{user.name}</span><button type="button" onClick={async () => { setLogoutError(""); try { await logout(); navigate("/login"); } catch (error) { setLogoutError(error instanceof Error ? error.message : "Gagal keluar dari akun."); } }}>Keluar</button></div>}
      {logoutError && <p className="app-auth-error" role="alert">{logoutError}</p>}
      {home ? children : <main className="app-main"><section className="app-page-header" aria-labelledby="app-page-title"><div><h1 id="app-page-title">{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{actions && <div className="actions">{actions}</div>}</section>{children}</main>}
    </div>
  </div>;
}
