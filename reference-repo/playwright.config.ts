import { defineConfig, devices } from "@playwright/test";
import dotenv from "dotenv";

/**
 * Load .env (set by setup-worktree.sh with Docker Compose ports/keys).
 * All Supabase URLs, keys, and frontend URL come from here.
 */
dotenv.config();

/**
 * Base URL: NEXT_PUBLIC_FRONTEND_URL (set by setup-worktree.sh) or localhost:3001.
 * Both local dev and CI use the same Docker Compose stack via setup-worktree.sh.
 */
const BASE_URL =
  process.env.NEXT_PUBLIC_FRONTEND_URL ||
  "http://localhost:3001";

/**
 * Playwright Test configuration for Next.js + Supabase project.
 * See https://playwright.dev/docs/test-configuration
 *
 * Tests run against the Docker dev environment started by setup-worktree.sh.
 * No webServer is needed — the Next.js app is already running in Docker.
 */
export default defineConfig({
  testDir: "./tests/e2e",

  /* Global setup/teardown for test user pre-seeding and cleanup */
  globalSetup: "./tests/global-setup.ts",
  globalTeardown: "./tests/global-teardown.ts",

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Global test timeout — some tests with slow fixtures need headroom */
  timeout: 120_000,

  /* Retry transient failures (dev server compilation, Docker contention) */
  retries: process.env.CI ? 2 : 1,

  /* Bound worker count to avoid resource contention */
  workers: process.env.CI ? 4 : 6,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ["html", { outputFolder: "playwright-report" }],
    ["list"],
    ...(process.env.CI
      ? [["json", { outputFile: "playwright-results.json" }] as const]
      : []),
  ],

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: BASE_URL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: "on-first-retry",

    /* Take screenshot on failure */
    screenshot: "only-on-failure",

    /* Record video on failure */
    video: "retain-on-failure",

    /* Default action timeout — CI is slower due to JIT page compilation */
    actionTimeout: process.env.CI ? 30_000 : 10_000,
  },

  /* Configure projects for major browsers — desktop and mobile */
  projects: [
    /* Desktop browsers */
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },

    /* Mobile browsers */
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 5"] },
    },
    {
      name: "mobile-safari",
      use: { ...devices["iPhone 13"] },
    },
  ],

  /* No webServer needed — Docker dev environment provides the Next.js app.
   * Start Docker with: ./setup-worktree.sh */
});
