import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /mp-setup page.
 */
export class MpSetupPage {
  readonly page: Page;

  readonly heading: Locator;
  readonly completeButton: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading").first();
    this.completeButton = page.getByRole("button", {
      name: /complete|continue|finish/i,
    });
  }

  async navigate() {
    await this.page.goto("/mp-setup");
    await expect(this.heading).toBeVisible({ timeout: 20_000 });
  }

  async verifyMPInfo(data: { name: string; constituency?: string }) {
    // Use .first() — the MP name appears in multiple page sections
    await expect(this.page.getByText(data.name).first()).toBeVisible();
    if (data.constituency) {
      await expect(this.page.getByText(data.constituency).first()).toBeVisible();
    }
  }

  async completeSetup() {
    // Wait for hydration — WebKit can try clicking before React attaches handlers
    await this.page.waitForLoadState("networkidle");
    await this.completeButton.scrollIntoViewIfNeeded();

    // Try native click first, then force click, then JS .click() as final fallback.
    // WebKit/mobile Safari overlays can intercept native clicks.
    try {
      await this.completeButton.click({ timeout: 5_000 });
    } catch {
      try {
        await this.completeButton.click({ force: true, timeout: 5_000 });
      } catch {
        await this.completeButton.evaluate((el) =>
          (el as HTMLButtonElement).click()
        );
      }
    }
  }
}
