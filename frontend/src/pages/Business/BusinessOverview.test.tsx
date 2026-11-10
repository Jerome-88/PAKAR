import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import type { BusinessAnalysis, BusinessEvent, BusinessFinding, BusinessPersona, SwarmStance } from "../../api/business";
import { BusinessOverview } from "./BusinessOverview";
import { BusinessText } from "./BusinessText";
import { BusinessResultGraph } from "./BusinessResultGraph";
import { discussionFindings, formatBusinessAmount, readableText, recordedConnections, responseSummary } from "./resultSummary";

const persona = (id: string, role = "customer"): BusinessPersona => ({ id, name: `Persona ${id}`, role, stakeholder_type: "direct", goals: [], motivations: [], constraints: [], knowledge: [], interests: [], relationships: [], provenance: {}, discovery_rationale: "", active: true, reviewed: false, revision: 1 });
const state = (stance: SwarmStance["stance"], reason = "Alasan belum terverifikasi"): SwarmStance => ({ stance, stance_reason: reason, stance_history: [] });
const event = (sequence: number, actor_id: string, after: SwarmStance["stance"]): BusinessEvent => ({ id: `e${sequence}`, sequence, round: sequence, actor_id, target_id: "all", kind: "post_message", parent_event_ids: [], rationale: "", stance_update: { before: "undecided", after, reason: "Alasan dari pesan", influenced_by_event_ids: [] } });
const analysis = (personas: BusinessPersona[], stances: Record<string, SwarmStance>): BusinessAnalysis => ({
  id: "demo", project_id: "project", baseline_id: null, status: "completed", stage: "completed", created_at: "2026-11-03",
  input_snapshot: { revision: 1, context: { name: "Produk usulan", industry: "FMCG", region: "Indonesia", target_customer: "Calon pembeli", decision_question: "Apa yang perlu diuji?", data_classification: "synthetic" }, claims: [], personas, config: { engine: "oasis", rounds: 3, interaction_mode: "swarm" } },
  result: { simulation: { stances } as BusinessAnalysis["result"]["simulation"] },
});

