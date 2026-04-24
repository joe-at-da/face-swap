import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /no-team-access page.
 */
export class NoTeamAccessPage {
  readonly page: Page;

  readonly heading: Locator;
  readonly reasonsList: Locator;
  readonly returnHomeButton: Locator;
  readonly signOutButton: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading", { name: /no team access/i });
    this.reasonsList = page.locator("ul");
    this.returnHomeButton = page.getByRole("link", {
      name: /return to home/i,
    });
    this.signOutButton = page.getByRole("button", { name: /sign out/i });
  }

  async navigate() {
    await this.page.goto("/no-team-access");
    await expect(this.heading).toBeVisible({ timeout: 30_000 });
  }

  async verifyContent() {
    await expect(this.heading).toBeVisible({ timeout: 30_000 });
    await expect(this.reasonsList).toBeVisible({ timeout: 10_000 });
    await expect(this.returnHomeButton).toBeVisible({ timeout: 10_000 });
    await expect(this.signOutButton).toBeVisible({ timeout: 10_000 });
  }

  async clickReturnHome() {
    await this.returnHomeButton.scrollIntoViewIfNeeded();
    await this.returnHomeButton.click({ timeout: 10_000 }).catch(async () => {
      await this.returnHomeButton.evaluate((node) => {
        (node as HTMLAnchorElement).click();
      });
    });
  }
}
