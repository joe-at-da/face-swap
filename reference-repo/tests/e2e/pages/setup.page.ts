import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /setup wizard page.
 */
export class SetupPage {
  readonly page: Page;

  // Step headings
  readonly stepHeading: Locator;

  // Step 1: Profile
  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly avatarUpload: Locator;
  readonly continueButton: Locator;
  readonly previousButton: Locator;

  // Step 3: MP Selection
  readonly mpSearchInput: Locator;
  readonly completeSetupButton: Locator;

  // Validation errors
  readonly errorAlert: Locator;

  constructor(page: Page) {
    this.page = page;

    this.stepHeading = page.getByRole("heading").first();

    this.firstNameInput = page.getByLabel(/first name/i);
    this.lastNameInput = page.getByLabel(/last name/i);
    this.avatarUpload = page.locator('input[type="file"]');
    this.continueButton = page.getByRole("button", { name: "Continue" });
    this.previousButton = page.getByRole("button", {
      name: /previous|back/i,
    });

    this.mpSearchInput = page.getByPlaceholder(/search/i);
    this.completeSetupButton = page.getByRole("button", {
      name: /complete|finish/i,
    });

    this.errorAlert = page.locator("[data-slot='alert'].text-destructive");
  }

  async navigate() {
    await this.page.goto("/setup");
    await expect(this.stepHeading).toBeVisible({ timeout: 20_000 });
  }

  async fillProfile(firstName: string, lastName: string) {
    await this.firstNameInput.clear();
    await this.firstNameInput.fill(firstName);
    await this.lastNameInput.clear();
    await this.lastNameInput.fill(lastName);
  }

  async clickContinue() {
    await expect(this.continueButton).toBeVisible({ timeout: 20_000 });
    await expect(this.continueButton).toBeEnabled({ timeout: 20_000 });
    await this.continueButton.scrollIntoViewIfNeeded();
    // Prefer a real click, but fall back to HTMLElement.click() if Firefox
    // actionability checks race with step-transition overlays.
    await this.continueButton.click({ timeout: 10_000 }).catch(async () => {
      await this.continueButton.evaluate((button: HTMLElement) => button.click());
    });
  }

  async clickPrevious() {
    await this.previousButton.click({ force: true });
  }

  async searchMP(term: string) {
    await this.mpSearchInput.clear();
    await this.mpSearchInput.fill(term);
  }

  async selectMP(name: string) {
    const option = this.page.getByText(name, { exact: false }).first();
    await option.click();
    await this.page.keyboard.press("Escape"); // close any dropdown overlay
    await option.waitFor({ state: "hidden", timeout: 10_000 }).catch(() => {
      // Dropdown may already be closed; proceed regardless
    });
  }

  async clickCompleteSetup() {
    // force: true needed — setup wizard step overlay can intercept normal clicks
    await this.completeSetupButton.scrollIntoViewIfNeeded();
    await this.completeSetupButton.click({ force: true });
  }
}
