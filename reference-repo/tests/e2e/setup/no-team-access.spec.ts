import { test, expect } from "../fixtures/test-fixtures";
import { NoTeamAccessPage } from "../pages/no-team-access.page";

test.describe("No Team Access — Expected Pass", () => {
  test("displays heading, reason list, and action cards", async ({
    noTeamAccessPage,
  }) => {
    await expect(noTeamAccessPage).toHaveURL(/\/no-team-access/, { timeout: 30_000 });
    const noTeamPage = new NoTeamAccessPage(noTeamAccessPage);
    await noTeamPage.verifyContent();
  });

  test("'Return to Home' link navigates to /", async ({
    noTeamAccessPage,
  }) => {
    const noTeamPage = new NoTeamAccessPage(noTeamAccessPage);
    await noTeamPage.clickReturnHome();
    // Should navigate to home page "/"
    await expect(noTeamAccessPage).toHaveURL("/", { timeout: 30_000 });
  });

  test("'Sign Out' button signs out and redirects to /", async ({
    noTeamAccessPage,
  }) => {
    test.slow();
    const noTeamPage = new NoTeamAccessPage(noTeamAccessPage);
    await expect(noTeamPage.signOutButton).toBeVisible({ timeout: 30_000 });
    await noTeamPage.signOutButton.click();
    await expect(noTeamAccessPage).toHaveURL("/", { timeout: 30_000 });
  });
});

test.describe("No Team Access — Expected Fail", () => {
  test("regular user can visit /no-team-access (no guard redirect)", async ({
    authenticatedPage,
  }) => {
    // /no-team-access is accessible to any authenticated user — no middleware redirect
    await authenticatedPage.goto("/no-team-access");
    await expect(authenticatedPage).toHaveURL(/\/no-team-access/, {
      timeout: 20_000,
    });
  });
});

test.describe("No Team Access — Edge Cases", () => {
  test("user with active team membership redirects to /dashboard", async ({
    teamSetupPage,
  }) => {
    test.slow();
    // NOTE: Uses teamSetupPage fixture (e2e-team-member@test.local) which resets
    // is_first_login in afterEach. This creates cross-spec coupling with team-setup.spec.ts
    // if both run in the same worker. Acceptable because this test only reads state.
    await teamSetupPage.goto("/no-team-access");
    await expect(teamSetupPage).toHaveURL(/\/(dashboard|team-setup)/, {
      timeout: 20_000,
    });
  });
});
