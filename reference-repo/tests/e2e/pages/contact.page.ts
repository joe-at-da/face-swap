import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /contact page.
 *
 * UI structure:
 * 1. Header: Mail icon + "Get in touch" heading + subtitle
 * 2. Form card: Name + Email (2-col grid), Phone, Message (textarea), Submit button
 * 3. Success screen: CheckCircle icon + "Thank you!" + "Send another message" button
 * 4. Error state: Alert at top of form with error message
 */
export class ContactPage {
  readonly page: Page;

  // Page header
  readonly heading: Locator;
  readonly subtitle: Locator;

  // Form fields — use attribute selectors (Shadcn FormControl + Radix Slot breaks getByLabel)
  readonly nameInput: Locator;
  readonly emailInput: Locator;
  readonly phoneInput: Locator;
  readonly messageInput: Locator;

  // Buttons
  readonly submitButton: Locator;
  readonly sendingButton: Locator;

  // Success screen
  readonly successHeading: Locator;
  readonly successMessage: Locator;
  readonly sendAnotherButton: Locator;

  // Error state
  readonly errorAlert: Locator;
  readonly errorAlertText: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading", { name: "Get in touch" });
    this.subtitle = page.getByText(/contact us or request a demo/i);

    this.nameInput = page.locator('input[autocomplete="name"]');
    this.emailInput = page.locator('input[type="email"]');
    this.phoneInput = page.locator('input[type="tel"]');
    this.messageInput = page.locator("textarea");

    this.submitButton = page.getByRole("button", { name: /send message/i });
    this.sendingButton = page.getByRole("button", { name: /sending/i });

    this.successHeading = page.getByRole("heading", { name: "Thank you!" });
    this.successMessage = page.getByText(/thanks for reaching out/i);
    this.sendAnotherButton = page.getByRole("button", {
      name: /send another message/i,
    });

    this.errorAlert = page.locator("[data-slot='alert']");
    this.errorAlertText = page.locator(
      "[data-slot='alert'] [data-slot='alert-description']"
    );
  }

  async navigate() {
    await this.page.goto("/contact");
    await expect(this.heading).toBeVisible({ timeout: 20_000 });
  }

  async fillName(name: string) {
    await this.nameInput.clear();
    await this.nameInput.fill(name);
  }

  async fillEmail(email: string) {
    await this.emailInput.clear();
    await this.emailInput.fill(email);
  }

  async fillPhone(phone: string) {
    await this.phoneInput.clear();
    await this.phoneInput.fill(phone);
  }

  async fillMessage(message: string) {
    await this.messageInput.clear();
    await this.messageInput.fill(message);
  }

  async fillForm(data: {
    name: string;
    email: string;
    phone?: string;
    message: string;
  }) {
    await this.fillName(data.name);
    await this.fillEmail(data.email);
    if (data.phone) {
      await this.fillPhone(data.phone);
    }
    await this.fillMessage(data.message);
  }

  async submit() {
    await this.submitButton.click();
  }

  async fillAndSubmit(data: {
    name: string;
    email: string;
    phone?: string;
    message: string;
  }) {
    await this.fillForm(data);
    await this.submit();
  }

  /** Click away from the current field to trigger onBlur validation */
  async blurActiveField() {
    await this.heading.click();
  }

  async sendAnotherMessage() {
    await this.sendAnotherButton.click();
  }
}
