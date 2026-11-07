import { expect } from "@playwright/test";

export const API_URL = process.env.E2E_API_URL || "http://127.0.0.1:8010";

/** Fail the test with a clear message if the page rendered ErrorState. */
export async function expectNoError(page) {
  const error = page.locator(".error-state");
  if (await error.count()) {
    const text = await error.first().innerText();
    throw new Error(`The page rendered an error state: ${text}`);
  }
}

/** Wait until the loading skeleton is gone and real content is on screen. */
export async function waitForPage(page) {
  await expect(page.locator(".page-loading")).toHaveCount(0, { timeout: 20_000 });
  await expect(page.locator(".page-heading h1")).toBeVisible();
  await expectNoError(page);
}

/** Fetch from the API directly, for cross-checking what the UI shows. */
export async function apiGet(request, path) {
  const response = await request.get(`${API_URL}${path}`);
  expect(response.ok(), `${path} returned ${response.status()}`).toBeTruthy();
  return response.json();
}

/** Navigate via the sidebar so the router is exercised, not just the URL. */
export async function gotoPage(page, label) {
  await page.getByRole("link", { name: label }).click();
  await waitForPage(page);
}
