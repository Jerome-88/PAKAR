import { expect, test } from "@playwright/test";

test("intake freezes disclosure and retries the same launch after an ambiguous response", async ({ page }, info) => {
  const api = "/backend/api/v1/business";
  await page.request.post("/backend/api/auth/register", { data: { name: "Disclosure QA", email: `disclosure-intake-${Date.now()}@example.com`, password: "local-ui-test-password" } });
  const attempts: { key: string | undefined; body: unknown }[] = [];
  await page.route(`**${api}/projects/*/quick-analysis`, async route => {
    attempts.push({ key: route.request().headers()["idempotency-key"], body: route.request().postDataJSON() });
    if (attempts.length === 1) { await route.fulfill({ status: 503, json: { message: "Status run belum pasti untuk tes UI" } }); return; }
    await route.fulfill({ response: await route.fetch() });
  });
  await page.goto("/business/new?example=1");
  await page.locator("summary").filter({ hasText: "Pengaturan tambahan" }).click();
  await page.getByLabel("Mode analisis").selectOption("fixture");
  await page.getByLabel("Brief untuk stakeholder").fill("Konsep usaha sintetis untuk menilai manfaat dan kemudahan mencoba. Data internal tidak dibagikan.");
  await page.getByRole("checkbox", { name: /Saya berwenang memakai dokumen ini/ }).check();
  await page.getByRole("button", { name: "Mulai analisis", exact: true }).click();
  await expect(page.getByText("Status run belum pasti untuk tes UI")).toBeVisible();
  await expect(page.getByLabel("Brief untuk stakeholder")).toBeDisabled();
  await expect(page.getByLabel("Mode analisis")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Buka ruang ide dahulu" })).toBeDisabled();
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.locator(".business-stakeholder-brief").evaluate(el => el.scrollIntoView({ block: "start", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("intake-frozen-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: info.outputPath("intake-frozen-mobile.png") });
  await page.getByRole("button", { name: "Mulai analisis", exact: true }).click();
  await expect(page).toHaveURL(/\/business\/analyses\/analysis_/);
  expect(attempts).toHaveLength(2); expect(attempts[0]).toEqual(attempts[1]);
  await page.unrouteAll({ behavior: "wait" });
});

for (const mode of ["quick", "reviewed"] as const) {
  test(`${mode} project launch freezes disclosure and keeps its identity on retry`, async ({ page }, info) => {
    const api = "/backend/api/v1/business";
    await page.request.post("/backend/api/auth/register", { data: { name: "Project disclosure QA", email: `disclosure-${mode}-${Date.now()}@example.com`, password: "local-ui-test-password" } });
    let project = await (await page.request.post(`${api}/projects`, { data: { name: "Uji disclosure sintetis", industry: "FMCG", region: "Indonesia", target_customer: "Customer sintetis", decision_question: "Apa yang perlu dipertimbangkan sebelum mencoba konsep produk ini?", data_classification: "synthetic" } })).json();
    project = await (await page.request.post(`${api}/projects/${project.id}/documents`, { multipart: { files: { name: "internal-synthetic.txt", mimeType: "text/plain", buffer: Buffer.from("Studi kasus sintetis, bukan riset nyata. Harga jual Rp30.000 per unit. Biaya variabel Rp12.000 per unit. Biaya tetap Rp36.000.000 per bulan. Pelanggan mempertimbangkan manfaat produk.") } } })).json();
    project = await (await page.request.post(`${api}/projects/${project.id}/claims/approve`, { data: { expected_revision: project.revision } })).json();
    for (const role of ["operator", "customer"]) {
      const response = await page.request.post(`${api}/projects/${project.id}/personas?expected_revision=${project.revision}`, { data: { id: "test-ignored", name: `Perspektif sintetis ${role}`, role, goals: ["Memeriksa konsep dalam tes UI"], reviewed: true } });
      expect(response.ok()).toBeTruthy();
      project = await (await page.request.get(`${api}/projects/${project.id}`)).json();
    }
    const endpoint = mode === "quick" ? "quick-analysis" : "analyses";
    const attempts: { key: string | undefined; body: unknown }[] = [];
    await page.route(`**${api}/projects/${project.id}/${endpoint}`, async route => {
      attempts.push({ key: route.request().headers()["idempotency-key"], body: route.request().postDataJSON() });
      if (attempts.length === 1) { await route.fulfill({ status: 503, json: { message: "Status run proyek belum pasti untuk tes UI" } }); return; }
      await route.fulfill({ response: await route.fetch() });
    });
    await page.goto(`/business/projects/${project.id}?tab=runs`);
    await page.getByLabel("Engine").selectOption("fixture");
    await page.getByLabel("Brief untuk stakeholder").fill("Konsep produk sintetis yang menawarkan kemudahan penggunaan, tanpa data biaya internal.");
    const label = mode === "quick" ? "Analisis otomatis" : "Mulai analisis";
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.getByText("Status run proyek belum pasti untuk tes UI")).toBeVisible();
    await expect(page.getByLabel("Brief untuk stakeholder")).toBeDisabled();
    await expect(page.getByLabel("Engine")).toBeDisabled();
    await expect(page.getByLabel("Ronde interaksi")).toBeDisabled();
    await expect(page.getByRole("button", { name: mode === "quick" ? "Mulai analisis" : "Analisis otomatis", exact: true })).toBeDisabled();
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.locator(".business-stakeholder-brief").evaluate(el => el.scrollIntoView({ block: "start", behavior: "instant" }));
    await page.screenshot({ path: info.outputPath(`${mode}-frozen-desktop.png`) });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: info.outputPath(`${mode}-frozen-mobile.png`) });
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page).toHaveURL(/\/business\/analyses\/analysis_/);
    expect(attempts).toHaveLength(2); expect(attempts[0]).toEqual(attempts[1]);
    await page.unrouteAll({ behavior: "wait" });
  });
}
