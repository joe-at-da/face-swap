import { test, expect } from "../fixtures/test-fixtures";
import { SignInPage } from "../pages/sign-in.page";
import {
  getLatestEmail,
  extractOtpFromEmail,
  clearMailbox,
} from "../helpers/mailpit";
import { TEST_USERS, TEST_EMAILS, getProjectEmail } from "../helpers/test-users";

// ─── Expected to Pass ────────────────────────────────────────────────────────

// Serial within each block: tests share signinUser.email mailbox —
// parallel clearMailbox/getLatestEmail calls would pollute each other.
test.describe("Sign In — Expected Pass", () => {
  test.describe.configure({ mode: "serial" });
  let signInPage: SignInPage;

  test.beforeEach(async ({ page }) => {
    signInPage = new SignInPage(page);
    await signInPage.navigate();
  });

  test("sign in with OTP for regular user", async ({ page, supabaseAdmin }, testInfo) => {
    // First email test in the suite — cold start makes email delivery slower in CI
    test.slow();
    const email = getProjectEmail(TEST_USERS.signinUser.email, testInfo.project.name);
    await clearMailbox(email);

    // Submit email (with retry for rate limit from parallel workers)
    await signInPage.fillAndSubmitEmailWithRetry(email);

    // Wait for OTP input to appear (first request may be slow — dev server compilation)
    await expect(signInPage.otpContainer).toBeVisible({ timeout: 40_000 });

    // Get OTP from Mailpit (generous polling for CI cold start)
    const message = await getLatestEmail(email, { maxAttempts: 20, initialDelayMs: 500 });
    expect(message).not.toBeNull();
    const otp = extractOtpFromEmail(message!);
    expect(otp).not.toBeNull();
    expect(otp).toHaveLength(6);

    // Enter OTP and verify
    await signInPage.otp.fillAndSubmitOtp(otp!);

    // Should redirect to dashboard (existing user, not first login)
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });
    expect(page.url()).toContain("/dashboard");

    // DB verification: user should exist in user_roles with correct role
    const { data: userRole } = await supabaseAdmin
      .from("user_roles")
      .select("role, email")
      .eq("email", email)
      .single();
    expect(userRole).not.toBeNull();
    expect(userRole!.role).toBe("user");
  });

  test("admin user sign in with OTP", async ({ page, supabaseAdmin }) => {
    test.slow();
    const email = TEST_USERS.adminUser.email;
    await clearMailbox(email);

    await signInPage.fillAndSubmitEmailWithRetry(email);
    await expect(signInPage.otpContainer).toBeVisible({ timeout: 30_000 });

    const message = await getLatestEmail(email, { maxAttempts: 20, initialDelayMs: 500 });
    expect(message).not.toBeNull();
    const otp = extractOtpFromEmail(message!);
    expect(otp).not.toBeNull();

    await signInPage.otp.fillAndSubmitOtp(otp!);
    await page.waitForURL(/\/dashboard/, { timeout: 60_000 });

    // DB verification: should have admin role
    const { data: userRole } = await supabaseAdmin
      .from("user_roles")
      .select("role")
      .eq("email", email)
      .single();
    expect(userRole!.role).toBe("admin");
  });
});

// ─── Expected to Fail ────────────────────────────────────────────────────────

