import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end configuration.
 *
 * The suite expects the stack to be running (`./scripts/start.ps1` or
 * `./scripts/start.sh`). Set E2E_BASE_URL to point somewhere else.
 *
 * The tests assert on data that comes from the database, never on pixels, so
 * they stay stable across chart library upgrades.
 */
const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:5173";
const API_URL = process.env.E2E_API_URL || "http://127.0.0.1:8010";

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  metadata: { apiUrl: API_URL },
});
