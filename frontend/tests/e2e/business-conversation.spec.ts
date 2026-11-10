import { expect, test, type Route } from "@playwright/test";

test.skip(process.env.RUN_BUSINESS_E2E !== "true", "Requires a separate local API/PostgreSQL; AI replies are mocked.");

test("project chat keeps ideas versioned and starts a new simulation only explicitly", async ({ page }, testInfo) => {
  const api = "/backend/api/v1/business";
  // React Query cancels obsolete GETs during route changes/StrictMode. A late
  // scripted response must not try to fulfill a request Chromium has aborted.
  const fulfillActive = async (route: Route, options: Parameters<Route["fulfill"]>[0]) => {
    const aborted = () => /ERR_ABORTED|NS_BINDING_ABORTED/.test(route.request().failure()?.errorText ?? "");
    if (aborted()) return;
    try {
      await route.fulfill(options);
    } catch (error) {
      // Chromium can dispose the route before its requestfailed event arrives.
      // This helper issues one fulfill only; ignore that exact lifecycle error,
      // while preserving all response/content assertions and other failures.
      const disposed = error instanceof Error && error.message.includes("Route is already handled!");
      if (!aborted() && !page.isClosed() && !disposed) throw error;
    }
  };
  const registered = await page.request.post("/backend/api/auth/register", { data: { name: "Conversation QA", email: `conversation-${Date.now()}@example.com`, password: "local-ui-test-password" } });
  expect(registered.status()).toBe(201);
  await page.route(`**${api}/capabilities`, async route => {
    const response = await page.request.get(route.request().url()); const body = await response.json();
    await fulfillActive(route, { json: { ...body, llm_available: true, oasis_available: false } });
  });
  // Scripted UI responses only. The real HTTP/worker/provider boundary is
  // exercised separately by backend tests using a local provider, never credit.
  const replies: Record<string, unknown>[] = [];
  await page.route(`**${api}/projects/*/conversation`, async route => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON();
      replies.push({ id: "ui-fixture-chat", project_id: "ui-fixture", sequence: 1, status: "completed", request: body, response: { responder: "Finance Agent", answer: "Respons terprogram untuk tes UI: biaya kemasan belum tersedia. Dua ruang tube perlu diuji sebelum memperkirakan margin.", questions: ["Bagaimana pengguna memilih rasa dari satu tube?"], citations: [], suggested_revision: null }, created_at: "2026-10-31T14:00:00Z", updated_at: "2026-10-31T14:00:01Z" });
      await fulfillActive(route, { status: 202, json: replies.at(-1) }); return;
    }
    const response = await page.request.get(route.request().url()); const state = await response.json();
    await fulfillActive(route, { json: { ...state, turns: replies } });
  });
  let simulations = 0;
  page.on("request", req => { if (req.method() === "POST" && req.url().endsWith("/quick-analysis")) simulations++; });
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto("/business/new?example=1");
  await page.getByLabel("Nama analisis", { exact: true }).fill("Pepsodent · studi kasus chat sintetis");
  await page.getByLabel("Keterangan dan pertanyaan").fill("Apakah inovasi dua rasa membantu konsumen muda kembali ke segmen premium?");
  await page.getByLabel("Isi proposal contoh").fill("Studi kasus sintetis untuk tes UI. Konsumen muda mempertimbangkan manfaat dan harga pasta gigi premium. Data contoh bukan hasil riset pasar nyata.");
  await page.getByRole("checkbox", { name: /Saya berwenang memakai dokumen ini/ }).check();
  await page.getByRole("button", { name: "Buka ruang ide dahulu" }).click();
  await expect(page).toHaveURL(/\/business\/projects\/business_.*\?tab=chat/);
  const projectId = new URL(page.url()).pathname.split("/").at(-1)!;
  await expect(page.getByRole("heading", { name: "Ruang ide", exact: true })).toBeVisible();
  expect(simulations).toBe(0);
  await page.getByRole("button", { name: "Ide baru", exact: true }).click();
  await page.getByLabel("Nama ide", { exact: true }).fill("Pepsodent dual-rasa");
  await page.getByLabel("Isi ide", { exact: false }).fill("Satu tube mempunyai dua rasa dan perubahan warna sebagai hipotesis fitur yang perlu diuji.");
  await page.getByRole("button", { name: "Simpan versi ide" }).click();
  await expect(page.getByRole("button", { name: "Edit sebagai versi baru" })).toBeVisible();
  await page.getByLabel("Tanya kepada").selectOption("finance");
  await page.getByLabel("Pesan atau penjelasan tambahan").fill("Tube memakai dua ruang. Apa dampaknya pada kelayakan bisnis?");
  await page.getByRole("button", { name: "Kirim ke AI" }).click();
  await expect(page.getByText(/Respons terprogram untuk tes UI:/)).toBeVisible();
  expect(simulations).toBe(0);
  await page.reload();
  await expect(page.getByText(/Respons terprogram untuk tes UI:/)).toBeVisible();
  await page.getByRole("button", { name: "Edit sebagai versi baru" }).click();
  await page.getByLabel("Isi ide", { exact: false }).fill("Konsep revisi: dua ruang terpisah dengan pilihan nozzle. Perubahan warna belum terbukti menandakan kebersihan gigi.");
  await page.getByRole("button", { name: "Simpan versi ide" }).click();
  await expect(page.getByRole("button", { name: "Analisis ide versi 2" })).toBeVisible();
  const state = await (await page.request.get(`${api}/projects/${projectId}/conversation`)).json();
  const idea = state.ideas[0];
  const history = await (await page.request.get(`${api}/projects/${projectId}/ideas/${idea.id}/revisions`)).json();
  expect(history.items.map((r: { version: number }) => r.version)).toEqual([2, 1]);
  expect(history.items[1].content.text).toContain("hipotesis fitur");
  expect(simulations).toBe(0);
  await page.getByRole("heading", { name: "Ruang ide", exact: true }).evaluate(el => el.scrollIntoView({ block: "start", behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("project-chat-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.locator(".project-idea-panel").evaluate(el => el.scrollIntoView({ block: "start", behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("project-chat-mobile-idea.png") });
  await page.locator(".project-chat-turn").first().evaluate(el => el.scrollIntoView({ block: "start", behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("project-chat-mobile-discussion.png") });
  await expect(page.getByLabel("Brief untuk stakeholder")).toHaveValue("");
  await expect(page.getByRole("button", { name: "Analisis ide versi 2" })).toBeDisabled();
  await page.getByLabel("Brief untuk stakeholder").fill("Konsep pasta gigi dua rasa yang dapat dipilih. Perubahan warna merupakan fitur usulan yang belum diuji.");
  await page.locator(".project-idea-run").evaluate(el => el.scrollIntoView({ block: "start", behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("stakeholder-brief-mobile.png") });
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.locator(".project-idea-run").evaluate(el => el.scrollIntoView({ block: "start", behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("stakeholder-brief-desktop.png") });
  await page.getByLabel("Mode simulasi").selectOption("fixture");
  await page.getByRole("button", { name: "Analisis ide versi 2" }).click();
  await expect(page).toHaveURL(/\/business\/analyses\/analysis_.*\?tab=swarm/);
  const runId = new URL(page.url()).pathname.split("/").at(-1)!;
  await expect(page.getByRole("heading", { name: "Diskusi stakeholder", exact: true })).toBeVisible({ timeout: 20000 });
  const run = await (await page.request.get(`${api}/analyses/${runId}`)).json();
  expect(run.input_snapshot.information_policy.version).toBe("public-brief-v1");
  expect(run.input_snapshot.information_policy.public_brief).toContain("fitur usulan");
  expect(run.input_snapshot.idea.id).toBe(idea.latest_revision.id);
  expect(run.input_snapshot.idea.version).toBe(2);
  expect(simulations).toBe(1);
  await page.getByRole("button", { name: "Tanya PAKAR", exact: true }).click();
  await page.getByRole("link", { name: "Kelola ide & sumber", exact: true }).click();
  await expect(page.getByLabel("Rujuk hasil analisis")).toHaveValue(runId);
  // All product assertions are complete; dispose polling mocks without waiting
  // for requests cancelled by the return navigation to finish handling.
  await page.unrouteAll({ behavior: "ignoreErrors" });
});
