import { expect, test, type Page } from "@playwright/test";
import { existsSync, readFileSync } from "node:fs";
import type { BusinessAnalysis, BusinessPersona, StanceValue } from "../../src/api/business";

function example(size = 8): BusinessAnalysis {
  const personas: BusinessPersona[] = Array.from({ length: size }, (_, index) => ({ id: `person-${index}`, name: `Persona ${index + 1}`, role: index < 4 ? "customer" : "supplier", stakeholder_type: "direct", goals: [], motivations: [], constraints: [], knowledge: [], interests: [], relationships: [], provenance: {}, discovery_rationale: "", active: true, reviewed: false, revision: 1 }));
  return { id: "graph-example", project_id: "graph-project", baseline_id: null, status: "completed", stage: "completed", created_at: "2026-11-06",
    input_snapshot: { revision: 1, context: { name: "Contoh graf hasil sintetis", industry: "FMCG", region: "Indonesia", target_customer: "Calon pembeli", decision_question: "Apa yang perlu diuji?", data_classification: "synthetic" }, personas, claims: [], config: { engine: "fixture", rounds: 2, interaction_mode: "swarm" } },
    result: { simulation: { events: [
      { id: "first", kind: "post_message", round: 1, actor_id: "person-0", target_id: "all", rationale: "Contoh pesan publik", content: "Apa yang perlu diuji?", parent_event_ids: [], thread_id: "first", visibility: "public" },
      { id: "reply", kind: "post_message", round: 2, actor_id: "person-1", target_id: "person-0", rationale: "Contoh balasan", content: "Formula perlu diuji lebih dulu.", parent_event_ids: [], thread_id: "first", reply_to: "first", visibility: "public" },
    ], states: {}, stances: Object.fromEntries(personas.map((p, i) => [p.id, { stance: (["support", "oppose", "conditional", "undecided"] as StanceValue[])[i % 4], stance_reason: `Alasan tersimpan untuk ${p.name}; contoh terprogram untuk pengujian tampilan.`, stance_history: [] }])), calculation: { contribution_margin: null, break_even_units_monthly: null, profit_monthly: null, missing_inputs: [], inputs: {}, status: "unknown", formulas: {} }, stop_reason: "completed", usage: {} } },
  };
}

async function openExample(page: Page, row: BusinessAnalysis) {
  const writes: string[] = [];
  page.on("request", request => { if (new URL(request.url()).pathname.startsWith("/backend/") && request.method() !== "GET") writes.push(request.method()); });
  await page.route("**/backend/**", async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/backend/api/auth/me") return route.fulfill({ json: { id: "graph-ui-test", name: "Graph QA", email: "graph@example.com" } });
    if (path === `/backend/api/v1/business/analyses/${row.id}`) return route.fulfill({ json: row });
    if (path.endsWith("/events")) return route.fulfill({ json: { items: [] } });
    return route.fulfill({ status: 404, json: { message: "Not part of this read-only UI example" } });
  });
  await page.goto(`/business/analyses/${row.id}`);
  await expect(page.getByRole("group", { name: "Graf hasil interaktif" })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  return writes;
}

