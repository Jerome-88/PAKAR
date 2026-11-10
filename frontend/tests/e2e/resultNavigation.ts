import type { Page } from "@playwright/test";

export async function openResultDetail(page: Page, tab: "findings" | "timeline" | "scenario" | "audit") {
  const target = new URL(page.url());
  target.searchParams.set("tab", tab);
  await page.goto(target.href);
}

export async function openProcessDetails(page: Page) {
  await page.locator(".business-result-recovery").waitFor();
}
