import type { Page, Locator } from "@playwright/test";

/**
 * Shared OTP verification methods used by both SignInPage and SignUpPage.
 * The OTP UI is identical on both pages except for the submit button label.
 */
export class OtpMixin {
  readonly page: Page;
  readonly otpContainer: Locator;
  readonly otpSubmitButton: Locator;
  readonly useDifferentEmailButton: Locator;

  constructor(page: Page, otpSubmitButton: Locator) {
    this.page = page;
    this.otpContainer = page.locator("[data-input-otp-container].flex");
    this.otpSubmitButton = otpSubmitButton;
    this.useDifferentEmailButton = page.getByRole("button", {
      name: "Use a different email",
    });
  }

  async fillOtp(code: string) {
    await this.otpContainer.click();
    await this.page.keyboard.type(code);
  }

  async submitOtp() {
    await this.otpSubmitButton.click();
  }

  async fillAndSubmitOtp(code: string) {
    await this.fillOtp(code);
    await this.submitOtp();
  }

  async goBackToEmailForm() {
    await this.useDifferentEmailButton.click();
  }
}
