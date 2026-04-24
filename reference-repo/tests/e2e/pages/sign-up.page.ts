import { type Page, type Locator, expect } from "@playwright/test";
import { OtpMixin } from "./otp-mixin";

/**
 * Page Object Model for the /signup page.
 *
 * UI structure:
 * 1. Email step: email input + "Create Account" button
 * 2. OTP step: "Verify Your Email" heading + 6-digit OTP + "Complete Signup"
 */
export class SignUpPage {
  readonly page: Page;

  // Page headings
  readonly heading: Locator;

  // Email form
  readonly emailInput: Locator;
  readonly termsCheckbox: Locator;
  readonly termsLink: Locator;
  readonly createAccountButton: Locator;

  // OTP verification step
  readonly verifyHeading: Locator;

  // OTP verification (shared with SignInPage)
  readonly otp: OtpMixin;

  // Alerts
  readonly errorAlert: Locator;

  // Navigation links
  readonly signInLink: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading", {
      name: "Join Parliament Connect",
    });

    this.emailInput = page.locator('input[type="email"]');
    this.termsCheckbox = page.locator('button[role="checkbox"]').first();
    this.termsLink = page.getByRole("link", { name: "Terms & Conditions" });
    this.createAccountButton = page.getByRole("button", {
      name: "Create Account",
    });

    this.verifyHeading = page.getByRole("heading", {
      name: "Verify Your Email",
    });

    this.otp = new OtpMixin(
      page,
      page.getByRole("button", { name: "Complete Signup" })
    );

    this.errorAlert = page.locator("[data-slot='alert'].text-destructive");

    this.signInLink = page.getByRole("link", { name: "Sign in instead" });
  }

  /** Delegates to `this.otp.otpContainer` for backward compat with specs */
  get otpContainer() {
    return this.otp.otpContainer;
  }

  async navigate() {
    await this.page.goto("/signup");
    await expect(this.heading).toBeVisible();
  }

  async fillEmail(email: string) {
    await this.emailInput.clear();
    await this.emailInput.fill(email);
  }

  async submitEmail() {
    await this.createAccountButton.click();
  }

  async acceptTerms() {
    await this.termsCheckbox.click();
  }

  async fillAndSubmitEmail(email: string) {
    await this.fillEmail(email);
    await this.acceptTerms();
    await this.submitEmail();
  }
}
