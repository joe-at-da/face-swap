import { test, expect } from "../fixtures/test-fixtures";
import { CreateClipsPage } from "../pages/create-clips.page";

// WebKit/Mobile Safari crash on the JS-heavy Speech Library page
// eslint-disable-next-line no-empty-pattern
test.beforeEach(({}, testInfo) => {
  if (
    testInfo.project.name === "mobile-safari" ||
    testInfo.project.name === "webkit"
  ) {
    testInfo.skip(true, "WebKit/Safari crashes on heavy Speech Library page");
  }
});

test.describe("Create Clips — Expected Pass", () => {
  test("loads Speech Library with MP info", async ({
    mpAuthenticatedPage,
  }) => {
    const createClips = new CreateClipsPage(mpAuthenticatedPage);
    await createClips.navigate();

    // Verify an MP name is shown (h2 below h1)
    await expect(createClips.mpName).toBeVisible();
  });

  test("shows clip grid with parliament_member_clips", async ({
    mpAuthenticatedPage,
  }) => {
    const createClips = new CreateClipsPage(mpAuthenticatedPage);
    await createClips.navigate();

    // Should have clips visible (result summary confirms)
    await expect(createClips.resultsSummary).toBeVisible({ timeout: 20_000 });
    const count = await createClips.getClipCount();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test("search filters clips by text", async ({
    mpAuthenticatedPage,
  }) => {
    test.slow();
    const createClips = new CreateClipsPage(mpAuthenticatedPage);
    await createClips.navigate();

    await expect(createClips.resultsSummary).toBeVisible({ timeout: 20_000 });

    const countBefore = await createClips.getClipCount();

    // Search for unique clip description — only clip 1 has "healthcare"
    await createClips.search("healthcare");

    // Results should update — either fewer than total or summary changes
    await expect
      .poll(
        async () => createClips.getClipCount(),
        { message: "Waiting for search to filter results", timeout: 20_000 }
      )
      .toBeLessThan(countBefore);
  });

  test("date range filter narrows results", async ({
    mpAuthenticatedPage,
  }) => {
    const createClips = new CreateClipsPage(mpAuthenticatedPage);
    await createClips.navigate();

    await expect(createClips.resultsSummary).toBeVisible({ timeout: 20_000 });

    // Click "Last Week" date filter — assert it exists rather than silently skipping
    await expect(createClips.lastWeekButton).toBeVisible({ timeout: 20_000 });
    await createClips.lastWeekButton.click();

    // Date filter may legitimately return 0 results — accept either state
    await expect(
      createClips.resultsSummary.or(createClips.emptyState)
    ).toBeVisible({ timeout: 20_000 });

    // Verify page didn't error out
    await expect(createClips.heading).toBeVisible();
  });
});

test.describe("Create Clips — Expected Fail", () => {
  test("search with no results shows empty state", async ({
    mpAuthenticatedPage,
  }) => {
    const createClips = new CreateClipsPage(mpAuthenticatedPage);
    await createClips.navigate();

    await expect(createClips.resultsSummary).toBeVisible({ timeout: 20_000 });

    await createClips.search("xyznonexistentquery12345");

    // Wait for empty state or zero-results indicator to appear
    // Use .first() — both "No clips found" and "Showing 0" may match simultaneously
    await expect(
      createClips.emptyState.or(mpAuthenticatedPage.getByText(/showing 0|no match/i)).first()
    ).toBeVisible({ timeout: 60_000 });
  });
});

test.describe("Create Clips — Edge Cases", () => {
  test("user with no followed MP sees appropriate state", async ({
    authenticatedPage,
  }) => {
    // Regular user may not have an MP — visiting create-clips should handle gracefully
    await authenticatedPage.goto("/dashboard/create-clips");

    // Should show either the speech library or redirect
    await expect(
      authenticatedPage.getByRole("heading", { level: 1 })
    ).toBeVisible({ timeout: 20_000 });
  });
});
