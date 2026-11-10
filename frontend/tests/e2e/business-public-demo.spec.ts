import { expect, test } from "@playwright/test";

test.skip(process.env.RUN_PUBLIC_DEMO_E2E !== "1", "Requires the isolated public static build");

test("public demo mirrors the application with a draggable network and no backend", async ({ page, request }, testInfo) => {
  const apiRequests: string[] = [], errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", req => { if (/\/(backend|api)\//.test(new URL(req.url()).pathname) || req.method() !== "GET") apiRequests.push(req.url()); });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Ide Anda, dari berbagai sudut pandang." })).toBeVisible();
  await page.getByRole("link", { name: /Coba demo/ }).click();
  await expect(page.getByRole("heading", { name: "Analisis bisnis baru" })).toBeVisible();
  await expect(page.getByLabel("Nama analisis")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Buka navigasi produk" })).toHaveCount(0);
  await page.getByRole("button", { name: "Buka ruang ide dahulu" }).click();
  await expect(page.getByRole("region", { name: "Ulasan AI tersimpan" })).toBeVisible();
  await page.getByRole("button", { name: "Lihat hasil analisis", exact: true }).click();
  await expect(page.locator(".result-graph-node")).toHaveCount(10);
  await expect(page.locator(".result-graph-node rect")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Executive Summary" })).toBeVisible();
  const before = await page.getByLabel("Zoom graf").textContent();
  await page.getByRole("button", { name: "Perbesar graf", exact: true }).click();
  await expect(page.getByLabel("Zoom graf")).not.toHaveText(before!);
  await page.getByRole("button", { name: "Atur ulang graf", exact: true }).click();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: testInfo.outputPath("public-result-desktop.png"), fullPage: true });
  await page.getByRole("button", { name: "Diskusi", exact: true }).click();
  await expect(page.locator(".swarm-message")).toHaveCount(22);
  await page.getByRole("button", { name: "Tanya PAKAR", exact: true }).click();
  await expect(page.locator(".project-chat-message.is-agent")).toHaveCount(4);
  await expect(page.getByRole("button", { name: "Kirim ke AI" })).toBeDisabled();
  await page.getByRole("button", { name: "Ringkasan", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect.poll(() => page.locator(".result-graph-stage").evaluate(stage => {
    const bounds = stage.getBoundingClientRect();
    return [...stage.querySelectorAll(".result-graph-node image")].every(image => {
      const avatar = image.getBoundingClientRect();
      return avatar.left >= bounds.left && avatar.right <= bounds.right && avatar.top >= bounds.top && avatar.bottom <= bounds.bottom;
    });
  })).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("public-result-mobile.png"), fullPage: true });
  await page.reload();
  await expect(page.locator(".result-graph-node")).toHaveCount(10);
  await page.getByRole("link", { name: "Kembali ke awal", exact: true }).click();
  await expect(page.getByRole("link", { name: /Coba demo/ })).toBeVisible();
  expect((await request.get("/backend/api/auth/me")).status()).toBe(404);
  expect((await request.post("/backend/api/v1/business/projects", { data: {} })).status()).toBe(405);
  expect((await request.get("/.env")).status()).toBe(404);
  expect(apiRequests).toEqual([]);
  expect(errors).toEqual([]);
});
