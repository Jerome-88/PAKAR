import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { BusinessAnalysis } from "../../src/api/business";

const demo: BusinessAnalysis = JSON.parse(readFileSync(new URL("../../public/demos/pepsodent.json", import.meta.url), "utf8"));

test("saved demo uses the real intake, idea workspace and result layout", async ({ page }, testInfo) => {
  const writes: string[] = [];
  page.on("request", request => { if (request.method() !== "GET") writes.push(request.method()); });
  await page.route("**/backend/**", route => route.fulfill({ status: 503, json: { message: "Offline" } }));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/business/demo");
  await expect(page.getByRole("heading", { name: "Analisis bisnis baru" })).toBeVisible();
  await expect(page.getByLabel("Nama analisis")).toBeDisabled();
  await expect(page.getByLabel("Keterangan dan pertanyaan")).toHaveValue(/Pepsodent/);
  await expect(page.getByRole("navigation", { name: "Alur demo" })).toHaveCount(0);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: testInfo.outputPath("intake-desktop.png"), fullPage: true });
  await page.getByRole("button", { name: "Buka ruang ide dahulu" }).click();
  await expect(page.getByRole("region", { name: "Ulasan AI tersimpan" })).toBeVisible();
  await expect(page.getByLabel("Pesan atau penjelasan tambahan")).toBeDisabled();
  await page.getByRole("button", { name: "Lihat hasil analisis", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Hasil analisis", exact: true })).toBeVisible();
  await expect(page.locator(".business-results-navigation")).toBeVisible();
  await expect(page.locator(".result-graph-node")).toHaveCount(10);
  await expect(page.locator(".result-graph-node rect")).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("result-desktop.png"), fullPage: true });
  await page.getByRole("button", { name: "Tanya PAKAR", exact: true }).click();
  await expect(page.locator(".project-chat-message.is-agent")).toHaveCount(4);
  await expect(page.getByRole("button", { name: "Kirim ke AI" })).toBeDisabled();
  await page.goBack();
  await expect(page.getByRole("button", { name: "Ringkasan", exact: true })).toHaveAttribute("aria-current", "page");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath("result-mobile.png"), fullPage: true });
  await page.getByRole("button", { name: "Input contoh", exact: true }).click();
  await page.screenshot({ path: testInfo.outputPath("intake-mobile.png"), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(writes).toEqual([]);
});

test("entry still offers demo or real intake without history", async ({ page }) => {
  const backendReads: string[] = [];
  await page.route("**/backend/**", route => { backendReads.push(new URL(route.request().url()).pathname); return route.fulfill({ status: 503, json: { message: "Offline" } }); });
  for (const path of ["/", "/business"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: "Ide Anda, dari berbagai sudut pandang." })).toBeVisible();
    await expect(page.getByRole("link", { name: /Coba demo/ })).toHaveAttribute("href", "/business/demo");
    await expect(page.getByRole("link", { name: /Analisis ide sendiri/ })).toHaveAttribute("href", "/business/new");
    await expect(page.getByText(/Riwayat|Proyek bisnis Anda/)).toHaveCount(0);
  }
  await page.getByRole("link", { name: /Coba demo/ }).click();
  await page.getByRole("button", { name: "Mulai analisis", exact: true }).click();
  await expect(page.locator(".result-graph-node")).toHaveCount(10);
  expect(backendReads.every(path => path === "/backend/api/auth/me")).toBe(true);
});

test("saved demo keeps recorded messages and positions across navigation", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route("**/backend/**", route => route.fulfill({ status: 503, json: { message: "Offline" } }));
  await page.goto("/business/demo?view=result");
  await expect(page.locator(".result-graph-node")).toHaveCount(10);
  await expect(page.getByRole("heading", { name: "Executive Summary" })).toBeVisible();
  await expect(page.getByRole("button", { name: "7 Bersyarat", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Diskusi", exact: true }).click();
  await expect(page.locator(".swarm-message")).toHaveCount(22);
  await expect(page.locator(".swarm-message-content").first()).toContainText(demo.result.simulation!.events[0].content!);
  await page.getByRole("button", { name: /^Membalas / }).first().click();
  await expect(page.locator(".swarm-message:focus")).toHaveCount(1);
  await page.getByRole("button", { name: "Ringkasan", exact: true }).click();
  await page.reload();
  await expect(page.getByRole("button", { name: "7 Bersyarat", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("demo loading failure can retry and return to the normal real-analysis choice", async ({ page }) => {
  let loads = 0;
  await page.route("**/backend/api/auth/me", route => route.fulfill({ json: { user: { id: "workspace_pakar", name: "PAKAR", shared: true } } }));
  await page.route("**/backend/api/v1/business/capabilities", route => route.fulfill({ json: {} }));
  await page.route("**/demos/pepsodent.json", route => ++loads === 1 ? route.fulfill({ status: 503 }) : route.fulfill({ json: demo }));
  await page.goto("/business/demo?view=result");
  await expect(page.getByRole("alert")).toContainText("Contoh hasil belum dapat dimuat");
  await page.getByRole("button", { name: "Muat ulang demo" }).click();
  await expect(page.locator(".result-graph-node")).toHaveCount(10);
  await page.getByRole("link", { name: "Kembali ke awal", exact: true }).click();
  await page.getByRole("link", { name: /Analisis ide sendiri/ }).click();
  await expect(page.getByRole("heading", { name: "Analisis bisnis baru" })).toBeVisible();
  await expect(page.getByLabel("Nama analisis")).toBeEnabled();
});
