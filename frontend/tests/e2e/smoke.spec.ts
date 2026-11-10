import { expect, test } from "@playwright/test";

test("loads the landing page", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1, name: /Temukan yang terlewat dalam rencana bisnis/i })).toBeVisible();
});
