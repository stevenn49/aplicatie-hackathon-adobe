import { expect, test } from "@playwright/test";
import { apiGet, expectNoError, gotoPage, waitForPage } from "./helpers.js";

test.describe("Application shell", () => {
  test("every route renders without an error state", async ({ page }) => {
    const routes = [
      { path: "/", title: "Market overview" },
      { path: "/products", title: "Product analysis" },
      { path: "/brands", title: "Know where every brand stands." },
      { path: "/sentiment", title: "Sentiment analysis" },
      { path: "/consumers", title: "Meet the people behind the purchase." },
      { path: "/marketing", title: "Marketing analytics" },
      { path: "/competitors", title: "See the market from every angle." },
      { path: "/recommendations", title: "The signal, and what to do next." },
    ];

    for (const route of routes) {
      await page.goto(route.path);
      await waitForPage(page);
      await expect(page.locator(".page-heading h1")).toHaveText(route.title);
    }
  });

  test("sidebar navigation works for all eight pages", async ({ page }) => {
    await page.goto("/");
    await waitForPage(page);

    for (const label of [
      "Product Analysis",
      "Brand Intelligence",
      "Sentiment Analysis",
      "Consumer Insights",
      "Marketing Analytics",
      "Competitor Analysis",
      "AI Recommendations",
      "Market Overview",
    ]) {
      await gotoPage(page, label);
      await expect(page.locator(".nav-link.active")).toContainText(label);
    }
  });

  test("the sidebar reports the real database status", async ({ page, request }) => {
    const health = await apiGet(request, "/health");
    await page.goto("/");
    await waitForPage(page);

    const status = page.locator(".data-status");
    await expect(status).toContainText(
      health.database === "healthy" ? "Database connected" : "Database unreachable",
    );
    await expect(status).toContainText(health.database === "healthy" ? "LIVE" : "DOWN");
  });

  test("an unknown route redirects to the overview", async ({ page }) => {
    await page.goto("/does-not-exist");
    await expect(page).toHaveURL(/\/$/);
    await waitForPage(page);
  });

  test("the theme toggle switches and persists", async ({ page }) => {
    await page.goto("/");
    await waitForPage(page);

    const before = await page.evaluate(() => document.documentElement.dataset.theme);
    await page.getByRole("button", { name: /Switch to (light|dark) theme/ }).click();
    const after = await page.evaluate(() => document.documentElement.dataset.theme);
    expect(after).not.toBe(before);

    await page.reload();
    await waitForPage(page);
    expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe(after);
  });
});

test.describe("Global filters", () => {
  test("the brand filter narrows the product list", async ({ page, request }) => {
    const all = await apiGet(request, "/api/products");
    const sony = await apiGet(request, "/api/products?brand=Sony");

    await page.goto("/products");
    await waitForPage(page);
    await expect(page.locator(".data-table tbody tr")).toHaveCount(all.length);

    await page.getByLabel("Brand filter").selectOption("Sony");
    await expect(page.locator(".data-table tbody tr")).toHaveCount(sony.length);
    await expect(page.locator(".data-table tbody")).toContainText("Sony");
    await expect(page.locator(".data-table tbody")).not.toContainText("Apple");
  });

  test("the source filter narrows the review explorer", async ({ page, request }) => {
    const all = await apiGet(request, "/api/analytics/sentiment");
    const emag = await apiGet(request, "/api/analytics/sentiment?source=eMAG");

    await page.goto("/sentiment");
    await waitForPage(page);
    await expect(page.locator(".freshness-pill")).toContainText(`${all.total_reviews} reviews analyzed`);

    await page.getByLabel("Data source filter").selectOption("eMAG");
    await expect(page.locator(".freshness-pill")).toContainText(`${emag.total_reviews} reviews analyzed`);
  });

  test("the global search filters products", async ({ page }) => {
    await page.goto("/products");
    await waitForPage(page);

    const total = await page.locator(".data-table tbody tr").count();
    await page.getByLabel("Search products and brands").fill("iPhone");
    await expect(page.locator(".data-table tbody tr")).toHaveCount(1);
    await expect(page.locator(".data-table tbody")).toContainText("iPhone");
    expect(total).toBeGreaterThan(1);

    await page.getByRole("button", { name: "Clear search" }).click();
    await expect(page.locator(".data-table tbody tr")).toHaveCount(total);
  });
});
