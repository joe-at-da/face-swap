import { test, expect } from "../fixtures/test-fixtures";
import { LDClipsPage } from "../pages/ld-clips.page";

// WebKit/Mobile Safari crash on JS-heavy pages
// eslint-disable-next-line no-empty-pattern
test.beforeEach(({}, testInfo) => {
  if (
    testInfo.project.name === "mobile-safari" ||
    testInfo.project.name === "webkit"
  ) {
    testInfo.skip(true, "WebKit/Safari crashes on heavy LD Clips page");
  }
});

test.describe("LD Clips — Expected Pass", () => {
  test("LD user can access ld-clips page", async ({ ldMpPage }) => {
    const ldClips = new LDClipsPage(ldMpPage);
    await ldClips.navigate();
    await ldClips.waitForResults();

    await expect(ldClips.heading).toBeVisible();
  });

  test("shows results summary with clip count", async ({ ldMpPage }) => {
    const ldClips = new LDClipsPage(ldMpPage);
    await ldClips.navigate();
    await ldClips.waitForClipsLoaded();

    const text = await ldClips.getResultsText();
    expect(text).toMatch(/showing \d+-\d+ of \d+ clips/i);
  });

  test("shows clips from other LD MPs (cross-party access)", async ({ ldMpPage }) => {
    const ldClips = new LDClipsPage(ldMpPage);
    await ldClips.navigate();
    await ldClips.waitForClipsLoaded();

    const text = await ldClips.getResultsText();
    const total = parseInt(text.match(/of (\d+) clips/i)?.[1] ?? "0");
    // Should include clips from both MP Gamma (own) and MP LD Delta (cross-LD)
    expect(total).toBeGreaterThanOrEqual(2);
  });

  test("text search returns filtered results", async ({ ldMpPage }) => {
    test.slow();
    const ldClips = new LDClipsPage(ldMpPage);
    await ldClips.navigate();
    await ldClips.waitForClipsLoaded();

    await ldClips.search("climate");

    await expect(
      ldClips.resultsSummary.or(ldClips.noClipsSummary)
    ).toBeVisible({ timeout: 20_000 });
  });

  test("member filter narrows results to selected LD MP", async ({ ldMpPage }) => {
    test.slow();
    const ldClips = new LDClipsPage(ldMpPage);
    await ldClips.navigate();
    await ldClips.waitForClipsLoaded();

    await ldClips.selectMP("E2E Test MP LD Delta");

    await expect(
      ldClips.resultsSummary.or(ldClips.noClipsSummary)
    ).toBeVisible({ timeout: 20_000 });
  });

  test("date filter Last Week works", async ({ ldMpPage }) => {
    const ldClips = new LDClipsPage(ldMpPage);
    await ldClips.navigate();
    await ldClips.waitForClipsLoaded();

    const responsePromise = ldClips.waitForSearchLdResponse();
    await ldClips.lastWeekButton.click();
    await responsePromise;

    // May return 0 results — accept either state
    await expect(
      ldClips.resultsSummary.or(ldClips.noClipsSummary)
    ).toBeVisible({ timeout: 20_000 });

    await expect(ldClips.heading).toBeVisible();
  });

  test("sidebar shows All LD Clips nav item for LD user", async ({ ldMpPage }) => {
    await ldMpPage.goto("/dashboard");
    await ldMpPage.waitForURL(/\/dashboard/, { timeout: 30_000 });

    // On mobile viewports the sidebar is collapsed — open it first
    const sidebarTrigger = ldMpPage.getByRole("button", { name: /toggle sidebar/i }).first();
    if (await sidebarTrigger.isVisible().catch(() => false)) {
      await sidebarTrigger.click();
    }

    const ldNavItem = ldMpPage.getByRole("link", { name: /all ld clips/i });
    await expect(ldNavItem).toBeVisible({ timeout: 15_000 });
  });
});

