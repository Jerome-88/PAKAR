import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { ChatTurn } from "../../api/business";
import { ConversationAnswer } from "./ConversationAnswer";
import { citationText } from "./citationReferences";

const turn: ChatTurn = {
  id: "chat-test", project_id: "project", sequence: 1, status: "completed",
  request: { content: "Jelaskan hasil", target: "facilitator", analysis_id: "analysis", idea_revision_id: null, expected_revision: 1 },
  response: { responder: "Fasilitator PAKAR", answer: "Perlu uji formula (sumber: analysis:event:7, doc-1). Jangan anggap ini hasil klinis.", citations: [
    { id: "analysis:event:7", kind: "synthetic_interaction", label: "Customer 4 kepada Customer 2", text: "Kemudahan pemakaian perlu diuji.", analysis_id: "analysis" },
    { id: "doc-1:claim:9", document_id: "doc-1", kind: "document_excerpt", label: "Usulan produk.txt", text: "Manfaat klinis belum terbukti." },
  ] }, created_at: "2026-11-06T10:00:00Z", updated_at: "2026-11-06T10:01:00Z",
};

describe("chat source presentation", () => {
  it("opens and focuses the exact saved source from an inline reference without modifying the reply", () => {
    const before = structuredClone(turn);
    const scroll = vi.spyOn(HTMLElement.prototype, "scrollIntoView").mockImplementation(() => {});
    render(<MemoryRouter><ConversationAnswer turn={turn} /></MemoryRouter>);
    expect(screen.queryByText(/analysis:event:7/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Buka sumber 2: Usulan produk.txt" }));
    expect(screen.getByText("Manfaat klinis belum terbukti.").closest("blockquote")).toHaveFocus();
    expect(screen.getByText("Manfaat klinis belum terbukti.").closest("details")).toHaveAttribute("open");
    expect(screen.getByText("Pesan simulasi; bukan fakta terverifikasi")).toBeVisible();
    expect(turn).toEqual(before);
    scroll.mockRestore();
  });

  it("keeps unresolved citations and ordinary prose intact rather than inventing a source", () => {
    const text = "Risiko tinggi (sumber: missing, analysis:event:7). Baca https://example.com.";
    expect(citationText(text, turn.response!.citations!, "test")).toBe(text);
    expect(citationText("Tidak ada sumber.", [], "test")).toBe("Tidak ada sumber.");
    const ambiguous = [...turn.response!.citations!, { id: "doc-1:claim:10", document_id: "doc-1", kind: "document_excerpt", label: "Kutipan lain", text: "Kutipan kedua." }];
    expect(citationText("Pernyataan (sumber: doc-1).", ambiguous, "test")).toBe("Pernyataan (sumber: doc-1).");
  });
});
