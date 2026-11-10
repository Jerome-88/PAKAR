import { expect, test } from "@playwright/test";

test("loads the workspace overview without a backend connection", async ({ page }) => {
  await page.route("**/backend/**", route => route.fulfill({ status: 503, json: { message: "Offline" } }));
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1, name: "Overview", exact: true })).toBeVisible();
});
