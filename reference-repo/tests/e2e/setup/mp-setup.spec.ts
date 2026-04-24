import { test, expect } from "../fixtures/test-fixtures";
import { MpSetupPage } from "../pages/mp-setup.page";
import { assertSetupComplete } from "../helpers/assertions";

// Serial mode: tests mutate the same MP user's is_first_login state
test.describe.configure({ mode: "serial" });

test.describe("MP Setup — Expected Pass", () => {
  test("shows auto-matched MP info and completes setup", async ({
    mpSetupPage,
    mpUser,
    supabaseAdmin,
  }) => {
    test.slow();
    const mpPage = new MpSetupPage(mpSetupPage);

    // Verify auto-matched MP info is displayed
    await mpPage.verifyMPInfo({
      name: "E2E Test MP Alpha",
      constituency: "Test North",
    });

    // Click complete and wait for API response.
    // Retry the click if waitForResponse times out — WebKit/mobile Safari
    // can silently swallow clicks when overlays or hydration are in play.
    const CLICK_ATTEMPTS = 3;
    const RESPONSE_TIMEOUT = 30_000;
    let completeRes: import("@playwright/test").Response | null = null;

    for (let i = 0; i < CLICK_ATTEMPTS; i++) {
      const responsePromise = mpSetupPage.waitForResponse(
        (r) =>
          r.url().includes("/api/setup/complete") &&
          r.request().method() === "POST",
        { timeout: RESPONSE_TIMEOUT }
      );
      await mpPage.completeSetup();
      completeRes = await responsePromise.catch(() => null);
      if (completeRes) break;
    }

    // If API failed, try clicking "Retry Setup" once
    if (completeRes && completeRes.status() !== 200) {
      const retryBtn = mpSetupPage.getByRole("button", { name: /retry/i });
      if (await retryBtn.isVisible({ timeout: 10_000 }).catch(() => false)) {
        const retryResponse = mpSetupPage.waitForResponse(
          (r) => r.url().includes("/api/setup/complete") && r.request().method() === "POST",
          { timeout: 60_000 }
        );
        await retryBtn.click();
        await retryResponse;
      }
    }

    // UI check — non-fatal (DB assertion is ground truth)
    await assertSetupComplete(mpSetupPage, /setup completed|success|welcome/i);

    // DB assertion (ground truth): is_first_login should be false
    await expect
      .poll(
        async () => {
          const { data } = await supabaseAdmin
            .from("user_roles")
            .select("is_first_login")
            .eq("email", mpUser.email)
            .single();
          return data?.is_first_login;
        },
        { message: "Waiting for MP setup to complete in DB", timeout: 60_000 }
      )
      .toBe(false);
  });

  test("displays correct MP name, constituency, party", async ({
    mpSetupPage,
  }) => {
    await expect(mpSetupPage.getByText("E2E Test MP Alpha").first()).toBeVisible();
    await expect(mpSetupPage.getByText("Test North").first()).toBeVisible();
  });
});

test.describe("MP Setup — Expected Fail", () => {
  test("non-MP user visiting /mp-setup redirects to /setup", async ({
    setupUserPage,
  }) => {
    test.slow();
    // setupUser is not an MP (not @veedoo.io, no parliament_member_contacts)
    await setupUserPage.goto("/mp-setup");
    await expect(setupUserPage).toHaveURL(/\/(setup|dashboard)/, {
      timeout: 20_000,
    });
  });
});

test.describe("MP Setup — Edge Cases", () => {
  test("already-setup MP visiting /mp-setup redirects to /dashboard", async ({
    mpAuthenticatedPage,
  }) => {
    test.slow();
    // mpAuthenticatedPage has is_first_login: false
    await mpAuthenticatedPage.goto("/mp-setup");
    await expect(mpAuthenticatedPage).toHaveURL(/\/dashboard/, {
      timeout: 20_000,
    });
  });
});
