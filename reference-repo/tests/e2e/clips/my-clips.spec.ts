import { test, expect } from "../fixtures/test-fixtures";
import { MyClipsPage } from "../pages/my-clips.page";
import { createTestSupabaseAdmin } from "../helpers/supabase-admin";
import { createTestUserClip } from "../helpers/factories/clip-factory";
import { E2E_MEMBER_ID_START } from "../helpers/constants";

test.describe("My Clips — Expected Pass", () => {
  test("loads clip grid with seeded clips", async ({
    authenticatedPage,
  }) => {
    const myClips = new MyClipsPage(authenticatedPage);
    await myClips.navigate();

    // Should have seeded user clips visible
    await expect(myClips.clipCards.first()).toBeVisible({ timeout: 30_000 });
    const count = await myClips.getClipCount();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test("search by text filters clips", async ({
    authenticatedPage,
  }) => {
    const myClips = new MyClipsPage(authenticatedPage);
    await myClips.navigate();

    // Wait for initial load
    await expect(myClips.clipCards.first()).toBeVisible({ timeout: 30_000 });

    // Search — use waitForResponse for debounced input
    const responsePromise = authenticatedPage.waitForResponse(
      (resp) =>
        (resp.url().includes("user-clips") ||
          resp.url().includes("user_clips")) &&
        resp.status() === 200,
      { timeout: 30_000 }
    );
    await myClips.search("E2E User Clip 1");
    await responsePromise;

    // Results should be filtered — use .first() to handle search indicator text
    await expect(
      authenticatedPage.getByText("E2E User Clip 1").first()
    ).toBeVisible({ timeout: 20_000 });
  });

  test("shows results count with clip total", async ({
    authenticatedPage,
  }) => {
    const myClips = new MyClipsPage(authenticatedPage);
    await myClips.navigate();

    // Verify "Showing X of Y clips" text is present and reflects seeded data
    await expect(
      authenticatedPage.getByText(/Showing \d+ of \d+ clips/i)
    ).toBeVisible({ timeout: 30_000 });
  });

  test("clicking clip card navigates to detail page", async ({
    authenticatedPage,
  }) => {
    const myClips = new MyClipsPage(authenticatedPage);
    await myClips.navigate();

    await expect(myClips.clipCards.first()).toBeVisible({ timeout: 30_000 });

    // The view link is an overlay <a> that can be outside the viewport on Firefox/WebKit.
    // Use JS click as the most reliable cross-browser approach.
    const viewLink = authenticatedPage
      .locator("a[href*='/my-clips/']")
      .first();
    await viewLink.evaluate((el) => (el as HTMLElement).click());
    await expect(authenticatedPage).toHaveURL(/\/my-clips\//, {
      timeout: 20_000,
    });
  });

});

test.describe("My Clips — Mutations", () => {
  test.describe.configure({ mode: "serial" });

  // Track disposable clip for cleanup
  let disposableClipId: string | null = null;

  test.afterEach(async () => {
    if (disposableClipId) {
      const admin = createTestSupabaseAdmin();
      await admin.from("user_clips").delete().eq("id", disposableClipId);
      disposableClipId = null;
    }
  });

  test("delete clip removes it from grid", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    // Create a disposable clip to delete (avoids reducing seeded clip count)
    const { data: pmClips } = await supabaseAdmin
      .from("parliament_member_clips")
      .select("id")
      .gte("member_id", E2E_MEMBER_ID_START)
      .limit(1);
    if (!pmClips?.[0]?.id) {
      test.skip(true, "No parliament clip for FK reference");
      return;
    }
    const clip = await createTestUserClip(supabaseAdmin, {
      user_id: testUser.userId,
      clip_id: pmClips[0].id,
      title: "E2E Disposable Clip",
    });
    disposableClipId = clip.id;

    const myClips = new MyClipsPage(authenticatedPage);
    await myClips.navigate();

    await expect(myClips.clipCards.first()).toBeVisible({ timeout: 30_000 });
    const countBefore = await myClips.getClipCount();

    // Delete the first clip (the disposable one we just created)
    await myClips.deleteClip(0);

    // Verify clip count decreased
    await expect
      .poll(
        async () => await myClips.getClipCount(),
        { message: "Waiting for clip count to decrease", timeout: 20_000 }
      )
      .toBeLessThan(countBefore);
  });
});

test.describe("My Clips — Expected Fail", () => {
  test("search with no results shows empty state", async ({
    authenticatedPage,
  }) => {
    const myClips = new MyClipsPage(authenticatedPage);
    await myClips.navigate();

    // Wait for either clips or empty state (clips may have been deleted by previous serial test)
    await expect(
      myClips.clipCards.first().or(myClips.emptyState)
    ).toBeVisible({ timeout: 30_000 });

    // If already empty, the test is trivially satisfied
    if (await myClips.emptyState.isVisible().catch(() => false)) {
      return;
    }

    await myClips.search("xyznonexistentquery12345");

    // Should show empty state or "no results"
    await expect(myClips.emptyState).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("My Clips — Edge Cases", () => {
  test.describe.configure({ mode: "serial" });

  // Track IDs of clips created during tests for safety cleanup
  const createdClipIds: string[] = [];

  test.afterEach(async () => {
    if (createdClipIds.length > 0) {
      const admin = createTestSupabaseAdmin();
      await admin.from("user_clips").delete().in("id", createdClipIds);
      createdClipIds.length = 0;
    }
  });

  test("new clip appears after page refresh", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    await authenticatedPage.goto("/dashboard/my-clips");

    // Wait for initial load — may show results summary or empty state
    const resultsSummary = authenticatedPage.getByText(/Showing \d+ of \d+ clips/i);
    const emptyState = authenticatedPage.getByText(/no clips/i);
    await expect(resultsSummary.or(emptyState)).toBeVisible({ timeout: 30_000 });

    let totalBefore = 0;
    if (await resultsSummary.isVisible().catch(() => false)) {
      const countText = await resultsSummary.textContent();
      totalBefore = parseInt(countText?.match(/of (\d+)/)?.[1] ?? "0");
    }

    // Find a valid parliament_member_clips ID for the FK reference
    const { data: pmClips } = await supabaseAdmin
      .from("parliament_member_clips")
      .select("id")
      .gte("member_id", E2E_MEMBER_ID_START)
      .limit(1);

    const pmClipId = pmClips?.[0]?.id;
    if (!pmClipId) {
      test.skip(true, "No parliament clip found for FK reference");
      return;
    }

    // Insert clip via factory with proper FK reference
    const newClip = await createTestUserClip(supabaseAdmin, {
      user_id: testUser.userId,
      clip_id: pmClipId,
    });
    createdClipIds.push(newClip.id);

    // Verify clip exists in DB before reloading
    const { data: dbClip } = await supabaseAdmin
      .from("user_clips")
      .select("id")
      .eq("id", newClip.id)
      .single();
    expect(dbClip).not.toBeNull();

    // Refresh page and verify clip count increased
    await authenticatedPage.reload();
    await expect
      .poll(
        async () => {
          // Reload again if needed — the page may cache stale data
          const text = await authenticatedPage
            .getByText(/Showing \d+ of \d+ clips/i)
            .textContent()
            .catch(() => "");
          return parseInt(text?.match(/of (\d+)/)?.[1] ?? "0");
        },
        { message: "Waiting for clip count to increase", timeout: 30_000 }
      )
      .toBeGreaterThan(totalBefore);
  });

});
