import { test, expect } from "../fixtures/test-fixtures";
import { TEST_USERS } from "../helpers/test-users";
import { getTestMpClipId } from "../helpers/test-queries";

test.describe("Clip Detail — Expected Pass", () => {
  test("loads clip detail page from seeded clip", async ({
    mpAuthenticatedPage,
    supabaseAdmin,
  }) => {
    const clipId = await getTestMpClipId(supabaseAdmin, TEST_USERS.mpCompletedUser.email);
    test.skip(!clipId, "No parliament clip found for test MP");

    await mpAuthenticatedPage.goto(
      `/dashboard/create-clips/clip/${clipId}`
    );

    // Verify we stayed on the clip detail route (not redirected to 404)
    await expect(mpAuthenticatedPage).toHaveURL(/\/clip\//, { timeout: 30_000 });

    // Verify actual clip content loaded (transcript text from seeded data)
    await expect(
      mpAuthenticatedPage.getByText(/transcript|description|E2E test clip/i).first()
    ).toBeVisible({ timeout: 20_000 });
  });

  test("Back to Speech Library navigates back", async ({
    mpAuthenticatedPage,
    supabaseAdmin,
  }) => {
    test.slow(); // Navigation under parallel load can be slow
    const clipId = await getTestMpClipId(supabaseAdmin, TEST_USERS.mpCompletedUser.email);
    test.skip(!clipId, "No parliament clip found");

    await mpAuthenticatedPage.goto(
      `/dashboard/create-clips/clip/${clipId}`,
      { timeout: 60_000 }
    );

    // Verify we're actually on the clip page (not redirected to home)
    await expect(mpAuthenticatedPage).toHaveURL(/\/clip\//, { timeout: 30_000 });

    const backLink = mpAuthenticatedPage.getByRole("link", {
      name: /back.*speech library/i,
    });
    await expect(backLink).toBeVisible({ timeout: 30_000 });
    await backLink.scrollIntoViewIfNeeded();
    await backLink.click({ force: true });

    // Wait for navigation to Speech Library page
    await mpAuthenticatedPage.waitForURL(/\/create-clips/, { timeout: 60_000 });
  });
});

test.describe("Clip Detail — Expected Fail", () => {
  test("non-existent clip ID shows 404 / not found", async ({
    mpAuthenticatedPage,
  }) => {
    await mpAuthenticatedPage.goto(
      "/dashboard/create-clips/clip/00000000-0000-0000-0000-000000000000"
    );

    // Should show 404 page
    await expect(
      mpAuthenticatedPage.getByText(/not found|page not found/i).first()
    ).toBeVisible({ timeout: 20_000 });
  });
});

test.describe("Clip Detail — Edge Cases", () => {
  test("back button returns to previous page", async ({
    mpAuthenticatedPage,
    supabaseAdmin,
  }) => {
    // Dev server compilation makes this test slow across all browsers
    test.slow();

    // Navigate to create-clips first, then to a clip detail
    await mpAuthenticatedPage.goto("/dashboard/create-clips");
    await mpAuthenticatedPage.waitForURL(/\/create-clips/, { timeout: 30_000 });

    const clipId = await getTestMpClipId(supabaseAdmin, TEST_USERS.mpCompletedUser.email);
    test.skip(!clipId, "No parliament clip found");

    await mpAuthenticatedPage.goto(
      `/dashboard/create-clips/clip/${clipId}`,
      { timeout: 120_000 } // Allow extra time for dev server compilation under load
    );

    // Wait for clip page to fully load (not just URL — wait for content to render)
    await expect(mpAuthenticatedPage).toHaveURL(/\/clip\//, { timeout: 60_000 });
    await expect(
      mpAuthenticatedPage.getByText(/transcript|description|E2E test clip/i).first()
    ).toBeVisible({ timeout: 60_000 });

    // Use browser back
    await mpAuthenticatedPage.goBack();
    await expect(mpAuthenticatedPage).toHaveURL(/\/create-clips/, {
      timeout: 30_000,
    });
  });
});
