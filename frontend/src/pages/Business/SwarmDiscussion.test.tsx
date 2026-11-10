import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { BusinessEvent, BusinessPersona } from "../../api/business";
import { SwarmDiscussion } from "./SwarmDiscussion";

const persona = (id: string, name: string): BusinessPersona => ({ id, name, role: "customer", stakeholder_type: "direct", goals: ["Memeriksa manfaat"], motivations: [], constraints: [], knowledge: [], interests: [], relationships: [], provenance: {}, discovery_rationale: "Hipotesis", active: true, reviewed: false, revision: 1 });
const personas = [persona("a", "Customer harga"), persona("b", "Customer kualitas")];
const root: BusinessEvent = { id: "root", round: 1, actor_id: "a", target_id: "all", kind: "post_message", rationale: "Apakah harga sebanding?", content: "Apakah harga sebanding?", visibility: "public", thread_id: "root", reply_to: null, parent_event_ids: [], stance_update: { before: "undecided", after: "oppose", reason: "Harga perlu diuji", influenced_by_event_ids: [] } };
const response: BusinessEvent = { id: "reply", round: 1, actor_id: "b", target_id: "a", kind: "reply_message", rationale: "Manfaat perlu diuji", content: "Manfaat perlu diuji", visibility: "public", thread_id: "root", reply_to: "root", parent_event_ids: ["root"], stance_update: { before: "undecided", after: "conditional", reason: "Memerlukan bukti kualitas", influenced_by_event_ids: ["root"] } };

describe("swarm conversation", () => {
  it("shows who replied, follows the actual parent, and filters a private thread", async () => {
    const user = userEvent.setup();
    const privateRoot: BusinessEvent = { ...root, id: "private", thread_id: "private", target_id: "b", visibility: "participants", content: "Pertanyaan privat", rationale: "Pertanyaan privat" };
    render(<SwarmDiscussion events={[root, response, privateRoot]} personas={personas} openEvent={vi.fn()} />);
    expect(screen.getByText("Publik untuk peserta")).toBeVisible();
    expect(screen.getByText("Privat antarpartisipan")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Membalas Customer harga" }));
    expect(document.activeElement?.id).toBe("swarm-message-root");
    await user.selectOptions(screen.getByRole("combobox", { name: "Thread diskusi" }), "private");
    expect(screen.queryByRole("button", { name: "Membalas Customer harga" })).not.toBeInTheDocument();
    expect(screen.getByText("Privat antarpartisipan")).toBeVisible();
    expect(screen.getByText(/bukan bukti pasar/)).toBeVisible();
  });

  it("keeps stance explanations and opens the audit when the causal event is outside the thread", async () => {
    const user = userEvent.setup();
    const openEvent = vi.fn();
    render(<SwarmDiscussion events={[root, response]} personas={personas} stances={{ a: { stance: "conditional", stance_reason: "Perlu bukti manfaat", stance_history: [{ event_id: "audit-only", round: 2, before: "oppose", after: "conditional", reason: "Menanggapi argumen kualitas", influenced_by_event_ids: ["reply"], visibility: "participants" }] } }} openEvent={openEvent} />);
    const positions = screen.getByRole("heading", { name: "Posisi sintetis terakhir" }).closest("section")!;
    const customer = within(positions).getByText("Customer harga").closest("article")!;
    await user.click(within(customer).getByText("Riwayat perubahan (1)"));
    expect(within(positions).getByText("Menanggapi argumen kualitas")).toBeVisible();
    await user.click(within(customer).getByRole("button", { name: "Periksa interaksi perubahan" }));
    expect(openEvent).toHaveBeenCalledWith("audit-only");
  });

  it("shows a progress empty state without inventing consensus", () => {
    render(<SwarmDiscussion events={[]} personas={personas} openEvent={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Belum ada pesan diskusi");
    expect(screen.queryByRole("heading", { name: "Posisi sintetis terakhir" })).not.toBeInTheDocument();
  });

  it("shows reactive recipients, dispatch triggers and mechanical quality limits", async () => {
    const question = { ...root, target_id: "b", dialogue_act: "question" as const };
    const answer = { ...response, dialogue_act: "answer" as const, dispatch: { reason: "targeted_response", trigger_event_id: "root", followup: true } };
    render(<SwarmDiscussion events={[question, answer]} personas={personas} openEvent={vi.fn()} quality={{ version: "dialogue-structure-v1", messages: 2, reply_pairs: 1, reciprocal_pairs: 0, customer_peer_replies: 1, near_duplicate_event_ids: [], questions: 1, questions_without_recipient_reply: ["root"], warnings: ["Balasan tidak menjamin pertanyaan dijawab secara memadai."], limited_exchange: true, notice: "Indikator struktur, bukan kebenaran bisnis." }} />);
    expect(screen.getByText("Pertanyaan · kepada Customer kualitas")).toBeInTheDocument();
    expect(screen.getByText("Jawaban · kepada Customer harga")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Struktur percakapan" })).toHaveTextContent("bukan kebenaran bisnis");
    await userEvent.click(screen.getByRole("button", { name: "Giliran dipicu pertanyaan atau sanggahan" }));
    expect(document.activeElement?.id).toBe("swarm-message-root");
  });
});
