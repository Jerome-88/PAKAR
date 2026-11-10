import { expect, test } from "@playwright/test";
import { openProcessDetails } from "./resultNavigation";

test("recovered discussion offers one specialist review and links both immutable runs", async ({ page }, testInfo) => {
  test.skip(process.env.RUN_BUSINESS_E2E !== "true", "Requires local API/PostgreSQL; paid endpoint is mocked.");
  test.setTimeout(60_000);
  const api = "/backend/api/v1/business";
  const registered = await page.request.post("/backend/api/auth/register", { data: { name: "Review QA", email: `review-${Date.now()}@example.com`, password: "synthetic-review-test-password" } });
  expect(registered.status()).toBe(201);
  const project = await (await page.request.post(`${api}/projects`, { data: { name: "Review kedai contoh", industry: "F&B", region: "Bandung", target_customer: "Pekerja", decision_question: "Apa yang perlu diperiksa sebelum membuka kedai?", data_classification: "synthetic" } })).json();
  const uploaded = await (await page.request.post(`${api}/projects/${project.id}/documents`, { multipart: { files: { name: "contoh.txt", mimeType: "text/plain", buffer: Buffer.from("Rencana kedai untuk pelanggan pekerja. Supplier memasok bahan.\nHarga jual Rp30.000 per unit.\nBiaya variabel Rp12.000 per unit.\nBiaya tetap Rp36.000.000 per bulan.") } } })).json();
  const queued = await page.request.post(`${api}/projects/${project.id}/quick-analysis`, { data: { expected_revision: uploaded.revision, engine: "fixture" } });
  expect(queued.status()).toBe(202);
  const id = (await queued.json()).id;
  await expect.poll(async () => (await (await page.request.get(`${api}/analyses/${id}`)).json()).status).toBe("completed");
  const source = await (await page.request.get(`${api}/analyses/${id}`)).json();
  const report = await (await page.request.get(`${api}/analyses/${id}/report`)).json();
  const reviewId = "analysis-review-ui-only";
  let submissions = 0;
  let validationOutcome = false;
  let resumed = false;
  const resumedId = "analysis-completed-ui-only";
  const recovered = { ...source, status: "partial", result: { ...source.result, recovery: { original_execution_status: "failed", specialist_review: "not_run", new_model_calls: 0 } }, input_snapshot: { ...source.input_snapshot, config: { ...source.input_snapshot.config, engine: "oasis" } } };
  // Only the UI recovery/review contracts are mocked. No paid call is allowed.
  await page.route(`**${api}/analyses/${id}`, route => route.fulfill({ json: { ...recovered, review_followup: submissions ? { id: reviewId, status: "partial" } : null } }));
  await page.route(`**${api}/analyses/${id}/specialist-review`, async route => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().headers()["idempotency-key"]).toBeTruthy();
    submissions++;
    await route.fulfill({ status: 202, json: { id: reviewId } });
  });
  const specialistCalls = ["Market Agent", "Finance Agent", "Legal/Compliance Agent", "Risk Agent"].map((role, i) => ({ role, phase: "specialist", status: i ? "failed" : "completed", ...(i ? { status_code: 429, failure_kind: "rate_limit" } : {}) }));
  const validationCalls = [
    { role: "Market Agent", phase: "specialist", status: "completed" },
    { role: "Finance Agent", phase: "specialist", status: "completed" },
    { role: "Finance Agent", status: "failed", error_type: "ValueError" },
    { role: "Legal/Compliance Agent", phase: "specialist", status: "failed", failure_kind: "timeout" },
    { role: "Risk Agent", phase: "specialist", status: "failed", error_type: "BudgetExceeded" },
  ];
  await page.route(`**${api}/analyses/${reviewId}`, route => route.fulfill({ json: { ...recovered, id: reviewId, review_followup: resumed ? { id: resumedId, status: "completed" } : null, input_snapshot: { ...recovered.input_snapshot, review_source: { analysis_id: id } }, result: { ...source.result, agent_runs: validationOutcome ? validationCalls : specialistCalls, provenance: { ...source.result.provenance, execution_kind: "specialist_review_continuation" } } } }));
  await page.route(`**${api}/analyses/${reviewId}/specialist-review`, async route => {
    expect(route.request().postDataJSON()).toEqual({ retry_failed: true });
    resumed = true;
    await route.fulfill({ status: 202, json: { id: resumedId } });
  });
  const completeCalls = ["Market Agent", "Finance Agent", "Legal/Compliance Agent", "Risk Agent"].map((role, i) => ({ role, phase: i < 2 ? "inherited_specialist" : "specialist", status: "completed" }));
  await page.route(`**${api}/analyses/${resumedId}`, route => route.fulfill({ json: { ...source, id: resumedId, status: "completed", input_snapshot: { ...source.input_snapshot, config: { ...source.input_snapshot.config, engine: "oasis" }, review_source: { analysis_id: reviewId } }, result: { ...source.result, agent_runs: completeCalls } } }));
  await page.route(`**${api}/analyses/${resumedId}/report`, route => route.fulfill({ json: { ...report, analysis_id: resumedId, status: "completed" } }));
  await page.route(`**${api}/analyses/${resumedId}/events`, route => route.fulfill({ json: { items: [] } }));
  await page.route(`**${api}/analyses/${reviewId}/report`, route => route.fulfill({ json: { ...report, analysis_id: reviewId, status: "partial" } }));
  await page.route(`**${api}/analyses/${reviewId}/events`, route => route.fulfill({ json: { items: [] } }));
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto(`/business/analyses/${id}`);
  await openProcessDetails(page);
  await expect(page.getByRole("button", { name: "Jalankan empat specialist AI" })).toBeVisible();
  await expect(page.getByText(/biaya provider/)).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("specialist-review-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.locator('section[aria-labelledby="specialist-continuation-title"]').evaluate(el => window.scrollTo({ top: window.scrollY + el.getBoundingClientRect().top - 90, behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("specialist-review-mobile.png") });
  await page.getByRole("button", { name: "Jalankan empat specialist AI" }).click();
  await expect(page).toHaveURL(new RegExp(`${reviewId}$`));
  await openProcessDetails(page);
  await expect(page.getByRole("link", { name: "diskusi run asal", exact: true })).toBeVisible();
  await expect(page.getByRole("table", { name: "Hasil review specialist" })).toBeVisible();
  await expect(page.getByText(/HTTP 429/)).toHaveCount(3);
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("specialist-result-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator(".business-specialist-status").evaluate(el => window.scrollTo({ top: window.scrollY + el.getBoundingClientRect().top - 90, behavior: "instant" }));
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath("specialist-result-mobile.png") });
  await expect(page.getByRole("button", { name: "Jalankan empat specialist AI" })).toHaveCount(0);
  await page.getByRole("link", { name: "diskusi run asal", exact: true }).click();
  await openProcessDetails(page);
  await expect(page.getByRole("link", { name: "Buka review specialist" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Jalankan empat specialist AI" })).toHaveCount(0);
  expect(submissions).toBe(1);
  validationOutcome = true;
  await page.goto(`/business/analyses/${reviewId}`);
  await openProcessDetails(page);
  await expect(page.getByText(/keluarannya ditolak validator/)).toBeVisible();
  await expect(page.getByText("Provider tidak merespons dalam batas waktu.")).toBeVisible();
  await expect(page.getByText(/jenis batas tidak dirinci/)).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("specialist-validation-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator(".business-specialist-status").evaluate(el => window.scrollTo({ top: window.scrollY + el.getBoundingClientRect().top - 90, behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("specialist-validation-mobile.png") });
  await page.getByRole("button", { name: "Lanjutkan specialist yang belum selesai" }).click();
  await expect(page).toHaveURL(new RegExp(`${resumedId}$`));
  await expect(page.getByRole("table", { name: "Hasil review specialist" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Lanjutkan specialist yang belum selesai" })).toHaveCount(0);
  expect(completeCalls.filter(call => call.status === "completed")).toHaveLength(4);
  expect(completeCalls.filter(call => call.phase === "inherited_specialist")).toHaveLength(2);

});
