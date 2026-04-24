import { test, expect } from "../fixtures/test-fixtures";
import { SignInPage } from "../pages/sign-in.page";
import { createTestSupabaseAdmin } from "../helpers/supabase-admin";
import { cleanupAppReviewUser } from "../helpers/cleanup";

// ─── App Review Password Login ──────────────────────────────────────────────
// Tests for the password-based login flow used by Facebook/App Store reviewers.
// Requires NEXT_PUBLIC_APP_REVIEW_AUTH_ENABLED=true in .env.
// Serial: all tests share the same review email + in-memory rate limiter.
// Chromium-only: the server-side rate limiter (5 attempts/15min) is shared
// across all browser projects. Running on all 5 would exhaust the limit.

const reviewEmail = process.env.NEXT_PUBLIC_APP_REVIEW_EMAIL ?? "";
const reviewPassword = process.env.APP_REVIEW_PASSWORD ?? "";
const featureEnabled =
  process.env.NEXT_PUBLIC_APP_REVIEW_AUTH_ENABLED === "true";

test.describe("App Review Password Login", () => {
  test.describe.configure({ mode: "serial" });

  let signInPage: SignInPage;

  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(!featureEnabled, "App review auth is disabled in .env");
    test.skip(!reviewEmail, "NEXT_PUBLIC_APP_REVIEW_EMAIL is not set");
    test.skip(!reviewPassword, "APP_REVIEW_PASSWORD is not set");
    test.skip(
      testInfo.project.name !== "chromium",
      "Runs on chromium only — server-side rate limiter is shared across projects"
    );

    signInPage = new SignInPage(page);
    await signInPage.navigate();
  });

  // eslint-disable-next-line no-empty-pattern
  test.afterEach(async ({}, testInfo) => {
    if (!featureEnabled || !reviewEmail) return;
    if (testInfo.project.name !== "chromium") return;
    const admin = createTestSupabaseAdmin();
    await cleanupAppReviewUser(admin, reviewEmail);
  });

  // ─── Expected Pass ──────────────────────────────────────────────

  test("correct password signs in and redirects to dashboard", async ({
    page,
    supabaseAdmin,
  }) => {
    // Submit review email — should show password form
    await signInPage.fillEmail(reviewEmail);
    await signInPage.continueButton.click();
    await expect(signInPage.passwordInput).toBeVisible({ timeout: 10_000 });

    // Submit correct password
    await signInPage.fillAndSubmitPassword(reviewPassword);

    // Should redirect to dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });
    expect(page.url()).toContain("/dashboard");

    // DB verification: user should exist in user_roles
    const { data: userRole } = await supabaseAdmin
      .from("user_roles")
      .select("role, email")
      .eq("email", reviewEmail)
      .maybeSingle();
    expect(userRole).not.toBeNull();
    expect(userRole!.email).toBe(reviewEmail);
  });

  // ─── Expected Fail ──────────────────────────────────────────────

  test("wrong password shows error", async ({ page }) => {
    await signInPage.fillEmail(reviewEmail);
    await signInPage.continueButton.click();
    await expect(signInPage.passwordInput).toBeVisible({ timeout: 10_000 });

    // Submit wrong password
    await signInPage.fillAndSubmitPassword("wrong-password-123");

    // Should show error
    await expect(signInPage.errorAlert).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByText("Invalid credentials")
    ).toBeVisible();

    // Should stay on signin page
    expect(page.url()).toContain("/signin");
  });

  // ─── UI Behavior ────────────────────────────────────────────────

  test("typing review email shows password UI hints", async ({ page }) => {
    // Default: OTP description and button
    await expect(
      page.getByRole("button", { name: "Send Verification Code" })
    ).toBeVisible();
    await expect(signInPage.formDescription).toContainText(
      "send you a 6-digit verification code"
    );

    // Type review email — UI should update reactively
    await signInPage.fillEmail(reviewEmail);
    await expect(signInPage.formDescription).toContainText(
      "sign in with your password"
    );
    await expect(signInPage.continueButton).toBeVisible();

    // Clear and type a regular email — should revert
    await signInPage.fillEmail("someone@example.com");
    await expect(signInPage.formDescription).toContainText(
      "send you a 6-digit verification code"
    );
    await expect(
      page.getByRole("button", { name: "Send Verification Code" })
    ).toBeVisible();
  });

  test("go back from password form returns to email form", async () => {
    // Navigate to password form
    await signInPage.fillEmail(reviewEmail);
    await signInPage.continueButton.click();
    await expect(signInPage.passwordInput).toBeVisible({ timeout: 10_000 });

    // Click "Use a different email"
    await signInPage.goBackFromPasswordForm();

    // Should be back on email form
    await expect(signInPage.emailInput).toBeVisible();
    await expect(signInPage.submitButton).toBeVisible();
    await expect(signInPage.passwordInput).not.toBeVisible();
  });
});
