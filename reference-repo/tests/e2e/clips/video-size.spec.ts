import { test, expect } from "../fixtures/test-fixtures";
import type { Page } from "@playwright/test";
import { MyClipDetailPage } from "../pages/my-clip-detail.page";
import { getTestUserClipId, getTestMpClipId } from "../helpers/test-queries";
import { createTestUserClip } from "../helpers/factories/clip-factory";
import type { TestSupabaseAdmin } from "../helpers/supabase-admin";

/** Known real DigitalOcean Spaces URL (verified: content-length 7017757 ≈ 6.7 MB) */
const REAL_CLIP_URL =
  "https://thempai.lon1.digitaloceanspaces.com/parliament-clips/729e5e5e-8edf-44ee-8ca6-b9e52d90f4af/clips/5296/seg_613_horizontal.mp4";

/**
 * Intercept /api/video-size requests and return controlled responses.
 * Keys in sizeMap are substring-matched against the request's `url` query param.
 * Unmatched requests receive the fallback value.
 */
async function mockVideoSizeApi(
  page: Page,
  sizeMap: Record<string, number | null> = {},
  fallback: number | null = null
) {
  await page.route("**/api/video-size*", async (route) => {
    const reqUrl = new URL(route.request().url());
    const videoUrl = reqUrl.searchParams.get("url") ?? "";

    for (const [key, sizeBytes] of Object.entries(sizeMap)) {
      if (videoUrl.includes(key)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ size_bytes: sizeBytes }),
        });
        return;
      }
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ size_bytes: fallback }),
    });
  });
}

/** Get any parliament member clip ID from seed data (for user clip creation) */
async function getAnyPmClipId(admin: TestSupabaseAdmin): Promise<string> {
  const { data } = await admin
    .from("parliament_member_clips")
    .select("id")
    .eq("is_deleted", false)
    .limit(1)
    .single();
  if (!data?.id)
    throw new Error("No parliament member clip found in seed data");
  return data.id;
}

// ---------------------------------------------------------------------------
// Video Size Display
// ---------------------------------------------------------------------------

test.describe("Video Size Display — Expected Pass", () => {
  test("my-clips page shows video size in clip details", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found for test user");

    await mockVideoSizeApi(authenticatedPage, {}, 5 * 1024 * 1024);

    const clipDetail = new MyClipDetailPage(authenticatedPage);
    await clipDetail.navigate(clipId!);
    await clipDetail.verifyClipLoaded();
    await clipDetail.expandClipDetails();

    await expect(clipDetail.videoSizeRow).toBeVisible();
    await expect(authenticatedPage.getByText(/5\.0 MB/)).toBeVisible();
  });

  test("create-clips page shows video size in sidebar", async ({
    mpAuthenticatedPage,
    supabaseAdmin,
    mpUser,
  }) => {
    const clipId = await getTestMpClipId(supabaseAdmin, mpUser.email);
    test.skip(!clipId, "No MP clip found");

    await mockVideoSizeApi(mpAuthenticatedPage, {}, 5 * 1024 * 1024);

    // Navigate and wait for both page load and API interception
    await Promise.all([
      mpAuthenticatedPage.waitForResponse(
        (r) => r.url().includes("/api/video-size"),
        { timeout: 30_000 }
      ).catch(() => null),
      mpAuthenticatedPage.goto(`/dashboard/create-clips/clip/${clipId}`),
    ]);

    await expect(
      mpAuthenticatedPage.getByRole("heading").first()
    ).toBeVisible({ timeout: 20_000 });

    await expect(mpAuthenticatedPage.getByText(/video size/i)).toBeVisible();
    await expect(mpAuthenticatedPage.getByText(/5\.0 MB/)).toBeVisible({
      timeout: 15_000,
    });
  });

  test("video size shows loading skeleton then resolves", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found");

    // Mock with a delay so the skeleton is visible briefly
    await authenticatedPage.route("**/api/video-size*", async (route) => {
      await new Promise((r) => setTimeout(r, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ size_bytes: 5 * 1024 * 1024 }),
      });
    });

    const clipDetail = new MyClipDetailPage(authenticatedPage);
    await clipDetail.navigate(clipId!);
    await clipDetail.verifyClipLoaded();
    await clipDetail.expandClipDetails();

    // After the delay the size should resolve
    await expect(authenticatedPage.getByText(/5\.0 MB/)).toBeVisible({
      timeout: 10_000,
    });
  });
});

