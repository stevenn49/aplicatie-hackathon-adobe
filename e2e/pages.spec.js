import { expect, test } from "@playwright/test";
import { apiGet, waitForPage } from "./helpers.js";

test.describe("Market Overview", () => {
  test("KPIs match the API", async ({ page, request }) => {
    const overview = await apiGet(request, "/api/analytics/overview");

    await page.goto("/");
    await waitForPage(page);

    const cards = page.locator(".kpi-card");
    await expect(cards).toHaveCount(overview.kpis.length + (overview.topMovers.length ? 1 : 0));

    for (const kpi of overview.kpis) {
      const card = page.locator(".kpi-card", { hasText: kpi.label });
      await expect(card).toContainText(kpi.value);
    }
  });

  test("top movers and mentions come from stored reviews", async ({ page, request }) => {
    const overview = await apiGet(request, "/api/analytics/overview");

    await page.goto("/");
    await waitForPage(page);

    await expect(page.locator(".mover-row")).toHaveCount(overview.topMovers.length);
    await expect(page.locator(".mention-row")).toHaveCount(overview.mentions.length);

    for (const mover of overview.topMovers) {
      await expect(page.locator(".mover-list")).toContainText(mover.name);
    }
    for (const mention of overview.mentions) {
      await expect(page.locator(".mention-list")).toContainText(mention.brand);
    }
  });

  test("share of voice sums to about 100%", async ({ page }) => {
    await page.goto("/");
    await waitForPage(page);

    const rows = page.locator(".share-row");
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    let total = 0;
    for (let i = 0; i < count; i += 1) {
      const text = await rows.nth(i).innerText();
      const match = text.match(/([\d.]+)%/);
      if (match) total += parseFloat(match[1]);
    }
    expect(total).toBeGreaterThan(99);
    expect(total).toBeLessThan(101);
  });
});