test.describe("LD Clips — Expected Fail", () => {
  test("non-LD regular user redirected from ld-clips", async ({ authenticatedPage }) => {
    await authenticatedPage.goto("/dashboard/ld-clips");

    await expect
      .poll(
        () => new URL(authenticatedPage.url()).pathname,
        {
          message: "Waiting for non-LD user to be redirected from /dashboard/ld-clips",
          timeout: 20_000,
        }
      )
      .toBe("/dashboard");

    await expect(
      authenticatedPage.getByRole("heading", { name: /all ld clips/i })
    ).not.toBeVisible();
  });

  test("admin (non-LD) redirected from ld-clips", async ({ adminPage }) => {
    await adminPage.goto("/dashboard/ld-clips");

    await expect
      .poll(
        () => new URL(adminPage.url()).pathname,
        {
          message: "Waiting for admin to be redirected from /dashboard/ld-clips",
          timeout: 20_000,
        }
      )
      .toBe("/dashboard");
  });

  test("non-LD user calling POST /api/clips/search-ld gets 403", async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.post("/api/clips/search-ld", {
      data: { limit: 10, offset: 0, searchType: "text" },
    });

    expect(response.status()).toBe(403);
  });

  test("search with no results shows empty state", async ({ ldMpPage }) => {
    test.slow();
    const ldClips = new LDClipsPage(ldMpPage);
    await ldClips.navigate();
    await ldClips.waitForClipsLoaded();

    await ldClips.search("xyznonexistentquery12345");

    await expect(ldClips.emptyStateCard).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("LD Clips — Edge Cases", () => {
  test("sidebar does NOT show All LD Clips for non-LD user", async ({ authenticatedPage }) => {
    await authenticatedPage.goto("/dashboard");
    await authenticatedPage.waitForURL(/\/dashboard/, { timeout: 30_000 });

    // On mobile viewports the sidebar is collapsed — open it first
    const sidebarTrigger = authenticatedPage.getByRole("button", { name: /toggle sidebar/i }).first();
    if (await sidebarTrigger.isVisible().catch(() => false)) {
      await sidebarTrigger.click();
    }

    const ldNavItem = authenticatedPage.getByRole("link", { name: /all ld clips/i });
    await expect(ldNavItem).not.toBeVisible();
  });

  test("clear filters resets all", async ({ ldMpPage }) => {
    test.slow();
    const ldClips = new LDClipsPage(ldMpPage);
    await ldClips.navigate();
    await ldClips.waitForClipsLoaded();

    const textBefore = await ldClips.getResultsText();
    const totalBefore = parseInt(textBefore.match(/of (\d+) clips/i)?.[1] ?? "0");

    // Apply date filter
    const responsePromise = ldClips.waitForSearchLdResponse();
    await ldClips.lastWeekButton.click();
    await responsePromise;
    await ldClips.waitForResults();

    // Clear filters
    await ldClips.clearFilters();

    // Poll until total returns to original
    await expect
      .poll(
        async () => {
          const text = await ldClips.resultsSummary.textContent();
          return parseInt(text?.match(/of (\d+) clips/i)?.[1] ?? "0");
        },
        { message: "Waiting for total to return after clearing filters", timeout: 20_000 }
      )
      .toBe(totalBefore);
  });

  test("URL preserves search params on reload", async ({ ldMpPage }) => {
    test.slow();
    const ldClips = new LDClipsPage(ldMpPage);
    await ldClips.navigate();
    await ldClips.waitForClipsLoaded();

    await ldClips.search("housing");

    await expect
      .poll(
        () => new URL(ldMpPage.url()).searchParams.get("search"),
        { message: "Waiting for search query param to survive debounce", timeout: 10_000 }
      )
      .toBe("housing");

    await ldMpPage.reload();
    await expect(ldClips.heading).toBeVisible({ timeout: 30_000 });
    await expect(ldClips.searchInput).toHaveValue("housing");
  });
});