test.describe("Sign In — Expected Fail", () => {
  test.describe.configure({ mode: "serial" });
  let signInPage: SignInPage;

  test.beforeEach(async ({ page }) => {
    signInPage = new SignInPage(page);
    await signInPage.navigate();
  });

  test("non-existent email shows account not found with sign-up link", async ({
    page,
  }) => {
    await signInPage.fillAndSubmitEmail(TEST_EMAILS.nonExistent);

    // Should show ACCOUNT_NOT_FOUND error with sign-up link
    await expect(
      page.getByText("You don't have an account")
    ).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByRole("link", { name: "Go to Sign Up" })
    ).toBeVisible();

    // Should stay on sign-in page
    expect(page.url()).toContain("/signin");
  });

  test("invalid OTP code shows error", async ({ page }, testInfo) => {
    const email = getProjectEmail(TEST_USERS.signinUser.email, testInfo.project.name);
    await clearMailbox(email);

    await signInPage.fillAndSubmitEmailWithRetry(email);
    await expect(signInPage.otpContainer).toBeVisible({ timeout: 20_000 });

    // Enter wrong OTP
    await signInPage.otp.fillAndSubmitOtp("000000");

    // Should show error alert
    await expect(signInPage.errorAlert).toBeVisible({ timeout: 20_000 });

    // Should stay on sign-in page
    expect(page.url()).toContain("/signin");
  });

  test("empty email submission shows validation error", async ({ page }) => {
    await signInPage.submitEmail();

    // Form should not submit — page stays on /signin
    expect(page.url()).toContain("/signin");

    // Verify no OTP step appeared (form was not submitted)
    const otpVisible = await signInPage.otpContainer
      .isVisible({ timeout: 10_000 })
      .catch(() => false);
    expect(otpVisible).toBe(false);
  });

  test("invalid email format shows validation error", async ({ page }) => {
    await signInPage.fillAndSubmitEmail("not-an-email");

    // HTML5 native validation on type="email" prevents form submission.
    // The browser blocks the submit, so the page stays on /signin.
    // Verify the input is in an invalid state.
    const isInvalid = await signInPage.emailInput.evaluate(
      (el: HTMLInputElement) => !el.checkValidity()
    );
    expect(isInvalid).toBe(true);
    expect(page.url()).toContain("/signin");
  });
});

// ─── Edge Cases ──────────────────────────────────────────────────────────────

test.describe("Sign In — Edge Cases", () => {
  test.describe.configure({ mode: "serial" });
  let signInPage: SignInPage;

  test.beforeEach(async ({ page }) => {
    signInPage = new SignInPage(page);
    await signInPage.navigate();
  });

  test("multiple OTP requests — latest OTP works", async ({ page }, testInfo) => {
    // Double OTP flow is slow under parallel load (rate limits, email delivery).
    // WebKit and mobile Safari are especially prone to timing issues here.
    test.slow();
    const email = getProjectEmail(TEST_USERS.signinUser.email, testInfo.project.name);
    await clearMailbox(email);

    // First OTP request (with retry for parallel worker rate limit)
    await signInPage.fillAndSubmitEmailWithRetry(email);
    await expect(signInPage.otpContainer).toBeVisible({ timeout: 30_000 });

    // Go back and request a new OTP
    await signInPage.otp.goBackToEmailForm();
    await expect(signInPage.emailInput).toBeVisible();

    // Wait for rate limit to clear — GoTrue invalidates the previous OTP when a
    // new one is issued, and max_frequency=1s. Use a generous buffer so the
    // second request doesn't collide with the first (especially under CI load).
    await page.waitForTimeout(5000);
    await clearMailbox(email);

    await signInPage.fillAndSubmitEmailWithRetry(email);
    await expect(signInPage.otpContainer).toBeVisible({ timeout: 30_000 });

    // Give Mailpit a moment to receive the email (WebKit can race ahead)
    await page.waitForTimeout(2000);

    // Get the latest OTP (from second request)
    const message = await getLatestEmail(email);
    expect(message).not.toBeNull();
    const otp = extractOtpFromEmail(message!);
    expect(otp).not.toBeNull();

    await signInPage.otp.fillAndSubmitOtp(otp!);
    await page.waitForURL(/\/dashboard/, { timeout: 60_000 });
  });

  test("already authenticated user on /signin redirects to /dashboard", async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto("/signin");
    await expect
      .poll(
        () => new URL(authenticatedPage.url()).pathname,
        {
          message: "Waiting for authenticated /signin redirect to settle on /dashboard",
          timeout: 30_000,
        }
      )
      .toBe("/dashboard");
  });

  test("email case insensitivity — uppercase email works", async () => {
    const email = TEST_USERS.signinUser.email;
    await clearMailbox(email);

    // The signInSchema applies .toLowerCase(), so uppercase should work
    await signInPage.fillAndSubmitEmailWithRetry(email.toUpperCase());

    await expect(signInPage.otpContainer).toBeVisible({ timeout: 20_000 });
  });
});
