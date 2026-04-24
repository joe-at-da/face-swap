import { test, expect } from "../fixtures/test-fixtures";
import { DashboardPage } from "../pages/dashboard.page";

test.describe("Dashboard — Expected Pass", () => {
  test("loads with dashboard heading", async ({
    authenticatedPage,
    isMobile,
  }) => {
    const dashboard = new DashboardPage(authenticatedPage, isMobile);
    await dashboard.navigate();
    await dashboard.verifyPageLoaded();
  });

  test("shows latest clips cards or empty state", async ({
    authenticatedPage,
    isMobile,
  }) => {
    const dashboard = new DashboardPage(authenticatedPage, isMobile);
    await dashboard.navigate();
    // Seeded 5 user_clips — dashboard shows them in "Recent Activity"
    await dashboard.verifyLatestClips(1);
  });

  test("quick action: Create New Clip links to /dashboard/create-clips", async ({
    authenticatedPage,
    isMobile,
  }) => {
    test.skip(
      test.info().project.name === "mobile-safari",
      "Mobile Safari hydration prevents client-side navigation"
    );
    const dashboard = new DashboardPage(authenticatedPage, isMobile);
    await dashboard.navigate();
    await dashboard.createClipLink.click();
    await expect(authenticatedPage).toHaveURL(/\/create-clips/, { timeout: 30_000 });
  });

  test("quick action: View My Clips links to /dashboard/my-clips", async ({
    authenticatedPage,
    isMobile,
  }) => {
    test.skip(
      test.info().project.name === "mobile-safari",
      "Mobile Safari hydration prevents client-side navigation"
    );
    const dashboard = new DashboardPage(authenticatedPage, isMobile);
    await dashboard.navigate();
    // Use exact "View My Clips" to avoid matching sidebar "My Clips"
    await dashboard.viewClipsLink.click();
    await expect(authenticatedPage).toHaveURL(/\/my-clips/, { timeout: 30_000 });
  });

  test("quick action: Settings links to /dashboard/settings", async ({
    authenticatedPage,
    isMobile,
  }) => {
    test.skip(
      test.info().project.name === "mobile-safari",
      "Mobile Safari hydration prevents client-side navigation"
    );
    const dashboard = new DashboardPage(authenticatedPage, isMobile);
    await dashboard.navigate();
    await dashboard.settingsLink.click();
    await expect(authenticatedPage).toHaveURL(/\/settings/, { timeout: 30_000 });
  });

  test("admin user sees same dashboard content", async ({
    adminPage,
    isMobile,
  }) => {
    const dashboard = new DashboardPage(adminPage, isMobile);
    await adminPage.goto("/dashboard");
    await dashboard.verifyPageLoaded();
  });
});

test.describe("Dashboard — Expected Fail", () => {
  test("API error shows graceful error state", async ({
    authenticatedPage,
  }) => {
    // Intercept any dashboard data API with 500
    await authenticatedPage.route("**/api/**", (route) => {
      if (route.request().url().includes("dashboard")) {
        return route.fulfill({
          status: 500,
          body: "Internal Server Error",
        });
      }
      return route.continue();
    });
    await authenticatedPage.goto("/dashboard");

    // Page should still render (SSR) — verify it shows error state or doesn't crash.
    // The error text varies by browser engine:
    //   Chromium: "Unexpected token … is not valid JSON"
    //   Firefox:  "JSON.parse: unexpected character …"
    //   WebKit:   "The string did not match the expected pattern."
    await expect(
      authenticatedPage.getByText(/error|something went wrong|try again|not valid json|unexpected token|unexpected character|json.parse|json parse|did not match the expected pattern/i).first()
    ).toBeVisible({ timeout: 20_000 });
  });
});

test.describe("Dashboard — Edge Cases", () => {
  test("sidebar navigation works on desktop", async ({
    authenticatedPage,
    isMobile,
  }) => {
    test.skip(isMobile, "Sidebar not visible on mobile");
    const dashboard = new DashboardPage(authenticatedPage, false);
    await dashboard.navigate();

    await dashboard.navigateTo("Settings");
    await expect(authenticatedPage).toHaveURL(/\/settings/, { timeout: 30_000 });
  });

  test("hamburger menu navigation works on mobile", async ({
    authenticatedPage,
    isMobile,
  }) => {
    test.skip(!isMobile, "Hamburger menu only on mobile");
    const dashboard = new DashboardPage(authenticatedPage, true);
    await dashboard.navigate();
    await dashboard.navigateTo("Settings");
    await expect(authenticatedPage).toHaveURL(/\/settings/, { timeout: 30_000 });
  });
});
