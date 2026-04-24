import { type Page, test as baseTest, expect as baseExpect } from "@playwright/test";
import { test } from "../fixtures/test-fixtures";

/**
 * Auth guards: verify protected routes redirect unauthenticated users
 * and allow authenticated users through.
 */

const protectedRoutes = [
  "/dashboard",
  "/dashboard/settings",
  "/dashboard/my-clips",
  "/dashboard/create-clips",
  "/setup",
  "/mp-setup",
  "/team-setup",
  "/no-team-access",
];

const dashboardRoutes = [
  "/dashboard",
  "/dashboard/settings",
  "/dashboard/my-clips",
  "/dashboard/create-clips",
];

function getPathname(page: Page) {
  return new URL(page.url()).pathname;
}

// ── Expected Pass: authenticated users CAN access protected routes ──

test.describe("Auth Guards — Expected Pass", () => {
  for (const route of dashboardRoutes) {
    test(`authenticated user can access ${route}`, async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(route);
      await baseExpect
        .poll(
          () => getPathname(authenticatedPage),
          { message: `Waiting for authenticated user to settle on ${route}`, timeout: 30_000 }
        )
        .toBe(route);
    });
  }
});

// ── Expected Fail: unauthenticated → redirect to / ─────────────────

baseTest.describe("Auth Guards — Expected Fail", () => {
  for (const route of protectedRoutes) {
    baseTest(
      `unauthenticated visit to ${route} redirects to /`,
      async ({ page }) => {
        await page.goto(route);
        await baseExpect
          .poll(
            () => getPathname(page),
            { message: `Waiting for unauthenticated redirect from ${route}`, timeout: 30_000 }
          )
          .toBe("/");
      }
    );
  }
});

// ── Edge Cases ──────────────────────────────────────────────────────

baseTest.describe("Auth Guards — Edge Cases", () => {
  baseTest(
    "deep link with query params redirects unauthenticated user",
    async ({ page }) => {
      await page.goto("/dashboard?tab=clips");
      await baseExpect
        .poll(
          () => getPathname(page),
          { message: "Waiting for unauthenticated deep link redirect", timeout: 30_000 }
        )
        .toBe("/");
    }
  );
});
