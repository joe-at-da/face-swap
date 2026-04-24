import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /dashboard/my-clips page.
 *
 * UI structure (from Playwright snapshot):
 * - "My Clips" h1 heading
 * - Search input: "Search clips by transcript content or topic..."
 * - Status combobox filter (All Statuses)
 * - Date range shortcuts: "Last Week", "Last Month", "Date range" button
 * - "Showing X of Y clips" paragraph
 * - Clip cards: each has img "Clip thumbnail", status badge, duration, delete button, view link
 * - Pagination: navigation "pagination"
 */
export class MyClipsPage {
  readonly page: Page;

  readonly heading: Locator;
  readonly searchInput: Locator;
  readonly lastWeekButton: Locator;
  readonly clipCards: Locator;
  readonly resultsSummary: Locator;
  readonly emptyState: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading", { name: /my clips/i });
    this.searchInput = page.getByPlaceholder(
      /search clips by transcript/i
    );
    this.lastWeekButton = page.getByRole("button", { name: /last week/i });

    // Clip cards contain thumbnail images
    this.clipCards = page.locator("img[alt='Clip thumbnail']").locator("..");
    this.resultsSummary = page.getByText(/showing \d+ of \d+ clips/i);
    this.emptyState = page.getByText(/no clips|no results/i);
  }

  async navigate() {
    await this.page.goto("/dashboard/my-clips");
    await expect(this.heading).toBeVisible({ timeout: 20_000 });
  }

  async search(term: string) {
    await this.searchInput.clear();
    await this.searchInput.fill(term);
  }

  async getClipCount(): Promise<number> {
    return await this.clipCards.count();
  }

  async deleteClip(index: number) {
    const card = this.clipCards.nth(index);
    // The three-dot menu button has no accessible name — target by role within card
    const menuTrigger = card.getByRole("button").first();
    await menuTrigger.click();
    // Click the Delete menuitem in the dropdown
    await this.page.getByRole("menuitem", { name: /delete/i }).click();
    // Confirm the deletion dialog
    const confirmButton = this.page.getByRole("button", {
      name: /confirm|yes|delete/i,
    });
    await expect(confirmButton).toBeVisible({ timeout: 10_000 });
    await confirmButton.click();
  }
}
