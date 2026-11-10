import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { BusinessAnalysis } from "../../api/business";
import { SpecialistReviewStatus } from "./SpecialistReviewStatus";

const analysis = { result: { agent_runs: [
  { role: "Market Agent", phase: "specialist", status: "completed" },
  { role: "Finance Agent", phase: "specialist", status: "failed", status_code: 429 },
  { role: "Legal/Compliance Agent", execution_kind: "deterministic_checks", status: "completed" },
  { role: "Risk Agent", phase: "specialist", status: "completed" },
  { role: "Risk Agent", status: "failed", message: "Invalid finding reference" },
] } } as BusinessAnalysis;

describe("specialist review status", () => {
  it("separates rate limits, deterministic checks and rejected model outputs", () => {
    render(<SpecialistReviewStatus analysis={analysis} />);
    const table = screen.getByRole("table", { name: "Hasil review specialist" });
    expect(within(table).getAllByRole("row")).toHaveLength(5);
    expect(within(within(table).getByRole("row", { name: /^Market Agent/ })).getByText("Selesai")).toBeInTheDocument();
    expect(within(table).getByText(/HTTP 429/)).toBeInTheDocument();
    expect(within(within(table).getByRole("row", { name: /^Legal\/Compliance Agent/ })).getByText("Belum ada hasil")).toBeInTheDocument();
    expect(within(within(table).getByRole("row", { name: /^Risk Agent/ })).getByText("Belum selesai")).toBeInTheDocument();
    expect(within(table).getByText(/keluarannya ditolak validator/)).toBeInTheDocument();
    expect(screen.getByText(/Tidak ada retry AI otomatis/)).toBeInTheDocument();
  });
  it("shows recorded timeout and budget causes without guessing unspecified failures", () => {
    render(<SpecialistReviewStatus analysis={{ ...analysis, result: { agent_runs: [
      { role: "Market Agent", phase: "specialist", status: "failed", failure_kind: "timeout" },
      { role: "Finance Agent", status: "failed", error_type: "BudgetExceeded" },
      { role: "Legal/Compliance Agent", phase: "specialist", status: "failed", status_code: 503 },
      { role: "Risk Agent", phase: "specialist", status: "failed" },
    ] } }} />);
    expect(screen.getByText("Provider tidak merespons dalam batas waktu.")).toBeInTheDocument();
    expect(screen.getByText(/jenis batas tidak dirinci/)).toBeInTheDocument();
    expect(screen.getByText(/HTTP 503/)).toBeInTheDocument();
    expect(screen.getByText(/rincian penyebab tidak tersedia/)).toBeInTheDocument();
  });
  it("does not present deterministic-only checks as AI specialist coverage", () => {
    render(<SpecialistReviewStatus analysis={{ ...analysis, result: { agent_runs: analysis.result.agent_runs?.filter(entry => entry.execution_kind === "deterministic_checks") } }} />);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
  it("labels completed inherited reviews without implying new inference", () => {
    render(<SpecialistReviewStatus analysis={{ ...analysis, result: { agent_runs: [{ role: "Market Agent", phase: "inherited_specialist", status: "completed" }] } }} />);
    expect(screen.getByText(/hasil dipakai kembali tanpa panggilan AI baru/)).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /^Market Agent/ })).toHaveTextContent("Selesai");
  });
});
