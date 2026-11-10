import { render, screen, within } from "@testing-library/react";
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/server";
import type { BusinessAnalysis, BusinessProject, ChatTurn, Conversation, IdeaRevision } from "../../api/business";
import { ProjectConversation } from "./ProjectConversation";

const root = "/backend/api/v1/business/projects/project";
const revision: IdeaRevision = { id: "revision-1", idea_id: "idea", project_id: "project", version: 1, content: { title: "Dua rasa", text: "Dua rasa dalam satu tube untuk waktu penggunaan berbeda.", document_ids: [], source_turn_ids: [], provenance: "user_proposed_assumption" }, created_at: "2026-10-31T10:00:00Z" };
const project: BusinessProject = { id: "project", revision: 4, context: { name: "Pepsodent", industry: "Oral care", region: "Indonesia", target_customer: "18–30 tahun", decision_question: "Apakah ide ini menjawab masalah dalam studi kasus?", data_classification: "synthetic" }, documents: [], claims: [], personas: [], analyses: [], created_at: "2026-10-31", updated_at: "2026-10-31" };
const base = (): Conversation => ({ ideas: [{ id: "idea", title: "Dua rasa", version: 1, latest_revision: revision }], turns: [], next_before: null });
function mount(available = true, analysis?: BusinessAnalysis) {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}>
    <MemoryRouter initialEntries={["/project?tab=chat"]}><Routes><Route path="/project" element={<ProjectConversation project={project} analysis={analysis} capabilities={{ llm_available: available, oasis_available: available, discovery_mode: "llm", max_file_bytes: 20000000, max_personas: 24 }} onChanged={() => {}} />} /><Route path="/business/analyses/:id" element={<h1>Run ide terpisah</h1>} /></Routes></MemoryRouter>
  </QueryClientProvider>);
}
function serve(state = base()) {
  server.use(http.get(root + "/conversation", () => HttpResponse.json(state)), http.get(root + "/ideas/idea/revisions", () => HttpResponse.json({ items: [revision] })));
  return state;
}

