import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/server";
import type { BusinessAnalysis } from "../../api/business";
import { SpecialistContinuation } from "./SpecialistContinuation";

const analysis: BusinessAnalysis = {
  id: "source", project_id: "project", baseline_id: null, status: "partial", stage: "completed", created_at: "2026-10-31",
  input_snapshot: { revision: 1, context: { name: "Kedai", industry: "F&B", region: "Bandung", target_customer: "Pekerja", decision_question: "Apa yang perlu divalidasi?", data_classification: "synthetic" }, personas: [], claims: [], config: { engine: "oasis", rounds: 3 } },
  result: { recovery: { original_execution_status: "failed", specialist_review: "not_run", new_model_calls: 0 } },
};
function mount(value = analysis) {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
    <MemoryRouter initialEntries={["/source"]}><Routes>
      <Route path="/source" element={<SpecialistContinuation analysis={value} />} />
      <Route path="/business/analyses/review" element={<h1>Hasil review lanjutan</h1>} />
    </Routes></MemoryRouter>
  </QueryClientProvider>);
}

describe("specialist continuation", () => {
  it("explains new AI charges and reuses one request key after a transport error", async () => {
    const keys: (string | null)[] = [];
    server.use(http.post("/backend/api/v1/business/analyses/source/specialist-review", async ({ request }) => {
      keys.push(request.headers.get("Idempotency-Key"));
      expect(await request.json()).toEqual({});
      return keys.length === 1 ? HttpResponse.json({ message: "Layanan sementara gagal" }, { status: 503 }) : HttpResponse.json({ id: "review" });
    }));
    mount();
    expect(screen.getByText(/biaya provider/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Jalankan empat specialist AI" }));
    expect(await screen.findByText("Layanan sementara gagal")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Jalankan empat specialist AI" }));
    expect(await screen.findByRole("heading", { name: "Hasil review lanjutan" })).toBeInTheDocument();
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBeTruthy();
    expect(keys[0]).toBe(keys[1]);
  });
  it("links to an existing follow-up without offering another paid start", () => {
    mount({ ...analysis, review_followup: { id: "review", status: "partial" } });
    expect(screen.getByRole("link", { name: "Buka review specialist" })).toHaveAttribute("href", "/business/analyses/review");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
  it("offers an explicit paid review for a saved live discussion whose reviewers never started", () => {
    mount({ ...analysis, result: { simulation: { events: [{ id: "event" }] } } } as BusinessAnalysis);
    expect(screen.getByRole("button", { name: "Jalankan empat specialist AI" })).toBeInTheDocument();
    expect(screen.getByText(/panggilan AI baru dengan biaya provider/)).toBeInTheDocument();
  });
  it("explicitly requests only missing reviews and explains reuse of completed roles", async () => {
    server.use(http.post("/backend/api/v1/business/analyses/source/specialist-review", async ({ request }) => {
      expect(await request.json()).toEqual({ retry_failed: true });
      return HttpResponse.json({ id: "review" });
    }));
    mount({ ...analysis, result: { agent_runs: [{ role: "Market Agent", phase: "specialist", status: "completed" }, { role: "Finance Agent", phase: "specialist", status: "failed", status_code: 429 }] } });
    expect(screen.getByText(/Review yang sudah selesai dan lolos validator dipakai kembali/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Lanjutkan specialist yang belum selesai" }));
    expect(await screen.findByRole("heading", { name: "Hasil review lanjutan" })).toBeInTheDocument();
  });
  it("links the continuation to its original discussion and distinguishes new usage", () => {
    mount({ ...analysis, input_snapshot: { ...analysis.input_snapshot, review_source: { analysis_id: "original" } } });
    expect(screen.getByRole("link", { name: "diskusi run asal" })).toHaveAttribute("href", "/business/analyses/original");
    expect(screen.getByText(/hanya mencakup panggilan specialist baru/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
