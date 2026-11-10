import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "../../test/server";
import type { BusinessAnalysis, BusinessReport as Report } from "../../api/business";
import { BusinessReport } from "./BusinessReport";

const context = { name: "Kedai contoh", industry: "Kopi", region: "Bandung", target_customer: "Mahasiswa", decision_question: "Apa yang perlu divalidasi sebelum ekspansi?", data_classification: "synthetic" as const };
const titles = ["Executive Summary", "Assumption Register", "Top Blind Spots", "Evidence Table", "Contradictions", "Scenario Impact", "Recommended Validation Tasks", "Limitations"];
const ids = ["executive-summary", "assumption-register", "top-blind-spots", "evidence-table", "contradictions", "scenario-impact", "validation-tasks", "limitations"];
const analysis: BusinessAnalysis = { id: "analysis-report", project_id: "project", baseline_id: null, status: "completed", stage: "completed", created_at: "2026-10-29", input_snapshot: { revision: 1, context, claims: [], personas: [], config: { engine: "fixture", rounds: 2 } }, result: { report: { title: "Laporan" } } };
const report: Report = {
  version: "pakar-report-v2", title: "Laporan analisis bisnis — Kedai contoh", analysis_id: analysis.id, status: "completed", created_at: "2026-10-29", context,
  sections: titles.map((title, index) => ({ title, id: ids[index] })),
  summary: { decision_question: context.decision_question, text: "Satu kandidat blind spot perlu diperiksa.", finding_count: 1, high_priority_count: 1, disagreement_count: 0, unavailable_evidence_count: 1, top_finding_ids: ["finding-1"], validation_status: "NEEDS_VALIDATION", next_action: "Wawancarai customer" },
  assumptions: [], findings: [{ id: "finding-1", title: "Demand belum dibuktikan", category: "evidence", severity: "HIGH", status: "NEEDS_VALIDATION", origin: "document", author: "Market Agent", claim_ids: [], persona_ids: [], event_ids: [], evidence_ids: [], calculation_ids: [], reasoning: "Belum ada riset customer.", confidence: "low", evidence_gaps: ["Riset customer"], next_validation: "Wawancarai customer", owner_suggestion: "Peneliti pasar", affected_assumptions: [], supporting_evidence: [], interaction_chain: [], estimated_impact: { status: "UNKNOWN", explanation: "Dampak belum dapat dihitung." }, has_related_calculation: false }],
  evidence: [{ id: "bps", provider: "BPS", status: "UNAVAILABLE", url: "javascript:alert(1)", reason: "Indikator belum dikonfigurasi", related_claim_ids: [] }], contradictions: [],
  scenario: { is_scenario: false, baseline_id: null, shock: null, comparison_available: false, notice: "Ini baseline.", state_changes: [], new_finding_ids: [], metrics: [{ metric: "profit_monthly", label: "Profit kondisional (Rp/bulan)", before: null, after: null, delta: null, status: "UNKNOWN" }] },
  validation_tasks: [{ id: "task-1", finding_id: "finding-1", title: "Demand belum dibuktikan", priority: "HIGH", action: "Wawancarai customer", owner: "Peneliti pasar", evidence_gaps: ["Riset customer"], status: "PROPOSED" }], limitations: ["Respons persona merupakan hipotesis sintetis."],
  appendix: { personas: [], events: [], relationships: [], calculation: { contribution_margin: null, break_even_units_monthly: null, profit_monthly: null, missing_inputs: ["volume_monthly"], inputs: { volume_monthly: null }, status: "MISSING_INPUTS", formulas: { profit_monthly: "margin * volume - fixed" } }, provenance: {}, agent_runs: [], action_validation: {} },
};

function mount(value = analysis) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><BusinessReport analysis={value} openEvent={vi.fn()} /></MemoryRouter></QueryClientProvider>);
}

describe("PRD report", () => {
  it("renders eight sections, unknown metrics, proposed validation tasks and explicit absence of consensus", async () => {
    server.use(http.get("/backend/api/v1/business/analyses/analysis-report/report", () => HttpResponse.json(report)));
    mount();
    await screen.findByRole("heading", { name: "Executive Summary" });
    for (const title of titles) expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    const executive = screen.getByRole("heading", { name: "Executive Summary" }).parentElement!;
    expect(within(executive).getByRole("heading", { name: "Tangani risiko utama sebelum melanjutkan rencana" })).toBeInTheDocument();
    expect(within(executive).getByRole("heading", { name: "Langkah berikutnya" })).toBeInTheDocument();
    expect(within(executive).getByRole("table").closest("details")).not.toHaveAttribute("open");
    await userEvent.click(within(executive).getByText("Lihat konteks dan perhitungan"));
    expect(within(within(executive).getByRole("table", { name: "Metrik kondisional pada input" })).getByRole("cell", { name: "Belum diketahui" })).toBeInTheDocument();
    expect(screen.getByText(/tidak membuktikan adanya konsensus/)).toBeInTheDocument();
    expect(screen.getByText(/Tugas berikut merupakan usulan/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Buka sumber" })).not.toBeInTheDocument();
    expect(screen.getByText("Peneliti pasar")).toBeInTheDocument();
  });

  it("shows an actionable error state and retries the report request", async () => {
    let calls = 0;
    server.use(http.get("/backend/api/v1/business/analyses/analysis-report/report", () => ++calls === 1 ? HttpResponse.json({ message: "Laporan sementara gagal dimuat" }, { status: 503 }) : HttpResponse.json(report)));
    mount();
    await userEvent.click(await screen.findByRole("button", { name: "Coba muat laporan lagi" }));
    expect(await screen.findByRole("heading", { name: "Executive Summary" })).toBeInTheDocument();
  });

  it("keeps an unfinished report distinct from completed findings", () => {
    mount({ ...analysis, status: "running", result: {} });
    expect(screen.getByText(/Laporan sedang disusun/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Executive Summary" })).not.toBeInTheDocument();
  });
});
