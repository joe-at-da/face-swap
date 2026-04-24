import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /dashboard/ld-clips page ("All LD Clips").
 *
 * UI structure:
 * - h1 "All LD Clips"
 * - Search: "Text Search" / "AI Search" toggle buttons, text input
 * - Filters: MP filter (scoped to LD party), "Last Week", "Last Month", "Date range" buttons
 * - Results summary: "Showing X-Y of Z clips" or "No clips found"
 * - Empty state card: "No clips found matching your criteria." or "No LD clips available."
 * - Clip cards: grid of AllClipCard with img, play button, MP name, description
 * - Clear filters: "Clear filters" button appears when filters active
 */
export class LDClipsPage {
  readonly page: Page;

  readonly heading: Locator;
  readonly searchInput: Locator;
  readonly textSearchButton: Locator;
  readonly aiSearchButton: Locator;
  readonly mpFilterButton: Locator;
  readonly lastWeekButton: Locator;
  readonly lastMonthButton: Locator;
  readonly dateRangeButton: Locator;
  readonly resultsSummary: Locator;
  readonly noClipsSummary: Locator;
  readonly emptyStateCard: Locator;
  readonly clearFiltersButton: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading", {
      name: /all ld clips/i,
      level: 1,
    });
    this.searchInput = page.getByPlaceholder(/search/i).first();
    this.textSearchButton = page.getByRole("button", { name: /text search/i });
    this.aiSearchButton = page.getByRole("button", { name: /ai search/i });
    this.mpFilterButton = page.getByRole("combobox").filter({ hasText: /filter by mp|\d+ mp/i });
    this.lastWeekButton = page.getByRole("button", { name: /^last week$/i });
    this.lastMonthButton = page.getByRole("button", { name: /^last month$/i });
    this.dateRangeButton = page.getByRole("button", { name: /date range/i });
    this.resultsSummary = page.getByText(/showing \d+-\d+ of \d+ clips/i);
    this.noClipsSummary = page.getByText("No clips found", { exact: true });
    this.emptyStateCard = page.getByText(/no clips found matching|no ld clips available/i);
    this.clearFiltersButton = page.getByRole("button", { name: /clear filters/i });
  }

  async navigate() {
    await this.page.goto("/dashboard/ld-clips");
    await expect(this.heading).toBeVisible({ timeout: 30_000 });
  }

  async waitForResults() {
    await expect(
      this.resultsSummary.or(this.noClipsSummary)
    ).toBeVisible({ timeout: 30_000 });
  }

  async waitForClipsLoaded() {
    await expect(this.resultsSummary).toBeVisible({ timeout: 30_000 });
  }

  waitForSearchLdResponse() {
    return this.page.waitForResponse(
      (response) =>
        response.url().includes("/api/clips/search-ld") &&
        response.request().method() === "POST" &&
        response.ok(),
      { timeout: 20_000 }
    );
  }

  async search(term: string) {
    const responsePromise = this.waitForSearchLdResponse();
    await this.searchInput.clear();
    await this.searchInput.fill(term);
    await this.searchInput.press("Enter");
    await responsePromise;
    await this.waitForResults();
  }

  async selectMP(mpName: string) {
    await this.mpFilterButton.click();
    const searchInput = this.page.getByPlaceholder(/search mps/i);
    await expect(searchInput).toBeVisible({ timeout: 5_000 });
    // Wait for initial options to load (triggered by opening the popover)
    await this.page.getByText("Loading...").waitFor({ state: "hidden", timeout: 15_000 }).catch(() => {});
    // Type to filter — use pressSequentially so cmdk's onValueChange fires
    await searchInput.clear();
    await searchInput.pressSequentially(mpName, { delay: 30 });
    // Wait for the matching option to appear (covers debounce + API round-trip)
    const mpOption = this.page.getByRole("option", { name: new RegExp(mpName, "i") }).first();
    await expect(mpOption).toBeVisible({ timeout: 20_000 });
    const responsePromise = this.waitForSearchLdResponse();
    await mpOption.click();
    await this.page.keyboard.press("Escape");
    await responsePromise;
    await this.waitForResults();
  }

  async getResultsText(): Promise<string> {
    await this.waitForClipsLoaded();
    return (await this.resultsSummary.textContent()) ?? "";
  }

  async clearFilters() {
    const responsePromise = this.waitForSearchLdResponse();
    await this.clearFiltersButton.click();
    await responsePromise;
    await expect(this.clearFiltersButton).toBeHidden({ timeout: 10_000 });
    await this.waitForResults();
  }
}
