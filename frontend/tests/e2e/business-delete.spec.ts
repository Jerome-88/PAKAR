import { expect, test } from "@playwright/test";
import type { BusinessProject } from "../../src/api/business";

test("project deletion requires confirmation and removes cached history without AI calls", async ({ page }, info) => {
  const id = "business_deletefixture";
  const project: BusinessProject = { id, revision: 1, context: { name: "Project uji hapus", industry: "Retail", region: "Jakarta", target_customer: "Customer sintetis", decision_question: "Asumsi apa yang perlu diuji?", data_classification: "synthetic" }, documents: [], claims: [], personas: [], analyses: [], created_at: "2026-11-10", updated_at: "2026-11-10" };
  let deleted = false;
  const writes: string[] = [];
  await page.addInitScript(projectId => localStorage.setItem("pakar:workspace-projects:v1", JSON.stringify([projectId])), id);
  await page.route("**/backend/**", route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET") writes.push(request.method());
    if (path === "/backend/api/auth/me") return route.fulfill({ json: { user: { id: "workspace_pakar", name: "Workspace", shared: true } } });
    if (path === `/backend/api/v1/business/projects/${id}`) {
      if (request.method() === "DELETE") { deleted = true; return route.fulfill({ json: { status: "deleted", cleanup_pending: false } }); }
      return route.fulfill({ status: deleted ? 404 : 200, json: deleted ? { message: "Not found" } : project });
    }
    return route.fulfill({ status: 404, json: { message: "No live services in this example" } });
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/business/projects");
  await page.getByRole("button", { name: "Hapus project", exact: true }).click();
  await expect(page.getByText(/Data tidak dapat dipulihkan/)).toBeVisible();
  await page.screenshot({ path: info.outputPath("delete-confirm-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("delete-confirm-mobile.png"), fullPage: true });
  await page.getByRole("button", { name: "Batal", exact: true }).click();
  expect(writes).toEqual([]);
  await page.getByRole("button", { name: "Hapus project", exact: true }).click();
  await page.getByRole("button", { name: "Hapus permanen", exact: true }).click();
  await expect(page.getByRole("heading", { name: project.context.name, exact: true })).toHaveCount(0);
  await expect(page.getByText("Project berhasil dihapus.", { exact: true })).toBeVisible();
  expect(await page.evaluate(projectId => JSON.parse(localStorage.getItem("pakar:workspace-projects:v1") ?? "[]").includes(projectId), id)).toBe(false);
  expect(writes).toEqual(["DELETE"]);
});