test("graph is the main result, with count filters, accessible reasons and visible mobile nodes", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const writes = await openExample(page, example());
  await expect(page.locator(".result-graph-node")).toHaveCount(8);
  await expect(page.locator(".result-graph-stage line")).toHaveCount(1);
  await page.locator(".result-graph-stage").scrollIntoViewIfNeeded();
  await expect(page.locator(".result-graph-stage")).toBeInViewport();
  await expect(page.getByLabel("Jumlah sikap persona").getByRole("button", { name: "2 Mendukung", exact: true })).toBeVisible();
  const node = page.getByRole("button", { name: "Lihat alasan Persona 2: Menolak", exact: true });
  await node.focus();
  await page.keyboard.press("Space");
  await expect(node).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByLabel("Alasan persona terpilih")).toContainText("Alasan tersimpan untuk Persona 2");
  await page.screenshot({ path: testInfo.outputPath("graph-desktop.png") });
  await page.getByRole("button", { name: "2 Bersyarat", exact: true }).click();
  await expect(page.locator(".result-graph-node")).toHaveCount(2);
  await expect(page.locator(".result-graph-node[data-stance=conditional]")).toHaveCount(2);
  await page.getByRole("combobox", { name: "Kelompok persona" }).selectOption("customers");
  await expect(page.locator(".result-graph-node")).toHaveCount(4);
  await expect(page.getByRole("button", { name: "1 Mendukung", exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Kelompok persona" }).selectOption("all");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("group", { name: "Graf hasil interaktif" })).toBeVisible();
  await page.locator(".result-graph-stage").scrollIntoViewIfNeeded();
  await expect(page.locator(".result-graph-stage")).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath("graph-mobile.png") });
  await page.getByRole("combobox", { name: "Lihat persona" }).selectOption("person-2");
  await expect(page.getByLabel("Alasan persona terpilih")).toContainText("Alasan tersimpan untuk Persona 3");
  await page.getByLabel("Alasan persona terpilih").screenshot({ path: testInfo.outputPath("graph-reason-mobile.png") });
  await page.getByRole("button", { name: /^Baca seluruh diskusi/ }).click();
  await expect(page.getByRole("button", { name: "Tim Discussion", exact: true })).toHaveAttribute("aria-current", "page");
  await expect(page).toHaveURL(/\?tab=swarm$/);
  await page.goBack();
  await expect(page.getByRole("button", { name: "Tim Discussion", exact: true })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { name: "Executive Summary", exact: true })).toBeVisible();
  expect(writes).toEqual([]);
});

test("120 persona graph remains scrollable and selection remains readable", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await openExample(page, example(120));
  await expect(page.locator(".result-graph-node image")).toHaveCount(120);
  await page.getByRole("combobox", { name: "Lihat persona" }).selectOption("person-119");
  await expect(page.getByLabel("Alasan persona terpilih")).toContainText("Alasan tersimpan untuk Persona 120");
  await expect.poll(() => page.locator(".result-graph-stage").evaluate(stage => {
    const node = stage.querySelector('[aria-pressed="true"] image')!.getBoundingClientRect();
    const box = stage.getBoundingClientRect();
    return node.top >= box.top && node.bottom <= box.bottom;
  })).toBeTruthy();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".result-graph-stage")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});

test("ten-person results stay a network with dragging, panning and zoom controls", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await openExample(page, example(10));
  await expect(page.locator(".result-graph-node")).toHaveCount(10);
  await expect(page.locator(".result-graph-node rect")).toHaveCount(0);
  const node = page.locator('.result-graph-node[data-persona-id="person-0"]');
  const before = (await node.locator("image").boundingBox())!;
  await page.mouse.move(before.x + before.width / 2, before.y + before.height / 2);
  await page.mouse.down();
  await page.mouse.move(before.x + before.width / 2 + 70, before.y + before.height / 2 + 35, { steps: 8 });
  await page.mouse.up();
  const after = (await node.locator("image").boundingBox())!;
  expect(after.x - before.x).toBeGreaterThan(40);
  const scene = page.locator(".result-network-scene");
  const initial = await scene.getAttribute("transform");
  await page.getByRole("button", { name: "Perbesar graf", exact: true }).click();
  await expect(scene).not.toHaveAttribute("transform", initial!);
  await page.getByRole("button", { name: "Atur ulang graf", exact: true }).click();
  await page.locator(".result-graph-stage").scrollIntoViewIfNeeded();
  const stage = (await page.locator(".result-graph-stage").boundingBox())!;
  const transform = await scene.getAttribute("transform");
  await page.mouse.move(stage.x + stage.width - 20, stage.y + stage.height - 20);
  await page.mouse.down();
  await page.mouse.move(stage.x + stage.width - 70, stage.y + stage.height - 60, { steps: 5 });
  await page.mouse.up();
  await expect(scene).not.toHaveAttribute("transform", transform!);
});

