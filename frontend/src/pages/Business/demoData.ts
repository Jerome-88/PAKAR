import type { BusinessAnalysis } from "../../api/business";

export type DemoAnalysis = BusinessAnalysis & { demo?: { public_brief: string; source_note: string; quality_note: string; source_analysis_id: string; model?: string; specialists: { role: string; status: string }[] } };
export const demoQueryKey = ["public-demo", "pepsodent", 6] as const;

export async function loadDemo(): Promise<DemoAnalysis> {
  const response = await fetch(`${import.meta.env.BASE_URL}demos/pepsodent.json`);
  if (!response.ok) throw new Error("Contoh hasil belum dapat dimuat.");
  const data = await response.json();
  if (!Array.isArray(data?.input_snapshot?.personas) || !Array.isArray(data?.result?.simulation?.events)) throw new Error("Berkas contoh hasil tidak lengkap.");
  return data;
}
