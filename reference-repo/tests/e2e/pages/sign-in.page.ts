import { type Page, type Locator, expect } from "@playwright/test";
import { OtpMixin } from "./otp-mixin";

/**
 * Page Object Model for the /signin page.
 *
 * UI structure:
 * 1. Email step: email input + "Send Verification Code" submit
 * 2. OTP step: 6-digit OTP input + "Verify & Sign In" + "Use a different email"
 * 3. Password step (app review): password input + "Sign In" + "Use a different email"
 */
export class SignInPage {
  readonly page: Page;

  // Page headings
  readonly heading: Locator;

  // Email form
  readonly emailInput: Locator;
  readonly submitButton: Locator;
  readonly continueButton: Locator;
  readonly formDescription: Locator;

  // OTP verification (shared with SignUpPage)
  readonly otp: OtpMixin;

  // Password form (app review)
  readonly passwordInput: Locator;
  readonly passwordSubmitButton: Locator;
  readonly passwordBackButton: Locator;

  // Alerts
  readonly errorAlert: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading", { name: "Welcome Back" });

    this.emailInput = page.locator('input[type="email"]');
    this.submitButton = page.getByRole("button", {
      name: "Send Verification Code",
    });
    this.continueButton = page.getByRole("button", { name: "Continue", exact: true });
    this.formDescription = page.locator("[data-slot='form-description']");

    this.otp = new OtpMixin(
      page,
      page.getByRole("button", { name: "Verify & Sign In" })
    );

    // Password form (app review)
    this.passwordInput = page.locator('input[type="password"]');
    this.passwordSubmitButton = page.getByRole("button", { name: "Sign In", exact: true });
    this.passwordBackButton = page.getByRole("button", { name: "Use a different email" });

    this.errorAlert = page.locator("[data-slot='alert'].text-destructive");
  }

  /** Delegates to `this.otp.otpContainer` for backward compat with specs */
  get otpContainer() {
    return this.otp.otpContainer;
  }

  async navigate() {
    await this.page.goto("/signin");
    await expect(this.heading).toBeVisible();
  }

  async fillEmail(email: string) {
    await this.emailInput.clear();
    await this.emailInput.fill(email);
  }

  async submitEmail() {
    await this.submitButton.click();
  }

  async fillAndSubmitEmail(email: string) {
    await this.fillEmail(email);
    await this.submitEmail();
  }

  /**
   * Submit email with retry on rate limit.
   * Parallel workers may trigger GoTrue's per-email rate limit via generateLink().
   */
  async fillAndSubmitEmailWithRetry(email: string, maxRetries = 5) {
    await this.fillEmail(email);
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      await this.submitEmail();

      // Wait for the submit to finish — button shows "Sending..." while processing
      const sendingBtn = this.page.getByRole("button", { name: /sending/i });
      if (await sendingBtn.isVisible({ timeout: 10_000 }).catch(() => false)) {
        await sendingBtn.waitFor({ state: "hidden", timeout: 40_000 }).catch(() => {});
      }

      // Check if rate limit error appeared
      await this.page.waitForTimeout(500);
      const rateLimitMsg = this.page.getByText(/you can only request this after/i);
      const rateLimited = await rateLimitMsg.isVisible().catch(() => false);
      if (!rateLimited) return;

      // Wait for the rate limit countdown to disappear
      await rateLimitMsg.waitFor({ state: "hidden", timeout: 30_000 }).catch(() => {});
      await this.page.waitForTimeout(1000);
      // Re-fill email in case the form was reset
      await this.fillEmail(email);
    }
  }

  // ── Password form (app review) ──────────────────────────────────

  async fillAndSubmitPassword(password: string) {
    await this.passwordInput.fill(password);
    await this.passwordSubmitButton.click();
  }

  async goBackFromPasswordForm() {
    await this.passwordBackButton.click();
  }
}
