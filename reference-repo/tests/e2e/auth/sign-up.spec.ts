import { test, expect } from "../fixtures/test-fixtures";
import { SignUpPage } from "../pages/sign-up.page";
import {
  getLatestEmail,
  extractOtpFromEmail,
  clearMailbox,
} from "../helpers/mailpit";
import { TEST_EMAILS } from "../helpers/test-users";
import { cleanupTestUser } from "../helpers/cleanup";
import { createTestSupabaseAdmin } from "../helpers/supabase-admin";

// ─── Expected to Pass ────────────────────────────────────────────────────────

test.describe("Sign Up — Expected Pass", () => {
  // Use @veedoo.io email since canUserSignUp() requires MP email or invitation
  const freshMPEmail = TEST_EMAILS.signUpMp;
  let signUpPage: SignUpPage;

  test.beforeEach(async ({ page }) => {
    signUpPage = new SignUpPage(page);

    // Clean up any existing test user before each test
    const admin = createTestSupabaseAdmin();
    await cleanupTestUser(admin, freshMPEmail);
    await clearMailbox(freshMPEmail);

    await signUpPage.navigate();
  });

  test.afterEach(async () => {
    // Always clean up created users
    const admin = createTestSupabaseAdmin();
    await cleanupTestUser(admin, freshMPEmail);
  });

  test("sign up with MP email, verify OTP, and confirm user in DB", async ({
    page,
    supabaseAdmin,
  }) => {
    await signUpPage.fillAndSubmitEmail(freshMPEmail);

    // Should show OTP verification step
    await expect(signUpPage.otpContainer).toBeVisible({ timeout: 30_000 });

    // Get OTP from Mailpit
    const message = await getLatestEmail(freshMPEmail);
    expect(message).not.toBeNull();
    const otp = extractOtpFromEmail(message!);
    expect(otp).not.toBeNull();
    expect(otp).toHaveLength(6);

    // Complete signup
    await signUpPage.otp.fillAndSubmitOtp(otp!);

    // @veedoo.io is treated as MP → first login redirects to /mp-setup
    await page.waitForURL(/\/(mp-setup|setup|dashboard)/, { timeout: 30_000 });

    // DB verification: user should exist in user_roles (targeted query, no full scan)
    const { data: userRole } = await supabaseAdmin
      .from("user_roles")
      .select("user_id, email")
      .eq("email", freshMPEmail)
      .single();
    expect(userRole).not.toBeNull();
    expect(userRole!.email).toBe(freshMPEmail);

    const { data: termsAcceptance } = await supabaseAdmin
      .from("terms_acceptances")
      .select("accepted_via, user_id")
      .eq("user_id", userRole!.user_id)
      .single();

    expect(termsAcceptance).not.toBeNull();
    expect(termsAcceptance!.accepted_via).toBe("signup");
  });
});

// ─── Expected to Fail ────────────────────────────────────────────────────────

test.describe("Sign Up — Expected Fail", () => {
  let signUpPage: SignUpPage;

  test.beforeEach(async ({ page }) => {
    signUpPage = new SignUpPage(page);
    await signUpPage.navigate();
  });

  test("non-MP email without invitation shows restriction error", async ({
    page,
  }) => {
    await signUpPage.fillEmail(TEST_EMAILS.nonMpEmail);
    await signUpPage.acceptTerms();
    await signUpPage.submitEmail();

    // canUserSignUp returns "Sign up is currently limited to MPs..." for non-MP emails
    await expect(
      page.getByText(/sign up is currently limited/i)
    ).toBeVisible({ timeout: 20_000 });

    // Should stay on signup page
    expect(page.url()).toContain("/signup");
  });

  test("invalid email format shows validation error", async ({ page }) => {
    await signUpPage.fillAndSubmitEmail("not-valid-email");

    // HTML5 native validation on type="email" prevents form submission.
    const isInvalid = await signUpPage.emailInput.evaluate(
      (el: HTMLInputElement) => !el.checkValidity()
    );
    expect(isInvalid).toBe(true);
    expect(page.url()).toContain("/signup");
  });

  test("empty form submission stays on page", async ({ page }) => {
    await signUpPage.submitEmail();

    // Form should not submit — stay on signup page
    expect(page.url()).toContain("/signup");
  });

  test("terms checkbox is required before signup", async ({ page }) => {
    await signUpPage.fillEmail(TEST_EMAILS.signUpMp);
    await signUpPage.submitEmail();

    await expect(
      page.getByText("You must agree to the Terms & Conditions")
    ).toBeVisible({ timeout: 10_000 });
    expect(page.url()).toContain("/signup");
  });
});

// ─── Edge Cases ──────────────────────────────────────────────────────────────

test.describe("Sign Up — Edge Cases", () => {
  let signUpPage: SignUpPage;

  test.beforeEach(async ({ page }) => {
    signUpPage = new SignUpPage(page);
    await signUpPage.navigate();
  });

  test("double-clicking create account does not cause errors", async ({
    page,
  }) => {
    const email = TEST_EMAILS.doubleClick;
    const admin = createTestSupabaseAdmin();
    await cleanupTestUser(admin, email);
    await clearMailbox(email);

    await signUpPage.fillEmail(email);
    await signUpPage.acceptTerms();

    // Double click the submit button rapidly
    await signUpPage.createAccountButton.dblclick();

    // Should either show OTP step or rate-limit message (not just pre-existing button)
    await expect(
      signUpPage.otp.otpContainer.or(page.getByText(/rate limit|too many|try again/i))
    ).toBeVisible({ timeout: 30_000 });

    // Should not show an unexpected error — either OTP visible or loading state
    const hasError = await page
      .getByText(/unexpected error/i)
      .isVisible()
      .catch(() => false);
    expect(hasError).toBe(false);

    // Cleanup
    await cleanupTestUser(admin, email);
  });

  test("already authenticated user on /signup redirects to /dashboard", async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto("/signup");
    // Middleware or client-side redirect should send to /dashboard
    await authenticatedPage.waitForURL(/\/dashboard/, { timeout: 20_000 });
  });

  test("sign-up page has working link to sign-in", async ({ page }) => {
    await expect(signUpPage.signInLink).toBeVisible();
    await signUpPage.signInLink.click();
    await page.waitForURL(/\/signin/, { timeout: 30_000 });
  });

  test("sign-up page links to terms and conditions", async () => {
    await expect(signUpPage.termsLink).toBeVisible();
    await expect(signUpPage.termsLink).toHaveAttribute("href", "/terms-and-conditions");
  });

  test("sign-in page has working link to sign-up", async ({ page }) => {
    await page.goto("/signin");
    const signUpLink = page.getByRole("link", { name: "Sign up" });
    await expect(signUpLink).toBeVisible();
    await signUpLink.click();
    await page.waitForURL(/\/signup/, { timeout: 30_000 });
  });
});
