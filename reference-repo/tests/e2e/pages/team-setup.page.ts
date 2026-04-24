import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /team-setup page.
 */
export class TeamSetupPage {
  readonly page: Page;

  readonly heading: Locator;
  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly avatarUpload: Locator;
  readonly completeButton: Locator;
  readonly errorAlert: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading").first();
    this.firstNameInput = page.getByLabel(/first name/i);
    this.lastNameInput = page.getByLabel(/last name/i);
    this.avatarUpload = page.locator('input[type="file"]');
    this.completeButton = page.getByRole("button", {
      name: /complete|continue|finish/i,
    });
    this.errorAlert = page.locator("[data-slot='alert']");
  }

  async navigate() {
    await this.page.goto("/team-setup");
    await expect(this.heading).toBeVisible({ timeout: 20_000 });
  }

  async fillProfile(firstName: string, lastName: string) {
    await this.firstNameInput.clear();
    await this.firstNameInput.fill(firstName);
    await this.lastNameInput.clear();
    await this.lastNameInput.fill(lastName);
  }

}
