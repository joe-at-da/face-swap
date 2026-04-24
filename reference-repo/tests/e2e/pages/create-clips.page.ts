import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /dashboard/create-clips page ("Speech Library").
 *
 * UI structure (from Playwright snapshot):
 * - h1 "Speech Library"
 * - MP info: h2 with MP name, party paragraph, constituency paragraph
 * - Search: "Text Search" / "AI Search" toggle, text input
 * - Date filters: "Last Week", "Last Month", "Date range"
 * - Results summary: "Showing X-Y of Z clips"
 * - Clip cards: generic [cursor=pointer] with img, duration, description
 * - No data-testid attributes on cards
 */
export class CreateClipsPage {
  readonly page: Page;

  readonly heading: Locator;
  readonly mpName: Locator;
  readonly searchBar: Locator;
  readonly lastWeekButton: Locator;
  readonly lastMonthButton: Locator;
  readonly resultsSummary: Locator;
  readonly clipCards: Locator;
  readonly emptyState: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading", {
      name: /speech library|create clips/i,
      level: 1,
    });
    // MP name is the h2 below the h1
    this.mpName = page.getByRole("heading", { level: 2 }).first();
    this.searchBar = page.getByRole("textbox", {
      name: /search/i,
    });
    this.lastWeekButton = page.getByRole("button", { name: /last week/i });
    this.lastMonthButton = page.getByRole("button", { name: /last month/i });
    this.resultsSummary = page.getByText(/showing .+ of \d+ clips/i);
    // Clip cards are cursor=pointer generic elements containing paragraph descriptions
    // Use the "More Options" button that each clip has
    this.clipCards = page.getByRole("button", { name: /more options/i });
    this.emptyState = page.getByText(/no clips|no results|no speeches/i);
  }

  async navigate() {
    await this.page.goto("/dashboard/create-clips");
    await expect(this.heading).toBeVisible({ timeout: 20_000 });
  }

  async search(term: string) {
    await this.searchBar.clear();
    await this.searchBar.fill(term);
    await this.searchBar.press("Enter");
    // Wait for results to update (debounce + network)
    await this.page.waitForTimeout(2000);
  }

  async getClipCount(): Promise<number> {
    return await this.clipCards.count();
  }
}