describe("project conversation", () => {
  it("pins result chat to the frozen idea version and excludes other analysis turns", async () => {
    const state = serve();
    const frozen: BusinessAnalysis = { id: "saved-result", project_id: project.id, baseline_id: null, status: "completed", stage: "completed", created_at: "2026-11-06", input_snapshot: { revision: 1, context: project.context, personas: [], claims: [], config: { engine: "fixture", rounds: 2 }, idea: { id: "older-revision", idea_id: "idea", title: "Ide awal", version: 1, text: "Konsep awal tersimpan" } }, result: {} };
    state.turns = [{ id: "unrelated", project_id: project.id, sequence: 1, status: "completed", created_at: frozen.created_at, updated_at: frozen.created_at, request: { content: "Pertanyaan dari hasil lain", target: "facilitator", expected_revision: 4, analysis_id: "different-result", idea_revision_id: null }, response: { answer: "Jawaban hasil lain" } }];
    let sends = 0;
    server.use(http.post(root + "/conversation", async ({ request }) => {
      const body = await request.json() as ChatTurn["request"];
      sends++;
      expect(body).toMatchObject({ analysis_id: frozen.id, idea_revision_id: "older-revision", expected_revision: project.revision, target: "finance" });
      const turn: ChatTurn = { id: "answer", project_id: project.id, sequence: 2, status: "completed", created_at: frozen.created_at, updated_at: frozen.created_at, request: body, response: { responder: "Finance Agent", answer: '{"answer":"**Biaya kemasan** masih perlu diuji."}' } };
      state.turns.push(turn);
      return HttpResponse.json(turn, { status: 202 });
    }));
    mount(true, frozen);
    await screen.findByRole("button", { name: "Jelaskan alasan perbedaan sikap persona." });
    expect(screen.queryByText("Jawaban hasil lain")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ide baru" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Rujuk hasil analisis")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Apa yang perlu saya perbaiki dari ide ini?" }));
    expect(sends).toBe(0);
    expect(screen.getByLabelText("Pesan atau penjelasan tambahan")).toHaveValue("Apa yang perlu saya perbaiki dari ide ini?");
    await userEvent.selectOptions(screen.getByLabelText("Tanya kepada"), "finance");
    await userEvent.click(screen.getByRole("button", { name: "Kirim ke AI" }));
    expect(await screen.findByText("Biaya kemasan")).toHaveProperty("tagName", "STRONG");
    expect(sends).toBe(1);
    expect(screen.getByRole("link", { name: "Buat revisi ide di ruang ide" })).toHaveAttribute("href", `/business/projects/${project.id}?tab=chat&analysis=${frozen.id}`);
  });

  it("does not attach the project's latest idea to a result that had no idea", async () => {
    serve();
    const frozen: BusinessAnalysis = { id: "no-idea-result", project_id: project.id, baseline_id: null, status: "partial", stage: "completed", created_at: "2026-11-06", input_snapshot: { revision: 1, context: project.context, personas: [], claims: [], config: { engine: "fixture", rounds: 2 } }, result: {} };
    server.use(http.post(root + "/conversation", async ({ request }) => {
      expect(await request.json()).toMatchObject({ analysis_id: frozen.id, idea_revision_id: null });
      return HttpResponse.json({ message: "Snapshot checked" }, { status: 503 });
    }));
    mount(true, frozen);
    await userEvent.type(screen.getByLabelText("Pesan atau penjelasan tambahan"), "Jelaskan hasil ini");
    await userEvent.click(screen.getByRole("button", { name: "Kirim ke AI" }));
    expect(await screen.findByText("Snapshot checked")).toBeVisible();
  });

  it("saves a local idea without sending a chat or starting a swarm", async () => {
    const state = serve({ ideas: [], turns: [], next_before: null });
    let saved = 0;
    server.use(http.post(root + "/ideas", async ({ request }) => {
      const body = await request.json() as Record<string, unknown>;
      expect(body).toMatchObject({ title: "Dua rasa", text: "Dua ruang untuk dua rasa berbeda.", expected_version: 0 });
      saved++; state.ideas = base().ideas;
      return HttpResponse.json(revision, { status: 201 });
    }));
    mount(false);
    await userEvent.click(await screen.findByRole("button", { name: "Ide baru" }));
    await userEvent.type(screen.getByLabelText("Nama ide"), "Dua rasa");
    await userEvent.type(screen.getByLabelText("Isi ide", { exact: false }), "Dua ruang untuk dua rasa berbeda.");
    await userEvent.click(screen.getByRole("button", { name: "Simpan versi ide" }));
    expect(await screen.findByRole("button", { name: "Edit sebagai versi baru" })).toBeInTheDocument();
    expect(saved).toBe(1);
    expect(screen.getByRole("button", { name: "Kirim ke AI" })).toBeDisabled();
    expect(screen.getByText(/Chat AI belum dikonfigurasi/)).toBeInTheDocument();
  });

  it("keeps the message and request key after transport failure and attributes a single selected specialist", async () => {
    const state = serve();
    const keys: (string | null)[] = [];
    server.use(http.post(root + "/conversation", async ({ request }) => {
      keys.push(request.headers.get("Idempotency-Key"));
      const body = await request.json() as ChatTurn["request"];
      expect(body.target).toBe("finance"); expect(body.idea_revision_id).toBe("revision-1");
      if (keys.length === 1) return HttpResponse.json({ message: "Koneksi terputus" }, { status: 503 });
      const turn: ChatTurn = { id: "chat", project_id: "project", sequence: 1, status: "completed", request: body, response: { responder: "Finance Agent", answer: "Biaya kemasan belum tersedia dalam dokumen.", questions: ["Bagaimana rasa dipilih?"], citations: [{ id: "revision-1:claim", kind: "idea_assumption", label: "Dua rasa · versi 1", text: revision.content.text }] }, created_at: "2026-10-31T10:01:00Z", updated_at: "2026-10-31T10:01:00Z" };
      state.turns = [turn]; return HttpResponse.json(turn, { status: 202 });
    }));
    mount();
    await screen.findByRole("button", { name: "Edit sebagai versi baru" });
    await userEvent.selectOptions(screen.getByLabelText("Tanya kepada"), "finance");
    await userEvent.type(screen.getByLabelText("Pesan atau penjelasan tambahan"), "Kenapa kemasannya dianggap mahal?");
    await userEvent.click(screen.getByRole("button", { name: "Kirim ke AI" }));
    expect(await screen.findByText("Koneksi terputus")).toBeInTheDocument();
    expect(screen.getByLabelText("Pesan atau penjelasan tambahan")).toHaveValue("Kenapa kemasannya dianggap mahal?");
    await userEvent.click(screen.getByRole("button", { name: "Kirim ke AI" }));
    expect(await screen.findByText("Biaya kemasan belum tersedia dalam dokumen.")).toBeInTheDocument();
    expect(keys).toHaveLength(2); expect(keys[0]).toBeTruthy(); expect(keys[0]).toBe(keys[1]);
    const log = screen.getByRole("region", { name: "Riwayat percakapan proyek" });
    expect(within(log).getByText("Finance Agent")).toBeInTheDocument();
    expect(screen.getByText(/Jawaban baru dari Finance Agent tersedia/)).toHaveAttribute("aria-live", "polite");
    await userEvent.click(within(log).getByText("Sumber yang dirujuk (1)"));
    expect(within(log).getByText("[1] Dua rasa · versi 1")).toBeVisible();
    expect(within(log).getByText("Usulan pengguna")).toBeVisible();
  });

  it("opens a user clarification as an editable draft and requires explicit save", async () => {
    const state = serve(); let saves = 0;
    state.turns = [{ id: "chat", project_id: "project", sequence: 1, status: "completed", request: { content: "Tube memakai dua ruang terpisah.", target: "facilitator", expected_revision: 4, idea_revision_id: revision.id, analysis_id: null }, response: { responder: "Fasilitator PAKAR", answer: "Penjelasan ini belum disimpan sebagai revisi." }, created_at: "2026-10-31T10:01:00Z", updated_at: "2026-10-31T10:01:00Z" }];
    server.use(http.post(root + "/ideas/idea/revisions", async ({ request }) => {
      saves++; const body = await request.json() as Record<string, unknown>;
      expect(body.source_turn_ids).toEqual(["chat"]); expect(body.expected_version).toBe(1);
      expect(body.text).toContain("Tube memakai dua ruang terpisah.");
      return HttpResponse.json({ ...revision, id: "revision-2", version: 2 });
    }));
    mount();
    await userEvent.click(await screen.findByRole("button", { name: "Jadikan revisi ide" }));
    expect(saves).toBe(0); expect(screen.getByLabelText("Isi ide", { exact: false })).toHaveValue(revision.content.text + "\n\nPenjelasan tambahan pengguna: Tube memakai dua ruang terpisah.");
    expect(screen.getByRole("button", { name: "Analisis ide versi 1" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Simpan versi ide" }));
    await screen.findByRole("button", { name: "Edit sebagai versi baru" }); expect(saves).toBe(1);
  });

  it("starts the selected historical version only on an explicit simulation action", async () => {
    const state = serve();
    const next = { ...revision, id: "revision-2", version: 2 };
    state.ideas[0] = { ...state.ideas[0], version: 2, latest_revision: next };
    server.use(http.get(root + "/ideas/idea/revisions", () => HttpResponse.json({ items: [next, revision] })), http.post(root + "/quick-analysis", async ({ request }) => {
      expect(await request.json()).toMatchObject({ idea_revision_id: "revision-1", engine: "fixture", rounds: 2 });
      return HttpResponse.json({ id: "new-run" }, { status: 202 });
    }));
    mount();
    await screen.findByRole("option", { name: "Versi 1 · tersimpan" });
    await userEvent.selectOptions(screen.getByLabelText("Versi yang dibahas"), revision.id);
    await userEvent.selectOptions(screen.getByLabelText("Mode simulasi"), "fixture");
    await userEvent.type(screen.getByLabelText("Brief untuk stakeholder"), "Konsep pasta gigi dua rasa yang bisa dipilih pengguna.");
    await userEvent.click(screen.getByRole("button", { name: "Analisis ide versi 1" }));
    expect(await screen.findByRole("heading", { name: "Run ide terpisah" })).toBeInTheDocument();
  });

  it("explains an unavailable runtime beside the disabled analysis control", async () => {
    serve(); mount(false);
    expect(await screen.findByRole("button", { name: "Analisis ide versi 1" })).toBeDisabled();
    expect(screen.getByText(/Model atau runtime OASIS belum tersedia/)).toHaveTextContent(/Pilih fixture sintetis/);
  });

  it("recovers a definitively rejected stale run with refreshed revision and a new request identity", async () => {
    serve(); const keys: (string | null)[] = [];
    server.use(http.post(root + "/quick-analysis", async ({ request }) => {
      keys.push(request.headers.get("Idempotency-Key")); const body = await request.json() as Record<string, unknown>;
      if (keys.length === 1) { expect(body.expected_revision).toBe(4); return HttpResponse.json({ error: { code: "revision_conflict", message: "Input stale ditolak" } }, { status: 409 }); }
      expect(body.expected_revision).toBe(5); return HttpResponse.json({ id: "new-run" }, { status: 202 });
    }));
    function Harness() {
      const [p, setProject] = useState(project);
      return <ProjectConversation project={p} capabilities={{ llm_available: true, oasis_available: true, discovery_mode: "llm", max_file_bytes: 20000000, max_personas: 24 }} onChanged={() => setProject({ ...project, revision: 5 })} />;
    }
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}><MemoryRouter><Routes><Route path="/" element={<Harness />} /><Route path="/business/analyses/:id" element={<h1>Run direvisi</h1>} /></Routes></MemoryRouter></QueryClientProvider>);
    await screen.findByRole("button", { name: "Analisis ide versi 1" });
    await userEvent.type(screen.getByLabelText("Brief untuk stakeholder"), "Konsep pasta gigi dua rasa yang bisa dipilih pengguna.");
    await userEvent.click(screen.getByRole("button", { name: "Analisis ide versi 1" }));
    await userEvent.click(await screen.findByRole("button", { name: "Muat konteks analisis terbaru" }));
    await userEvent.click(screen.getByRole("button", { name: "Analisis ide versi 1" }));
    expect(await screen.findByRole("heading", { name: "Run direvisi" })).toBeInTheDocument();
    expect(keys).toHaveLength(2); expect(keys[0]).not.toBe(keys[1]);
  });

  it("retains the same simulation identity after an uncertain transport error", async () => {
    serve(); const keys: (string | null)[] = []; const bodies: unknown[] = [];
    server.use(http.post(root + "/quick-analysis", async ({ request }) => {
      keys.push(request.headers.get("Idempotency-Key")); bodies.push(await request.json());
      return keys.length === 1 ? HttpResponse.json({ message: "Koneksi run terputus" }, { status: 503 }) : HttpResponse.json({ id: "existing-run" }, { status: 202 });
    }));
    mount();
    await screen.findByRole("button", { name: "Analisis ide versi 1" });
    await userEvent.type(screen.getByLabelText("Brief untuk stakeholder"), "Konsep pasta gigi dua rasa yang bisa dipilih pengguna.");
    await userEvent.click(screen.getByRole("button", { name: "Analisis ide versi 1" }));
    expect(await screen.findByText("Koneksi run terputus")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Muat konteks analisis terbaru" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Brief untuk stakeholder")).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Analisis ide versi 1" }));
    expect(await screen.findByRole("heading", { name: "Run ide terpisah" })).toBeInTheDocument();
    expect(keys[0]).toBe(keys[1]); expect(bodies[0]).toEqual(bodies[1]);
  });

  it("requires a separately entered public brief and keeps disclosure scoped to each idea version", async () => {
    const state = serve();
    const next = { ...revision, id: "revision-2", version: 2 };
    state.ideas[0] = { ...state.ideas[0], version: 2, latest_revision: next };
    server.use(http.get(root + "/ideas/idea/revisions", () => HttpResponse.json({ items: [next, revision] })));
    mount();
    await screen.findByRole("option", { name: "Versi 1 · tersimpan" });
    const field = screen.getByLabelText("Brief untuk stakeholder");
    expect(field).toHaveValue("");
    expect(screen.getByRole("button", { name: "Analisis ide versi 2" })).toBeDisabled();
    await userEvent.type(field, "Konsep yang boleh dibagikan ke calon customer, tanpa data biaya.");
    expect(screen.getByRole("button", { name: "Analisis ide versi 2" })).toBeEnabled();
    await userEvent.selectOptions(screen.getByLabelText("Versi yang dibahas"), revision.id);
    expect(field).toHaveValue("");
    expect(screen.getByRole("button", { name: "Analisis ide versi 1" })).toBeDisabled();
    await userEvent.selectOptions(screen.getByLabelText("Versi yang dibahas"), next.id);
    expect(field).toHaveValue("Konsep yang boleh dibagikan ke calon customer, tanpa data biaya.");
  });
});
