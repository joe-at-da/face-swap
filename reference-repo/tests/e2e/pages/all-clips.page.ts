import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /dashboard/all-clips page ("All Parliament Clips").
 *
 * UI structure (from Playwright screenshots):
 * - h1 "All Parliament Clips"
 * - Search: "Text Search" / "AI Search" toggle buttons, text input
 * - Filters: "Filter by party" button (role=combobox), "Filter by MP" button (role=combobox)
 * - Date filters: "Last Week", "Last Month", "Date range" buttons
 * - Results summary: "Showing X-Y of Z clips" or "No clips found" (in paragraph)
 * - Empty state card: "No clips found matching your criteria."
 * - Clip cards: grid of AllClipCard with img, play button, MP name, description
 * - Clear filters: "Clear filters" button appears when filters active
 */
export class AllClipsPage {
  readonly page: Page;

  readonly heading: Locator;
  readonly searchInput: Locator;
  readonly textSearchButton: Locator;
  readonly aiSearchButton: Locator;
  readonly partyFilterButton: Locator;
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
      name: /all parliament clips/i,
      level: 1,
    });
    this.searchInput = page.getByPlaceholder(/search/i).first();
    this.textSearchButton = page.getByRole("button", { name: /text search/i });
    this.aiSearchButton = page.getByRole("button", { name: /ai search/i });
    // These buttons have role="combobox" from the source code
    this.partyFilterButton = page.getByRole("combobox").filter({ hasText: /filter by party|\d+ part/i });
    this.mpFilterButton = page.getByRole("combobox").filter({ hasText: /filter by mp|\d+ mp/i });
    this.lastWeekButton = page.getByRole("button", { name: /^last week$/i });
    this.lastMonthButton = page.getByRole("button", { name: /^last month$/i });
    this.dateRangeButton = page.getByRole("button", { name: /date range/i });
    // "Showing 1-24 of 2632 clips" in the results summary paragraph
    this.resultsSummary = page.getByText(/showing \d+-\d+ of \d+ clips/i);
    // "No clips found" in the summary paragraph (when total is 0)
    this.noClipsSummary = page.getByText("No clips found", { exact: true });
    // "No clips found matching your criteria." in the empty state card
    this.emptyStateCard = page.getByText(/no clips found matching/i);
    this.clearFiltersButton = page.getByRole("button", { name: /clear filters/i });
  }

  async navigate() {
    await this.page.goto("/dashboard/all-clips");
    await expect(this.heading).toBeVisible({ timeout: 30_000 });
  }

  /** Wait for the initial loading to finish — results summary or no-clips text appears */
  async waitForResults() {
    await expect(
      this.resultsSummary.or(this.noClipsSummary)
    ).toBeVisible({ timeout: 30_000 });
  }

  /** Wait specifically for the results summary with actual clip counts (not "No clips found") */
  async waitForClipsLoaded() {
    await expect(this.resultsSummary).toBeVisible({ timeout: 30_000 });
  }

  waitForSearchAllResponse() {
    return this.page.waitForResponse(
      (response) =>
        response.url().includes("/api/clips/search-all") &&
        response.request().method() === "POST" &&
        response.ok(),
      { timeout: 20_000 }
    );
  }

  waitForMpFilterOptionsResponse(searchTerm: string) {
    return this.page.waitForResponse(
      (response) => {
        if (!response.url().includes("/api/clips/filter-options")) return false;
        if (response.request().method() !== "GET" || !response.ok()) return false;
        const url = new URL(response.url());
        return (
          url.searchParams.get("type") === "mps" &&
          url.searchParams.get("search") === searchTerm
        );
      },
      { timeout: 20_000 }
    );
  }

  async search(term: string) {
    const responsePromise = this.waitForSearchAllResponse();
    await this.searchInput.clear();
    await this.searchInput.fill(term);
    await this.searchInput.press("Enter");
    await responsePromise;
    await expect
      .poll(
        () => new URL(this.page.url()).searchParams.get("search"),
        { message: `Waiting for search query param to sync to ${term}`, timeout: 10_000 }
      )
      .toBe(term);
    await this.waitForResults();
  }

  async selectParty(partyName: string) {
    await this.partyFilterButton.click();
    const searchInput = this.page.getByPlaceholder(/search parties/i);
    await expect(searchInput).toBeVisible({ timeout: 5_000 });
    await searchInput.fill(partyName);
    const partyOption = this.page.locator(`[role="option"][data-value="${partyName}"]`);
    await expect(partyOption).toBeVisible({ timeout: 10_000 });
    const responsePromise = this.waitForSearchAllResponse();
    await partyOption.click();
    // Close popover by pressing Escape
    await this.page.keyboard.press("Escape");
    await responsePromise;
    await expect(this.partyFilterButton).toContainText(/^1 party$/i);
    await this.waitForResults();
  }

  async selectMP(mpName: string) {
    await this.mpFilterButton.click();
    const searchInput = this.page.getByPlaceholder(/search mps/i);
    await expect(searchInput).toBeVisible({ timeout: 5_000 });
    const optionsResponse = this.waitForMpFilterOptionsResponse(mpName);
    await searchInput.fill(mpName);
    await optionsResponse;
    await this.page.getByText("Loading...").waitFor({ state: "hidden", timeout: 10_000 }).catch(() => {
      // The loading indicator is brief and may be gone before we start waiting.
    });
    const mpOption = this.page.getByRole("option", { name: new RegExp(mpName, "i") }).first();
    await expect(mpOption).toBeVisible({ timeout: 20_000 });
    const responsePromise = this.waitForSearchAllResponse();
    await mpOption.click();
    await this.page.keyboard.press("Escape");
    await responsePromise;
    await expect(this.mpFilterButton).toContainText(/^1 MP$/i);
    await this.waitForResults();
  }

  async getResultsText(): Promise<string> {
    await this.waitForClipsLoaded();
    return (await this.resultsSummary.textContent()) ?? "";
  }

  async clearFilters() {
    const responsePromise = this.waitForSearchAllResponse();
    await this.clearFiltersButton.click();
    await responsePromise;
    await expect(this.clearFiltersButton).toBeHidden({ timeout: 10_000 });
    await this.waitForResults();
  }
}