test("saved Pepsodent run keeps all eight declared undecided positions", async ({ page }, testInfo) => {
  const path = new URL("../../../backend/data/demo/pepsodent-public-2026-11-03-v3/analysis.json", import.meta.url);
  test.skip(!existsSync(path), "Optional local saved live-run artifact; no inference or database access.");
  const row = JSON.parse(readFileSync(path, "utf8")) as BusinessAnalysis;
  await page.setViewportSize({ width: 1440, height: 1000 });
  const writes = await openExample(page, row);
  await expect(page.getByRole("button", { name: "8 Belum memutuskan", exact: true })).toBeVisible();
  await expect(page.locator(".result-graph-node")).toHaveCount(8);
  await expect(page.getByRole("navigation", { name: "Hasil analisis", exact: true }).getByRole("button")).toHaveCount(3);
  await expect(page.locator(".app-sidebar, .app-drawer, .business-run-details, .business-limitations")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Buka navigasi produk", exact: true })).toHaveCount(0);
  await expect(page.getByText("Analisis lanjutan", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Yang masih kurang", exact: true })).toBeVisible();
  const executive = page.getByRole("region", { name: "Executive Summary", exact: true });
  await expect(executive).toBeVisible();
  expect(await executive.evaluate(section => section.previousElementSibling?.classList.contains("result-graph"))).toBeTruthy();
  await expect(executive).toContainText("Semua persona masih belum memutuskan");
  await page.getByRole("link", { name: "Lihat Executive Summary", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Executive Summary", exact: true })).toBeInViewport();
  await expect(executive).toBeFocused();
  // A shorter summary can reach the document's bottom before the scroll offset.
  await expect.poll(async () => (await executive.boundingBox())!.y).toBeLessThan(260);
  await expect(page.locator(".overview-priorities")).not.toContainText("Asumsi pasar belum memiliki bukti yang cocok");
  await expect(page.locator(".overview-priorities")).not.toContainText("Input biaya dan harga belum lengkap");
  await page.screenshot({ path: testInfo.outputPath("pepsodent-graph-desktop.png") });
  await page.locator(".overview-priorities").screenshot({ path: testInfo.outputPath("pepsodent-gaps-desktop.png") });
  await executive.evaluate(section => window.scrollTo({ top: Math.max(0, scrollY + section.getBoundingClientRect().top - 96), behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("pepsodent-executive-desktop.png") });
  const more = page.getByRole("button", { name: /^Lihat semua \d+ poin$/ });
  if (await more.count()) {
    await more.click();
    expect(await page.locator(".overview-priorities li").count()).toBeGreaterThan(3);
  }
  await page.getByRole("button", { name: "Tim Discussion", exact: true }).click();
  await expect(page.locator(".swarm-message")).not.toHaveCount(0);
  await expect(page.locator(".swarm-quality, .swarm-positions")).toHaveCount(0);
  await page.getByRole("button", { name: "Tim Discussion", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: testInfo.outputPath("pepsodent-graph-mobile.png") });
  await executive.evaluate(section => window.scrollTo({ top: Math.max(0, scrollY + section.getBoundingClientRect().top - 96), behavior: "instant" }));
  await page.screenshot({ path: testInfo.outputPath("pepsodent-executive-mobile.png") });
  await page.getByRole("combobox", { name: "Kelompok persona" }).selectOption("customers");
  await expect(page.getByRole("button", { name: "4 Belum memutuskan", exact: true })).toBeVisible();
  await expect(page.locator(".result-graph-node")).toHaveCount(4);
  for (const tab of ["summary", "timeline"]) {
    await page.goto(`/business/analyses/${row.id}?tab=${tab}#executive-summary`);
    await expect(page.getByRole("region", { name: "Executive Summary", exact: true })).toBeFocused();
    const top = (await page.getByRole("heading", { name: "Executive Summary", exact: true }).boundingBox())!.y;
    expect(top).toBeGreaterThanOrEqual(56);
    expect(top).toBeLessThan(200);
  }
  expect(writes).toEqual([]);
});
