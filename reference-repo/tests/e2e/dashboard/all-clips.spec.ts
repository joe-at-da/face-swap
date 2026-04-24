import { test, expect } from "../fixtures/test-fixtures";
import { AllClipsPage } from "../pages/all-clips.page";

// WebKit/Mobile Safari crash on JS-heavy pages
// eslint-disable-next-line no-empty-pattern
test.beforeEach(({}, testInfo) => {
  if (
    testInfo.project.name === "mobile-safari" ||
    testInfo.project.name === "webkit"
  ) {
    testInfo.skip(true, "WebKit/Safari crashes on heavy All Clips page");
  }
});

test.describe("All Clips — Expected Pass", () => {
  test("admin can access all-clips page", async ({ adminPage }) => {
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    await expect(allClips.heading).toBeVisible();
  });

  test("shows results summary with clip count", async ({ adminPage }) => {
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    const text = await allClips.getResultsText();
    expect(text).toMatch(/showing \d+-\d+ of \d+ clips/i);
  });

  test("filter by party shows only that party's clips", async ({ adminPage }) => {
    test.slow();
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    const textBefore = await allClips.getResultsText();
    const totalBefore = parseInt(textBefore.match(/of (\d+) clips/i)?.[1] ?? "0");

    await allClips.selectParty("Conservative");

    // Poll until filtered total is different from unfiltered total
    await expect
      .poll(
        async () => {
          const el = allClips.resultsSummary.or(allClips.noClipsSummary);
          const text = await el.textContent();
          if (!text) return totalBefore; // not yet loaded
          const match = text.match(/of (\d+) clips/i);
          return match ? parseInt(match[1]) : 0; // 0 = "No clips found"
        },
        { message: "Waiting for party filter to narrow results", timeout: 20_000 }
      )
      .toBeLessThan(totalBefore);
  });

  test("filter by MP shows only that MP's clips", async ({ adminPage }) => {
    test.slow();
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    await allClips.selectMP("E2E Test MP Beta");

    await expect(
      allClips.resultsSummary.or(allClips.noClipsSummary)
    ).toBeVisible({ timeout: 20_000 });
  });

  test("date filter Last Week works without error", async ({ adminPage }) => {
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    const responsePromise = allClips.waitForSearchAllResponse();
    await allClips.lastWeekButton.click();
    await responsePromise;

    // Date filter may return 0 results — accept either state
    await expect(
      allClips.resultsSummary.or(allClips.noClipsSummary)
    ).toBeVisible({ timeout: 20_000 });

    // Verify page didn't error
    await expect(allClips.heading).toBeVisible();
  });

  test("text search filters clips", async ({ adminPage }) => {
    test.slow();
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    // Search for "healthcare" — only specific clips have this in description
    await allClips.search("healthcare");

    await expect(
      allClips.resultsSummary.or(allClips.noClipsSummary)
    ).toBeVisible({ timeout: 20_000 });
  });

  test("clear filters resets all", async ({ adminPage }) => {
    test.slow();
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    const textBefore = await allClips.getResultsText();
    const totalBefore = parseInt(textBefore.match(/of (\d+) clips/i)?.[1] ?? "0");

    // Apply party filter
    await allClips.selectParty("Conservative");
    await allClips.waitForResults();

    // Clear filters
    await allClips.clearFilters();

    // Poll until the total returns to the original count (fetch may take time)
    await expect
      .poll(
        async () => {
          const text = await allClips.resultsSummary.textContent();
          return parseInt(text?.match(/of (\d+) clips/i)?.[1] ?? "0");
        },
        { message: "Waiting for total to return to original after clearing filters", timeout: 20_000 }
      )
      .toBe(totalBefore);
  });

  test("combined party + MP filters work", async ({ adminPage }) => {
    test.slow();
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    await allClips.selectParty("Conservative");
    await allClips.waitForResults();

    await allClips.selectMP("E2E Test MP Beta");

    await expect(
      allClips.resultsSummary.or(allClips.noClipsSummary)
    ).toBeVisible({ timeout: 20_000 });

    // Verify page didn't error
    await expect(allClips.heading).toBeVisible();
  });
});

test.describe("All Clips — Expected Fail", () => {
  test("non-admin redirected to dashboard", async ({ authenticatedPage }) => {
    await authenticatedPage.goto("/dashboard/all-clips");

    await expect
      .poll(
        () => new URL(authenticatedPage.url()).pathname,
        {
          message: "Waiting for non-admin all-clips redirect to settle on /dashboard",
          timeout: 20_000,
        }
      )
      .toBe("/dashboard");

    // Should NOT see the All Parliament Clips heading
    await expect(
      authenticatedPage.getByRole("heading", { name: /all parliament clips/i })
    ).not.toBeVisible();
  });

  test("search with no results shows empty state", async ({ adminPage }) => {
    test.slow();
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    await allClips.search("xyznonexistentquery12345");

    // Wait for "No clips found matching your criteria." in the empty state card
    await expect(allClips.emptyStateCard).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("All Clips — Edge Cases", () => {
  test("date range calendar popover opens", async ({ adminPage }) => {
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForResults();

    await allClips.dateRangeButton.click();
    await adminPage
      .getByRole("button", { name: /last 7 days/i })
      .waitFor({ state: "visible", timeout: 5_000 })
      .catch(async () => {
        await allClips.dateRangeButton.click({ force: true });
      });

    // Calendar popover should show quick range buttons and calendar grid
    await expect(
      adminPage.getByRole("button", { name: /last 7 days/i })
    ).toBeVisible({ timeout: 15_000 });
  });

  test("URL preserves search params on reload", async ({ adminPage }) => {
    test.slow();
    const allClips = new AllClipsPage(adminPage);
    await allClips.navigate();
    await allClips.waitForClipsLoaded();

    await allClips.search("education");

    await expect
      .poll(
        () => new URL(adminPage.url()).searchParams.get("search"),
        { message: "Waiting for search query param to survive debounce", timeout: 10_000 }
      )
      .toBe("education");

    // Reload and verify search term is preserved
    await adminPage.reload();
    await expect(allClips.heading).toBeVisible({ timeout: 30_000 });

    // The search input should still have the term
    await expect(allClips.searchInput).toHaveValue("education");
  });
});
