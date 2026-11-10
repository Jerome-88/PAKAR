import { expect, test } from "@playwright/test";

test("reactive discussion deep link exposes recipients, triggered replies and quality limits", async ({ page }, testInfo) => {
  test.skip(process.env.RUN_BUSINESS_E2E !== "true", "Requires local API/PostgreSQL; fixture and mocked UI metadata only.");
  test.setTimeout(60_000);
  const api = "/backend/api/v1/business";
  const registration = await page.request.post("/backend/api/auth/register", { data: { name: "Dialogue QA", email: `dialogue-${Date.now()}@example.com`, password: "synthetic-dialogue-test-password" } });
  expect(registration.status()).toBe(201);
  const project = await (await page.request.post(`${api}/projects`, { data: { name: "Dialog kedai contoh", industry: "Kedai kopi", region: "Bandung", target_customer: "Pekerja", decision_question: "Asumsi apa yang perlu diuji sebelum membuka kedai?", data_classification: "synthetic" } })).json();
  const uploaded = await (await page.request.post(`${api}/projects/${project.id}/documents`, { multipart: { files: { name: "dialogue.txt", mimeType: "text/plain", buffer: Buffer.from("Kedai untuk pelanggan pekerja dengan supplier bahan dan competitor sekitar.\nHarga jual Rp30.000 per unit.\nBiaya variabel Rp12.000 per unit.\nBiaya tetap Rp36.000.000 per bulan.") } } })).json();
  const started = await page.request.post(`${api}/projects/${project.id}/quick-analysis`, { data: { engine: "fixture", expected_revision: uploaded.revision } });
  expect(started.status()).toBe(202);
  const id = (await started.json()).id;
  await expect.poll(async () => (await (await page.request.get(`${api}/analyses/${id}`)).json()).status).toBe("completed");
  const row = await (await page.request.get(`${api}/analyses/${id}`)).json();
  expect(row.input_snapshot.config.discussion_policy).toBe("reactive-v2");
  // The scheduler is verified in backend/installed-SDK tests. This fixture
  // metadata isolates the browser rendering of one question and triggered answer.
  const root = row.result.simulation.events.find((e: { kind: string; visibility: string }) => e.kind === "post_message" && e.visibility === "public");
  const response = row.result.simulation.events.find((e: { reply_to: string }) => e.reply_to === root.id);
  Object.assign(root, { dialogue_act: "question", target_id: response.actor_id, content: "Bukti kualitas apa yang Anda perlukan sebelum mencoba kedai?" });
  Object.assign(response, { dialogue_act: "answer", content: "Saya perlu mencoba produknya sebelum menilai manfaatnya. Kesediaan membeli belum dapat dipastikan dari dokumen saja.", dispatch: { reason: "targeted_response", trigger_event_id: root.id, followup: true } });
  row.result.simulation.discussion_quality.questions = 1;
  await page.route(`**${api}/analyses/${id}`, route => route.fulfill({ json: row }));
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto(`/business/analyses/${id}?tab=swarm`);
  await expect(page.getByRole("heading", { name: "Diskusi stakeholder", exact: true })).toBeVisible();
  await expect(page.locator(".swarm-quality")).toHaveCount(0);
  const reply = page.locator(`[id="swarm-message-${response.id}"]`);
  await reply.getByRole("button", { name: /^Membalas / }).click();
  await expect(page.locator(`[id="swarm-message-${root.id}"]`)).toBeFocused();
  await page.screenshot({ path: testInfo.outputPath("reactive-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.locator(".swarm-thread").first().evaluate(el => window.scrollTo({ top: scrollY + el.getBoundingClientRect().top - 90, behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("reactive-mobile.png") });
  await expect(page.getByText(/Pertanyaan · kepada/)).toBeVisible();
  const exported = await page.request.get(`${api}/analyses/${id}/export`);
  expect(await exported.text()).toContain("Struktur dan batas diskusi");
});