test.describe("Product Analysis", () => {
  test("the table lists every product with derived values", async ({ page, request }) => {
    const products = await apiGet(request, "/api/products");

    await page.goto("/products");
    await waitForPage(page);

    await expect(page.locator(".data-table tbody tr")).toHaveCount(products.length);
    await expect(page.locator(".count-pill")).toContainText(`${products.length} products tracked`);

    for (const product of products.slice(0, 3)) {
      await expect(page.locator(".data-table tbody")).toContainText(product.name);
    }
  });

  test("sorting by price reorders the table", async ({ page }) => {
    await page.goto("/products");
    await waitForPage(page);

    await page.getByRole("button", { name: /^Price/ }).click();

    // Prices render as "6.499,99 lei": dots are thousands, the comma is decimal.
    const parsePrice = (text) => Number(text.replace(/[^\d,]/g, "").replace(",", "."));

    const prices = await page.locator(".data-table tbody tr td:nth-child(3)").allInnerTexts();
    const parsed = prices.map(parsePrice);
    expect(parsed.every((value) => Number.isFinite(value))).toBeTruthy();

    const sorted = [...parsed].sort((a, b) => b - a);
    expect(parsed).toEqual(sorted);
  });

  test("the category filter narrows the table", async ({ page }) => {
    await page.goto("/products");
    await waitForPage(page);

    const all = await page.locator(".data-table tbody tr").count();
    await page.getByLabel("Filter by category").selectOption("Laptop");
    const laptops = await page.locator(".data-table tbody tr").count();
    expect(laptops).toBeGreaterThan(0);
    expect(laptops).toBeLessThan(all);
    await expect(page.locator(".data-table tbody")).toContainText("Laptop");
  });

  test("the product drawer shows history, specs and reviews", async ({ page, request }) => {
    const products = await apiGet(request, "/api/products");
    const target = products[0];
    const detail = await apiGet(request, `/api/products/${target.id}`);

    await page.goto("/products");
    await waitForPage(page);

    await page.locator(".data-table tbody tr", { hasText: target.name }).first().click();

    const drawer = page.locator(".product-drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer.locator(".drawer-title")).toContainText(target.name);
    await expect(drawer.locator(".drawer-price")).toContainText("lei");

    if (detail.price_history.length) {
      await expect(drawer.locator(".recharts-surface").first()).toBeVisible();
    }
    if (Object.keys(target.specs).length) {
      await expect(drawer.locator(".drawer-specs")).toBeVisible();
    }

    await drawer.getByRole("button", { name: "Close product details" }).click();
    await expect(drawer).toHaveCount(0);
  });

  test("comparison starts with two products and can change", async ({ page, request }) => {
    const products = await apiGet(request, "/api/products");

    await page.goto("/products");
    await waitForPage(page);

    await expect(page.locator(".selected-product-pill")).toHaveCount(2);
    await expect(page.locator(".spec-comparison")).toBeVisible();

    // The pill itself is the remove button.
    const removedName = products[0].name;
    await page.locator(".selected-product-pill").first().click();
    await expect(page.locator(".selected-product-pill")).toHaveCount(1);
    await expect(page.locator(".comparison-panel")).toContainText("Choose one more product");

    // Add a third product from the table to get back to two.
    const third = products[2];
    const row = page.locator(".data-table tbody tr", { hasText: third.name }).first();
    await row.locator(".compare-toggle").click();

    await expect(page.locator(".selected-product-pill")).toHaveCount(2);
    await expect(page.locator(".spec-comparison")).toContainText(third.name);
    await expect(page.locator(".spec-comparison")).not.toContainText(removedName);
  });
});

test.describe("Brand Intelligence", () => {
  test("brand health matches the API", async ({ page, request }) => {
    const brands = await apiGet(request, "/api/analytics/brands");

    await page.goto("/brands");
    await waitForPage(page);

    const banner = page.locator(".brand-health-banner");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText(brands[0].brand);
    await expect(banner).toContainText(`${brands[0].shareOfVoice}%`);
    await expect(banner).toContainText(String(brands[0].mentions));
  });

  test("switching focus brand updates the banner", async ({ page, request }) => {
    const brands = await apiGet(request, "/api/analytics/brands");
    const other = brands[1];

    await page.goto("/brands");
    await waitForPage(page);

    await page.getByRole("combobox").first().selectOption(other.brand);
    await expect(page.locator(".brand-health-banner")).toContainText(other.brand);
    await expect(page.locator(".brand-health-banner")).toContainText(`${other.shareOfVoice}%`);
  });

  test("praise and concern columns reflect the API", async ({ page, request }) => {
    const brands = await apiGet(request, "/api/analytics/brands");
    const active = brands[0];

    await page.goto("/brands");
    await waitForPage(page);

    if (active.topics.length || active.concerns.length) {
      const topics = page.locator(".topics-card");
      await expect(topics).toBeVisible();
      for (const topic of active.topics) {
        await expect(topics).toContainText(topic);
      }
      for (const concern of active.concerns) {
        await expect(topics).toContainText(concern);
      }
    }
  });
});

test.describe("Sentiment Analysis", () => {
  test("the distribution matches the API", async ({ page, request }) => {
    const data = await apiGet(request, "/api/analytics/sentiment");

    await page.goto("/sentiment");
    await waitForPage(page);

    await expect(page.locator(".freshness-pill")).toContainText(`${data.total_reviews} reviews analyzed`);

    for (const slice of data.distribution) {
      await expect(page.locator(".sentiment-legend")).toContainText(`${slice.name}`);
      await expect(page.locator(".sentiment-legend")).toContainText(`${slice.value}%`);
    }
  });

  test("the sentiment filter narrows the review list", async ({ page, request }) => {
    const data = await apiGet(request, "/api/analytics/sentiment");
    const positive = data.reviews.filter((r) => r.sentiment === "positive").length;

    await page.goto("/sentiment");
    await waitForPage(page);

    await page.getByLabel("Filter reviews by sentiment").selectOption("Positive");
    const total = Math.min(positive, 3);
    await expect(page.locator(".review-card")).toHaveCount(total);
    if (total > 0) {
      await expect(page.locator(".review-card").first().locator(".sentiment-badge")).toHaveText("positive");
    }
  });

  test("pagination moves between pages", async ({ page }) => {
    await page.goto("/sentiment");
    await waitForPage(page);

    const next = page.getByRole("button", { name: "Next page" });
    if (await next.isEnabled()) {
      const firstBefore = (await page.locator(".review-card").first().innerText()).replace(/\s+/g, " ").trim();

      await next.click();
      await expect(page.locator(".pagination")).toContainText("Page 2");

      const firstAfter = (await page.locator(".review-card").first().innerText()).replace(/\s+/g, " ").trim();
      expect(firstAfter).not.toBe(firstBefore);

      await page.getByRole("button", { name: "Previous page" }).click();
      await expect(page.locator(".pagination")).toContainText("Page 1");
      const firstBack = (await page.locator(".review-card").first().innerText()).replace(/\s+/g, " ").trim();
      expect(firstBack).toBe(firstBefore);
    }
  });

  test("the keyword cloud shows real terms", async ({ page, request }) => {
    const data = await apiGet(request, "/api/analytics/sentiment");

    await page.goto("/sentiment");
    await waitForPage(page);

    await expect(page.locator(".keyword")).toHaveCount(data.keywords.length);
    for (const keyword of data.keywords.slice(0, 3)) {
      await expect(page.locator(".keyword-cloud")).toContainText(keyword.word);
    }
  });
});

test.describe("Consumer Insights", () => {
  test("segments match the API", async ({ page, request }) => {
    const segments = await apiGet(request, "/api/analytics/consumer-segments");

    await page.goto("/consumers");
    await waitForPage(page);

    await expect(page.locator(".segment-card")).toHaveCount(segments.length);
    for (const segment of segments) {
      const card = page.locator(".segment-card", { hasText: segment.name });
      await expect(card).toContainText(segment.size);
      await expect(card).toContainText(segment.spend);
    }
  });

  test("selecting a segment updates the spotlight", async ({ page, request }) => {
    const segments = await apiGet(request, "/api/analytics/consumer-segments");
    const second = segments[1];

    await page.goto("/consumers");
    await waitForPage(page);

    await page.locator(".segment-card", { hasText: second.name }).click();
    await expect(page.locator(".preference-panel")).toContainText(second.name);
    await expect(page.locator(".preference-panel")).toContainText(second.spend);
  });
});

test.describe("Marketing Analytics", () => {
  test("KPIs and opportunities match the API", async ({ page, request }) => {
    const data = await apiGet(request, "/api/marketing/trends");

    await page.goto("/marketing");
    await waitForPage(page);

    await expect(page.locator(".marketing-kpi")).toHaveCount(data.kpis.length);
    for (const kpi of data.kpis) {
      await expect(page.locator(".marketing-kpi", { hasText: kpi.label })).toContainText(kpi.value);
    }

    await expect(page.locator(".opportunity-card")).toHaveCount(data.opportunities.length);
    for (const opportunity of data.opportunities) {
      await expect(page.locator(".opportunity-grid")).toContainText(opportunity.title);
    }
  });

  test("the source distribution matches the API", async ({ page, request }) => {
    const data = await apiGet(request, "/api/marketing/trends");

    await page.goto("/marketing");
    await waitForPage(page);

    await expect(page.locator(".source-summary")).toContainText(data.source_volume[0].source);
  });
});

test.describe("Competitor Analysis", () => {
  test("the feature matrix matches the API", async ({ page, request }) => {
    const data = await apiGet(request, "/api/analytics/competitors");

    await page.goto("/competitors");
    await waitForPage(page);

    const headers = page.locator(".matrix-table thead th");
    await expect(headers).toHaveCount(data.features.length + 1);
    for (const feature of data.features) {
      await expect(page.locator(".matrix-table thead")).toContainText(feature);
    }

    await expect(page.locator(".matrix-table tbody tr")).toHaveCount(data.matrix.length);
  });

  test("price differences match the API", async ({ page, request }) => {
    const data = await apiGet(request, "/api/analytics/competitors");

    await page.goto("/competitors");
    await waitForPage(page);

    await expect(page.locator(".price-difference-card")).toBeVisible();
    for (const row of data.priceDifferences.slice(0, 3)) {
      await expect(page.locator(".price-difference-card")).toContainText(row.name.slice(0, 18));
    }
  });
});

test.describe("AI Recommendations", () => {
  test("the summary and items match the API", async ({ page, request }) => {
    const data = await apiGet(request, "/api/analytics/recommendations");

    await page.goto("/recommendations");
    await waitForPage(page);

    await expect(page.locator(".executive-summary")).toContainText(data.summary.headline);
    await expect(page.locator(".insight-card")).toHaveCount(data.items.length);

    for (const item of data.items.slice(0, 3)) {
      await expect(page.locator(".recommendation-list")).toContainText(item.title);
      await expect(page.locator(".recommendation-list")).toContainText(`${item.confidence}% confidence`);
    }
  });

  test("category tabs filter the list", async ({ page, request }) => {
    const all = await apiGet(request, "/api/analytics/recommendations");
    const product = await apiGet(request, "/api/analytics/recommendations?category=Product");

    await page.goto("/recommendations");
    await waitForPage(page);
    await expect(page.locator(".insight-card")).toHaveCount(all.items.length);

    await page.getByRole("button", { name: /^Product/ }).click();
    await expect(page.locator(".insight-card")).toHaveCount(product.items.length);
    for (const item of product.items) {
      await expect(page.locator(".recommendation-list")).toContainText(item.title);
    }
  });

  test("the evidence link navigates to the right page", async ({ page }) => {
    await page.goto("/recommendations");
    await waitForPage(page);

    const link = page.getByRole("link", { name: /View evidence/ }).first();
    const href = await link.getAttribute("href");
    await link.click();
    await expect(page).toHaveURL(new RegExp(`${href}$`));
    await waitForPage(page);
  });
});