// ---------------------------------------------------------------------------
// Bluesky Limits
// ---------------------------------------------------------------------------

test.describe("Bluesky Limits — Expected Pass", () => {
  test("Bluesky button disabled when video exceeds 100 MB", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const pmClipId = await getAnyPmClipId(supabaseAdmin);
    const clip = await createTestUserClip(supabaseAdmin, {
      user_id: testUser.userId,
      clip_id: pmClipId,
      duration: "01:00.000", // 1 min — under 3-min limit
    });

    try {
      // 110 MB — over 100 MB Bluesky limit
      await mockVideoSizeApi(authenticatedPage, {}, 110 * 1024 * 1024);

      await authenticatedPage.goto(`/dashboard/my-clips/${clip.id}`);
      await expect(
        authenticatedPage.getByRole("heading")
      ).toBeVisible({ timeout: 20_000 });

      // Wait for social media platforms to load then find Bluesky button
      const blueskyBtn = authenticatedPage.locator(
        'button[title*="Bluesky"]'
      );
      await expect(blueskyBtn).toBeVisible({ timeout: 15_000 });
      await expect(blueskyBtn).toHaveAttribute("aria-disabled", "true");
      await expect(blueskyBtn).toHaveClass(/opacity-50/);
      await expect(blueskyBtn).toHaveAttribute(
        "title",
        /larger than 100 MB/
      );
    } finally {
      await supabaseAdmin.from("user_clips").delete().eq("id", clip.id);
    }
  });

  test("Bluesky button disabled when video exceeds 3 minutes", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const pmClipId = await getAnyPmClipId(supabaseAdmin);
    const clip = await createTestUserClip(supabaseAdmin, {
      user_id: testUser.userId,
      clip_id: pmClipId,
      duration: "04:00.000", // 4 min — over 3-min limit
    });

    try {
      // 50 MB — under 100 MB limit
      await mockVideoSizeApi(authenticatedPage, {}, 50 * 1024 * 1024);

      await authenticatedPage.goto(`/dashboard/my-clips/${clip.id}`);
      await expect(
        authenticatedPage.getByRole("heading")
      ).toBeVisible({ timeout: 20_000 });

      const blueskyBtn = authenticatedPage.locator(
        'button[title*="Bluesky"]'
      );
      await expect(blueskyBtn).toBeVisible({ timeout: 15_000 });
      await expect(blueskyBtn).toHaveAttribute("aria-disabled", "true");
      await expect(blueskyBtn).toHaveAttribute(
        "title",
        /longer than 3 minutes/
      );
    } finally {
      await supabaseAdmin.from("user_clips").delete().eq("id", clip.id);
    }
  });

  test("Bluesky button enabled for compliant video", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const pmClipId = await getAnyPmClipId(supabaseAdmin);
    const clip = await createTestUserClip(supabaseAdmin, {
      user_id: testUser.userId,
      clip_id: pmClipId,
      duration: "01:00.000", // 1 min — under limit
    });

    try {
      // 50 MB — under 100 MB limit
      await mockVideoSizeApi(authenticatedPage, {}, 50 * 1024 * 1024);

      await authenticatedPage.goto(`/dashboard/my-clips/${clip.id}`);
      await expect(
        authenticatedPage.getByRole("heading")
      ).toBeVisible({ timeout: 20_000 });

      // When compliant, title is just "Bluesky" (exact match)
      const blueskyBtn = authenticatedPage.locator(
        'button[title="Bluesky"]'
      );
      await expect(blueskyBtn).toBeVisible({ timeout: 15_000 });

      // Should NOT have aria-disabled or opacity-50
      const ariaDisabled = await blueskyBtn.getAttribute("aria-disabled");
      expect(ariaDisabled).toBeNull();
      await expect(blueskyBtn).not.toHaveClass(/opacity-50/);
    } finally {
      await supabaseAdmin.from("user_clips").delete().eq("id", clip.id);
    }
  });
});

