import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { BusinessAnalysis } from "../../api/business";
import { businessKeys, getBusinessCapabilities, getBusinessProject } from "../../api/business";
import { ProjectConversation } from "./ProjectConversation";
import { errorText } from "./businessFormatting";

export function AnalysisConversation({ analysis }: { analysis: BusinessAnalysis }) {
  const client = useQueryClient();
  const project = useQuery({ queryKey: businessKeys.project(analysis.project_id), queryFn: () => getBusinessProject(analysis.project_id) });
  const capabilities = useQuery({ queryKey: ["business", "capabilities"], queryFn: getBusinessCapabilities });
  if (project.isPending || capabilities.isPending) return <p role="status">Menyiapkan chat hasil analisis…</p>;
  if (project.isError || capabilities.isError) return <div className="business-notice is-error" role="alert"><p>{errorText(project.error ?? capabilities.error)}</p><button type="button" className="business-text-button" onClick={() => { void project.refetch(); void capabilities.refetch(); }}>Muat ulang chat</button></div>;
  return <ProjectConversation project={project.data} capabilities={capabilities.data} analysis={analysis} onChanged={() => { void client.invalidateQueries({ queryKey: businessKeys.project(analysis.project_id) }); }} />;
}
