import { useSyncExternalStore } from "react";
import { publicDemoOnly } from "../../config/publicDemo";

const key = "pakar:pepsodent-demo-opened";
let opened = false;
try { opened = localStorage.getItem(key) === "true" || sessionStorage.getItem(key) === "true"; } catch { /* In-memory state is sufficient. */ }
const subscribe = (callback: () => void) => {
  window.addEventListener("pakar-demo-opened", callback);
  return () => window.removeEventListener("pakar-demo-opened", callback);
};
export const useDemoOpened = () => useSyncExternalStore(subscribe, () => opened, () => false);
export function activatePepsodentDemo() {
  try { localStorage.setItem(key, "true"); } catch { /* Keep this session in memory. */ }
  if (opened) return;
  opened = true;
  window.dispatchEvent(new Event("pakar-demo-opened"));
}
export const demoProjectId = "pepsodent-demo";
export const demoAnalysisId = "pepsodent-demo-analysis";
export const demoReplayPath = publicDemoOnly ? "/?view=process" : "/business/demo?view=process";
export function workspaceAnalysisPath(id: string, tab = "summary", finding?: string) {
  const base = id === demoAnalysisId ? (publicDemoOnly ? "/?view=result" : "/business/demo?view=result") : `/business/analyses/${encodeURIComponent(id)}?view=result`;
  return `${base}&tab=${encodeURIComponent(tab)}${finding ? `&finding=${encodeURIComponent(finding)}` : ""}`;
}
export const workspaceProjectPath = (id: string) => id === demoProjectId ? workspaceAnalysisPath(demoAnalysisId) : `/business/projects/${encodeURIComponent(id)}?tab=chat`;
