import { expect, test } from "@playwright/test";

/**
 * The in-app assistant.
 *
 * These tests drive the real streaming path against the AI backend on 8020,
 * which in turn calls the configured model. Each run spends one or two live
 * model requests, so the suite is deliberately small.
 *
 * The whole file is skipped when the AI backend is not running, so a checkout
 * with only the main API up still gets a green gate.
 */

const AI_URL = process.env.E2E_AI_URL || "http://127.0.0.1:8020";

let aiAvailable = false;

test.beforeAll(async ({ request }) => {
  try {
    const response = await request.get(`${AI_URL}/health`, { timeout: 5_000 });
    aiAvailable = response.ok();
  } catch {
    aiAvailable = false;
  }
});

test.beforeEach(async ({ page }) => {
  test.skip(!aiAvailable, `The AI backend is not running at ${AI_URL}`);
  await page.goto("/");
  await expect(page.locator(".page-loading")).toHaveCount(0, { timeout: 20_000 });
  await page.getByRole("button", { name: "Open MarketPulse AI assistant" }).click();
  await expect(page.locator(".assistant-panel")).toBeVisible();
});

test.describe("Assistant", () => {
  test("the panel opens with the page's charts registered", async ({ page }) => {
    await expect(page.locator(".assistant-header")).toContainText("MarketPulse AI");
    // The overview registers four charts, so the subtitle must not claim zero.
    await expect(page.locator(".assistant-title small")).not.toContainText("Sees 0 charts");
    await expect(page.locator(".assistant-quick button")).toHaveCount(6);
  });

  test("Stop halts the stream and marks the message", async ({ page }) => {
    await page.getByRole("textbox", { name: "Message MarketPulse AI" }).fill("Count slowly from one to fifty, one number per line.");
    await page.getByRole("button", { name: "Send message" }).click();

    // The typing indicator is replaced by the stop button as soon as the
    // request is in flight; clicking it must end the turn.
    const stop = page.getByRole("button", { name: "Stop generating" });
    await expect(stop).toBeVisible({ timeout: 20_000 });

    // Give the model a moment to actually start streaming, so this exercises
    // the abort of an in-flight body rather than a request that never started.
    await page.waitForTimeout(1_500);
    await stop.click();

    await expect(page.locator(".chat-stopped")).toBeVisible({ timeout: 10_000 });
    // The composer returns to its send state immediately.
    await expect(page.getByRole("button", { name: "Send message" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Stop generating" })).toHaveCount(0);

    // Nothing may arrive after the stop: the text is frozen.
    const frozen = await page.locator(".chat-msg.assistant .chat-markdown").last().innerText().catch(() => "");
    await page.waitForTimeout(2_000);
    const later = await page.locator(".chat-msg.assistant .chat-markdown").last().innerText().catch(() => "");
    expect(later).toBe(frozen);
  });

  test("New conversation clears the transcript", async ({ page }) => {
    await page.getByRole("textbox", { name: "Message MarketPulse AI" }).fill("Say hello in one word.");
    await page.getByRole("button", { name: "Send message" }).click();
    await expect(page.locator(".chat-msg.assistant").first()).toBeVisible({ timeout: 30_000 });

    await page.getByRole("button", { name: "Start a new conversation" }).click();
    await expect(page.locator(".chat-msg")).toHaveCount(0);
    await expect(page.locator(".assistant-welcome")).toBeVisible();
  });
});
