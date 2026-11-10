import { useSyncExternalStore } from "react";

const key = "pakar:workspace-projects:v1";
const event = "pakar-workspace-projects";
const empty: string[] = [];
let ids = empty;
try {
  const saved: unknown = JSON.parse(localStorage.getItem(key) ?? "[]");
  if (Array.isArray(saved)) ids = [...new Set(saved.filter((id): id is string => typeof id === "string" && /^business_[a-zA-Z0-9]+$/.test(id)))];
} catch { /* Keep the current workspace in memory when storage is unavailable. */ }
function subscribe(callback: () => void) {
  window.addEventListener(event, callback);
  return () => window.removeEventListener(event, callback);
}
export const useWorkspaceProjectIds = () => useSyncExternalStore(subscribe, () => ids, () => empty);
export function rememberBusinessProject(id: string) {
  if (ids.includes(id)) return;
  ids = [...ids, id];
  try { localStorage.setItem(key, JSON.stringify(ids)); } catch { /* Keep the saved project visible during this session. */ }
  window.dispatchEvent(new Event(event));
}
