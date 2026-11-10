import { expect, test } from "@playwright/test";
import type { BusinessAnalysis, BusinessProject, ChatTurn } from "../../src/api/business";

test("result chat is discoverable, pins context and persists a follow-up without starting a swarm", async ({ page }, testInfo) => {
  const row: BusinessAnalysis = { id: "saved-chat-result", project_id: "chat-project", baseline_id: null, status: "completed", stage: "completed", created_at: "2026-11-06", input_snapshot: { revision: 1, context: { name: "Pepsodent · contoh chat hasil", industry: "FMCG", region: "Indonesia", target_customer: "Calon pembeli", decision_question: "Apa yang perlu diuji?", data_classification: "synthetic" }, personas: [], claims: [], config: { engine: "fixture", rounds: 2, interaction_mode: "swarm" }, idea: { id: "frozen-idea-v1", idea_id: "idea", title: "Dua rasa", version: 1, text: "Dua ruang tube sebagai usulan konsep." } }, result: {} };
  const project: BusinessProject = { id: row.project_id, revision: 5, context: row.input_snapshot.context, documents: [], claims: [], personas: [], analyses: [], created_at: row.created_at, updated_at: row.created_at };
  const unrelated: ChatTurn = { id: "other-turn", project_id: project.id, sequence: 1, status: "completed", request: { content: "Pembahasan hasil lain", target: "market", idea_revision_id: null, analysis_id: "other-result", expected_revision: 1 }, response: { answer: "Jawaban untuk hasil lain" }, created_at: row.created_at, updated_at: row.created_at };
  const turns: ChatTurn[] = [unrelated];
  const sends: { body: ChatTurn["request"]; key?: string }[] = [];
  const otherWrites: string[] = [];
  await page.route("**/backend/**", async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET" && !path.endsWith("/conversation")) otherWrites.push(path);
    if (path.endsWith("/auth/me")) return route.fulfill({ json: { id: "chat-ui-test", name: "Chat QA", email: "chat@example.com" } });
    if (path.endsWith("/capabilities")) return route.fulfill({ json: { llm_available: true, oasis_available: false, discovery_mode: "llm", max_file_bytes: 20000000, max_personas: 24 } });
    if (path.endsWith(`/analyses/${row.id}`)) return route.fulfill({ json: row });
    if (path.endsWith(`/projects/${project.id}`)) return route.fulfill({ json: project });
    if (path.endsWith("/events")) return route.fulfill({ json: { items: [] } });
    if (path.endsWith("/conversation")) {
      if (request.method() === "POST") {
        const body = request.postDataJSON() as ChatTurn["request"];
        sends.push({ body, key: request.headers()["idempotency-key"] });
        if (sends.length === 1) return route.fulfill({ status: 503, json: { message: "Koneksi contoh terputus; pesan belum dikonfirmasi." } });
        const turn: ChatTurn = { id: "new-turn", project_id: project.id, sequence: 2, status: "completed", request: body, response: { responder: "Finance Agent", answer: '{"answer":"**Biaya dua ruang** belum tersedia. Penjelasan tambahan ini perlu diuji pada pemasok."}', citations: [{ id: "saved:stance", kind: "synthetic_persona_position", analysis_id: row.id, label: "Calon pembeli · sikap sintetis", text: "Bersyarat: mekanisme dan manfaat belum diuji." }] }, created_at: row.created_at, updated_at: row.created_at };
        turns.push(turn);
        return route.fulfill({ status: 202, json: turn });
      }
      return route.fulfill({ json: { ideas: [{ id: "idea", title: "Konsep terbaru", version: 2, latest_revision: { id: "latest-idea-v2", idea_id: "idea", project_id: project.id, version: 2, content: { title: "Konsep terbaru", text: "Versi setelah analisis", document_ids: [], source_turn_ids: [], provenance: "user" }, created_at: row.created_at } }], turns, next_before: null } });
    }
    return route.fulfill({ status: 404, json: { message: "Outside this scripted UI example" } });
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/business/analyses/${row.id}`);
  const chatTab = page.getByRole("button", { name: "Tanya PAKAR", exact: true });
  await expect(chatTab).toBeVisible();
  await chatTab.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Diskusikan hasil dengan PAKAR" })).toBeVisible();
  await expect(page.locator(".analysis-chat-context")).toContainText("Dua rasa, versi 1");
  await expect(page.getByText("Jawaban untuk hasil lain")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Ide baru", exact: true })).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("result-chat-empty-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath("result-chat-empty-mobile.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole("button", { name: "Jelaskan alasan perbedaan sikap persona.", exact: true }).click();
  expect(sends).toHaveLength(0);
  const composer = page.getByLabel("Pesan atau penjelasan tambahan");
  await composer.fill("Tube saya punya dua ruang. Apa dampaknya ke biaya dan asumsi penilaian?");
  await page.getByLabel("Tanya kepada").selectOption("finance");
  await page.getByRole("button", { name: "Ringkasan", exact: true }).click();
  await chatTab.click();
  await expect(composer).toHaveValue(/Tube saya punya dua ruang/);
  await page.getByRole("button", { name: "Kirim ke AI", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Koneksi contoh terputus; pesan belum dikonfirmasi.");
  expect(sends).toHaveLength(1);
  await page.getByRole("button", { name: "Ringkasan", exact: true }).click();
  await chatTab.click();
  await expect(composer).toHaveValue(/Tube saya punya dua ruang/);
  expect(sends).toHaveLength(1);
  await page.getByRole("button", { name: "Kirim ke AI", exact: true }).click();
  await expect(page.getByText("Biaya dua ruang", { exact: true })).toHaveJSProperty("tagName", "STRONG");
  expect(sends).toHaveLength(2);
  expect(sends[1]).toEqual(sends[0]);
  expect(sends[1].body).toMatchObject({ analysis_id: row.id, idea_revision_id: "frozen-idea-v1", target: "finance", expected_revision: 5 });
  await page.getByText("Sumber yang dirujuk (1)", { exact: true }).click();
  await expect(page.getByText(/Sikap persona sintetis; bukan bukti pasar/)).toBeVisible();
  await page.locator(".project-chat-turn").screenshot({ path: testInfo.outputPath("result-chat-answer-mobile.png") });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.locator(".project-chat-turn").screenshot({ path: testInfo.outputPath("result-chat-answer-desktop.png") });
  await page.goto(`/business/analyses/${row.id}?tab=chat`);
  await expect(page.getByText("Biaya dua ruang", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("Biaya dua ruang", { exact: true })).toBeVisible();
  expect(sends).toHaveLength(2);
  expect(otherWrites).toEqual([]);
});
