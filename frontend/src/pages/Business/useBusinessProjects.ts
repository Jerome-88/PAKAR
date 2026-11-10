import { useQuery } from "@tanstack/react-query";
import type { BusinessProjectSummary } from "../../api/business";
import { getBusinessAnalysis, getBusinessProject } from "../../api/business";
import { useQueries } from "@tanstack/react-query";
import { useWorkspaceProjectIds } from "../../data/businessWorkspace";
import { publicDemoOnly } from "../../config/publicDemo";
import { demoQueryKey, loadDemo } from "./demoData";
import { demoAnalysisId, demoProjectId, useDemoOpened } from "./demoWorkspace";

export function useBusinessProjects() {
  const opened = useDemoOpened();
  const ids = useWorkspaceProjectIds();
  const saved = useQueries({ queries: (publicDemoOnly ? [] : ids).map(id => ({
    queryKey: ["business", "workspace-summary", id],
    queryFn: async (): Promise<BusinessProjectSummary> => {
      const project = await getBusinessProject(id);
      const latest = [...project.analyses].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
      const analysis = latest ? await getBusinessAnalysis(latest.id) : undefined;
      return { ...project, analysis_count: project.analyses.length,
        completed_analysis_count: project.analyses.filter(run => run.status === "completed").length,
        ongoing_analysis_count: project.analyses.filter(run => ["running", "queued"].includes(run.status)).length,
        activity_at: latest?.created_at ?? project.updated_at,
        latest_analysis: analysis ? { ...analysis, findings: analysis.result.findings ?? [] } : null };
    }, retry: false, refetchInterval: 15000,
  })) });
  const query = useQuery({ queryKey: demoQueryKey, queryFn: loadDemo, enabled: opened, retry: false, staleTime: Infinity });
  const analysis = opened ? query.data : undefined;
  const projects: BusinessProjectSummary[] = analysis ? [{
    id: demoProjectId, context: { ...analysis.input_snapshot.context, name: "Pepsodent · Pasta gigi dua rasa" },
    revision: analysis.input_snapshot.revision, created_at: analysis.created_at, updated_at: analysis.created_at, activity_at: analysis.created_at,
    analysis_count: 1, completed_analysis_count: analysis.status === "completed" ? 1 : 0, ongoing_analysis_count: 0,
    latest_analysis: { id: demoAnalysisId, project_id: demoProjectId, status: analysis.status, stage: analysis.stage, created_at: analysis.created_at, findings: analysis.result.findings ?? [] },
  }] : [];
  projects.push(...saved.flatMap(item => item.data ? [item.data] : []));
  projects.sort((a, b) => b.activity_at.localeCompare(a.activity_at));
  return { ...query, projects, available: projects.length > 0 || (!opened && !ids.length), loading: (opened && query.isLoading) || saved.some(item => item.isPending), connectionError: saved.some(item => item.isError) ? "Sebagian project belum dapat dimuat. Coba muat ulang halaman." : undefined, enabled: opened || ids.length > 0 };
}
