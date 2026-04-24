import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /dashboard page.
 *
 * UI structure (from Playwright snapshot):
 * - Sidebar: Dashboard, My Clips, Settings nav links
 * - Main: "Parliamentary Dashboard" heading
 *   - "Latest Clips" section (may show empty state or clip links)
 *   - "Quick Actions" section with 3 cards: Create New Clip, View My Clips, Manage Settings
 *   - "Recent Activity" section with activity items
 */
export class DashboardPage {
  readonly page: Page;
  readonly isMobile: boolean;

  // Page elements
  readonly heading: Locator;
  readonly latestClipsHeading: Locator;
  readonly emptyClipsState: Locator;

  // Quick action links (scoped to quick actions section)
  readonly createClipLink: Locator;
  readonly viewClipsLink: Locator;
  readonly settingsLink: Locator;

  // Mobile navigation
  readonly hamburgerButton: Locator;

  constructor(page: Page, isMobile: boolean = false) {
    this.page = page;
    this.isMobile = isMobile;

    this.heading = page.getByRole("heading", {
      name: /parliamentary dashboard/i,
      level: 1,
    });
    this.latestClipsHeading = page.getByRole("heading", {
      name: /latest clips/i,
      level: 2,
    });
    this.emptyClipsState = page.getByRole("heading", {
      name: /no clips available/i,
    });

    // Quick action links — use exact heading text to disambiguate from sidebar
    this.createClipLink = page.getByRole("link", {
      name: /Create New Clip/,
    });
    this.viewClipsLink = page.getByRole("link", {
      name: /View My Clips/,
    });
    this.settingsLink = page.getByRole("link", {
      name: /Manage Settings/,
    });

    this.hamburgerButton = page.getByRole("button", {
      name: /toggle sidebar/i,
    });
  }

  async navigate() {
    await this.page.goto("/dashboard");
    await expect(this.heading).toBeVisible({ timeout: 20_000 });
  }

  /** Navigate via sidebar link — handles hamburger on mobile */
  async navigateTo(sectionName: string) {
    if (this.isMobile) {
      await this.hamburgerButton.first().click({ timeout: 10_000 }).catch(async () => {
        await this.hamburgerButton.first().dispatchEvent("click");
      });
    }
    const sidebarLink = this.page
      .getByRole("listitem")
      .filter({ hasText: new RegExp(`^${sectionName}$`, "i") })
      .getByRole("link")
      .first();
    await expect(sidebarLink).toBeVisible({ timeout: 15_000 });
    await sidebarLink.scrollIntoViewIfNeeded();
    await sidebarLink.click({ force: true, timeout: 10_000 }).catch(async () => {
      // WebKit/mobile Safari are intermittently flaky with a standard click here.
      await sidebarLink.evaluate((el) => (el as HTMLElement).click());
    });
  }

  async verifyPageLoaded() {
    await expect(this.heading).toBeVisible();
  }

  /**
   * Assert that the Latest Clips section shows at least `minCount` clip links.
   * Fails if no clips are found.
   */
  async verifyLatestClips(minCount: number) {
    const clipLinks = this.page.locator("a[href*='/create-clips/clip/']");
    await expect(clipLinks.first()).toBeVisible({ timeout: 30_000 });
    const count = await clipLinks.count();
    expect(count).toBeGreaterThanOrEqual(minCount);
  }

}