describe("simple outcome summary", () => {
  it("surfaces discussion-linked gaps without input-register boilerplate or rejected references", () => {
    const finding = (id: string, title: string, event_ids: string[], severity = "HIGH"): BusinessFinding => ({ id, title, event_ids, severity, category: "interaction", status: "NEEDS_VALIDATION", origin: "simulation", author: "Market Agent", claim_ids: [], persona_ids: [], evidence_ids: [], calculation_ids: [], reasoning: "Penjelasan", confidence: "low", evidence_gaps: [], next_validation: "Uji konsep", owner_suggestion: "Tim produk" });
    const items = [finding("registry", "Input biaya belum lengkap", []), finding("actual", "Mekanisme belum jelas", ["e1"]), finding("rejected", "Tidak boleh muncul", ["e2"]), finding("duplicate", "mekanisme belum jelas", ["e1"], "LOW")];
    const before = structuredClone(items);
    const selected = discussionFindings(items, [event(1, "a", "undecided"), { ...event(2, "b", "oppose"), kind: "action_rejected" }]);
    expect(selected.map(f => f.id)).toEqual(["actual"]);
    expect(items).toEqual(before);
  });
  it("counts final individuals, keeps conditional separate, and never treats missing data as opposition", () => {
    const people = [persona("a"), persona("b"), persona("c"), persona("d"), persona("missing")];
    const summary = responseSummary([event(1, "a", "oppose"), event(2, "a", "support"), event(3, "a", "support")], people, { a: state("support"), b: state("oppose"), c: state("conditional"), d: state("undecided") });
    expect(summary.counts).toEqual({ support: 1, oppose: 1, conditional: 1, undecided: 1, unrecorded: 1 });
    expect(summary.total).toBe(5);
    expect(responseSummary([], [persona("empty")]).counts.oppose).toBe(0);
  });

  it("orders fallback events and excludes rejected changes, duplicate IDs and inactive profiles", () => {
    const rejected = { ...event(4, "a", "oppose"), kind: "action_rejected" };
    const summary = responseSummary([event(3, "a", "support"), event(1, "a", "oppose"), rejected], [persona("a"), persona("a"), { ...persona("inactive"), active: false }]);
    expect(summary.total).toBe(1);
    expect(summary.counts.support).toBe(1);
  });

  it("does not infer a vote from a financial decision", () => {
    const legacy = { ...event(1, "a", "support"), stance_update: undefined, state_after: { version: 1, position: "terms_accepted" } };
    expect(responseSummary([legacy], [persona("a")]).counts.unrecorded).toBe(1);
  });

  it("draws actual directed interactions and replies without inventing broadcast or rejected links", () => {
    const people = responseSummary([], [persona("a"), persona("b"), persona("c")]).people;
    const messages = [event(1, "a", "undecided"), { ...event(2, "b", "undecided"), reply_to: "e1" }, { ...event(3, "a", "support"), target_id: "b" }, { ...event(4, "c", "oppose"), target_id: "a", kind: "action_rejected" }];
    const connections = recordedConnections(messages, people);
    expect(connections).toHaveLength(1);
    expect(connections[0]).toMatchObject({ source: "a", target: "b" });
    expect([...connections[0].eventIds]).toEqual(["e2", "e3"]);
    expect(recordedConnections(messages, people.filter(p => p.persona.id !== "b"))).toEqual([]);
  });

  it("opens the matching recorded reason by keyboard and keeps the selected persona after new messages", () => {
    const people = [persona("a"), persona("b")];
    const row = analysis(people, { a: state("support", "Manfaat konsep menarik"), b: state("conditional", "Perlu uji formula lebih dulu") });
    const { rerender } = render(<MemoryRouter><BusinessOverview analysis={row} events={[]} showTab={vi.fn()} /></MemoryRouter>);
    const node = screen.getByRole("button", { name: "Lihat alasan Persona b: Bersyarat" });
    fireEvent.keyDown(node, { key: "Enter" });
    expect(node).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Perlu uji formula lebih dulu")).toBeVisible();
    rerender(<MemoryRouter><BusinessOverview analysis={row} events={[event(1, "a", "support")]} showTab={vi.fn()} /></MemoryRouter>);
    expect(screen.getByRole("combobox", { name: "Lihat persona" })).toHaveValue("b");
    fireEvent.click(screen.getByRole("button", { name: "1 Mendukung" }));
    expect(screen.queryByRole("button", { name: "Lihat alasan Persona b: Bersyarat" })).not.toBeInTheDocument();
    expect(screen.getByText("Manfaat konsep menarik")).toBeVisible();
  });

  it("starts measuring when an empty running graph gains its first personas", () => {
    const observe = vi.fn();
    vi.stubGlobal("ResizeObserver", class { observe = observe; disconnect = vi.fn(); });
    try {
      const { rerender } = render(<BusinessResultGraph people={[]} events={[]} showDiscussion={vi.fn()} />);
      expect(observe).not.toHaveBeenCalled();
      rerender(<BusinessResultGraph people={responseSummary([], [persona("a")]).people} events={[]} showDiscussion={vi.fn()} />);
      expect(observe).toHaveBeenCalledWith(screen.getByRole("region", { name: "Graf pendapat persona, dapat digeser dan diperbesar" }));
    } finally { vi.unstubAllGlobals(); }
  });

  it("does not call one recorded supporter a majority of an unfinished group", () => {
    const people = [persona("a"), persona("b"), persona("c"), persona("d")];
    render(<MemoryRouter><BusinessOverview analysis={analysis(people, { a: state("support") })} events={[]} showTab={vi.fn()} /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Sebagian persona belum menyampaikan sikap" })).toBeVisible();
    expect(screen.getByRole("button", { name: /3 persona belum memiliki catatan/ })).toBeVisible();
  });

  it("shows the saved Pepsodent pattern honestly and filters who/why by role and stance", () => {
    const people = Array.from({ length: 8 }, (_, i) => persona(String(i), i < 4 ? "customer" : "operator"));
    const saved = Object.fromEntries(people.map(p => [p.id, state("undecided", p.id === "0" ? '{"reason":"**Mekanisme** belum dijelaskan"}' : "Menunggu informasi produk")]));
    render(<MemoryRouter><BusinessOverview analysis={analysis(people, saved)} events={[]} showTab={vi.fn()} /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Semua persona masih belum memutuskan" })).toBeVisible();
    const counts = screen.getByLabelText("Jumlah sikap persona");
    expect(within(counts).getByRole("button", { name: "0 Mendukung" })).toBeVisible();
    expect(within(counts).getByRole("button", { name: "8 Belum memutuskan" })).toBeVisible();
    expect(screen.getByText("Mekanisme belum dijelaskan")).toBeVisible();
    fireEvent.click(within(counts).getByRole("button", { name: "0 Menolak" }));
    expect(screen.getByText("Belum ada persona dengan sikap ini.")).toBeVisible();
    fireEvent.change(screen.getByRole("combobox", { name: "Kelompok persona" }), { target: { value: "customers" } });
    expect(within(counts).getByRole("button", { name: "4 Belum memutuskan" })).toBeVisible();
    expect(screen.getByText(/4 calon pembeli simulasi/)).toBeVisible();
  });

  it("decodes known JSON envelopes, renders Markdown safely, and keeps unknown numbers unknown", () => {
    expect(readableText(JSON.stringify({ answer: "Penjelasan yang tersimpan" }))).toBe("Penjelasan yang tersimpan");
    expect(readableText("Bukan {JSON} yang valid")).toBe("Bukan {JSON} yang valid");
    expect(formatBusinessAmount("unknown")).toBe("Belum diketahui");
    expect(formatBusinessAmount("")).toBe("Belum diketahui");
    expect(formatBusinessAmount(0)).toBe("0");
    render(<BusinessText value={JSON.stringify({ content: "**Perlu bukti**\n\n- Uji konsep\n- Periksa biaya" })} />);
    expect(screen.getByText("Perlu bukti").tagName).toBe("STRONG");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("never turns model Markdown into tracking images or executable HTML", () => {
    const { container } = render(<BusinessText value={'![Contoh gambar](https://external.invalid/tracker)\n\n<script>window.bad = true</script>\n\n[unsafe](javascript:alert(1))'} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector('a[href^="javascript:"]')).toBeNull();
  });
});