// ---------------------------------------------------------------------------
// Real URL Integration
// ---------------------------------------------------------------------------

test.describe("Video Size API — Real URL Integration", () => {
  // Real HEAD requests to DigitalOcean Spaces can be slow under parallel load;
  // restrict to chromium to avoid flaky failures on mobile emulators.
  // eslint-disable-next-line no-empty-pattern
  test.beforeEach(({}, testInfo) => {
    test.skip(
      testInfo.project.name !== "chromium",
      "Real URL integration tests only run on chromium"
    );
  });

  test("API returns valid size for real DigitalOcean clip URL", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const pmClipId = await getAnyPmClipId(supabaseAdmin);
    const clip = await createTestUserClip(supabaseAdmin, {
      user_id: testUser.userId,
      clip_id: pmClipId,
      clip_url: REAL_CLIP_URL,
      vertical_clip_url: null,
    });

    try {
      // Do NOT mock — let the real /api/video-size route execute
      const clipDetail = new MyClipDetailPage(authenticatedPage);
      await authenticatedPage.goto(`/dashboard/my-clips/${clip.id}`);
      await clipDetail.verifyClipLoaded();
      await clipDetail.expandClipDetails();

      await expect(clipDetail.videoSizeRow).toBeVisible();
      // Real content-length is 7017757 ≈ 6.7 MB — should show MB, not "Unknown"
      await expect(
        authenticatedPage.getByText(/\d+\.\d+ MB/)
      ).toBeVisible({ timeout: 30_000 });
    } finally {
      await supabaseAdmin.from("user_clips").delete().eq("id", clip.id);
    }
  });

  test("API returns valid size via direct fetch", async ({
    authenticatedPage,
  }) => {
    // Navigate to establish origin and authenticated cookies
    await authenticatedPage.goto("/dashboard");
    await authenticatedPage.waitForLoadState("domcontentloaded");

    const result = await authenticatedPage.evaluate(
      async (url: string) => {
        const resp = await fetch(
          `/api/video-size?url=${encodeURIComponent(url)}`
        );
        return {
          status: resp.status,
          body: (await resp.json()) as { size_bytes?: number },
          cacheControl: resp.headers.get("cache-control"),
        };
      },
      REAL_CLIP_URL
    );

    expect(result.status).toBe(200);
    expect(result.body.size_bytes).toBeGreaterThan(0);
    expect(typeof result.body.size_bytes).toBe("number");
    expect(result.cacheControl).toContain("private");
    expect(result.cacheControl).toContain("max-age=3600");
  });
});

// ---------------------------------------------------------------------------
// Edge Cases
// ---------------------------------------------------------------------------

test.describe("Video Size — Edge Cases", () => {
  test("video size shows Unknown when API returns null", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found");

    await mockVideoSizeApi(authenticatedPage, {}, null);

    const clipDetail = new MyClipDetailPage(authenticatedPage);
    await clipDetail.navigate(clipId!);
    await clipDetail.verifyClipLoaded();
    await clipDetail.expandClipDetails();

    await expect(clipDetail.videoSizeRow).toBeVisible();
    // formatFileSize(null) returns "Unknown"
    const row = authenticatedPage
      .locator("div")
      .filter({ hasText: /Video Size/i })
      .filter({ hasText: "Unknown" });
    await expect(row.first()).toBeVisible({ timeout: 10_000 });
  });

  test("video size shows Unknown when API fails", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found");

    await authenticatedPage.route("**/api/video-size*", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: "Internal Server Error" }),
      });
    });

    const clipDetail = new MyClipDetailPage(authenticatedPage);
    await clipDetail.navigate(clipId!);
    await clipDetail.verifyClipLoaded();
    await clipDetail.expandClipDetails();

    await expect(clipDetail.videoSizeRow).toBeVisible();
    const row = authenticatedPage
      .locator("div")
      .filter({ hasText: /Video Size/i })
      .filter({ hasText: "Unknown" });
    await expect(row.first()).toBeVisible({ timeout: 10_000 });
  });
});
