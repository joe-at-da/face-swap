import { expect } from "@playwright/test";
import { test } from "../fixtures/test-fixtures";
import { getTestUserClipId } from "../helpers/test-queries";

test.describe("Public Clip Reporting — Expected Pass", () => {
  let createdReportIds: string[] = [];

  test.afterEach(async ({ supabaseAdmin }) => {
    if (createdReportIds.length > 0) {
      await supabaseAdmin
        .from("public_clip_reports")
        .delete()
        .in("id", createdReportIds);
    }

    createdReportIds = [];
  });

  test("anonymous visitor can report a public clip and sees success toast", async ({
    page,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found for test user");
    const resolvedClipId = clipId!;

    const details = `Anonymous e2e report ${Date.now()}`;

    await page.goto(`/clips/${resolvedClipId}`);
    await page.getByRole("button", { name: "Report clip" }).click();
    await page
      .getByRole("radio", { name: "Wrong clip or speaker" })
      .click();
    await page.getByLabel("Additional details").fill(details);
    await page.getByRole("button", { name: "Submit report" }).click();

    // Toast should appear
    await expect(
      page.getByText("This clip has been reported for review."),
    ).toBeVisible({ timeout: 10_000 });

    // Verify DB state
    await expect
      .poll(
        async () => {
          const { data } = await supabaseAdmin
            .from("public_clip_reports")
            .select(
              "id, user_clip_id, reporter_user_id, reason, details, review_status, notification_status",
            )
            .eq("user_clip_id", resolvedClipId)
            .eq("details", details)
            .maybeSingle();

          return data;
        },
        {
          timeout: 15_000,
          message: "Waiting for anonymous report to persist",
        },
      )
      .toBeTruthy();

    const { data: insertedReport } = await supabaseAdmin
      .from("public_clip_reports")
      .select(
        "id, user_clip_id, reporter_user_id, reason, details, review_status, notification_status",
      )
      .eq("user_clip_id", resolvedClipId)
      .eq("details", details)
      .maybeSingle();

    expect(insertedReport).toMatchObject({
      user_clip_id: resolvedClipId,
      reporter_user_id: null,
      reason: "wrong_clip",
      details,
      review_status: "pending",
    });
    expect(["pending", "sent", "failed"]).toContain(
      insertedReport!.notification_status,
    );

    createdReportIds.push(insertedReport!.id);
  });

  test("signed-in user report stores reporter_user_id", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found for test user");
    const resolvedClipId = clipId!;

    const details = `Authenticated e2e report ${Date.now()}`;

    await authenticatedPage.goto(`/clips/${resolvedClipId}`);
    await authenticatedPage
      .getByRole("button", { name: "Report clip" })
      .click();
    await authenticatedPage
      .getByRole("radio", { name: "Misleading or inaccurate" })
      .click();
    await authenticatedPage
      .getByLabel("Additional details")
      .fill(details);
    await authenticatedPage
      .getByRole("button", { name: "Submit report" })
      .click();

    await expect
      .poll(
        async () => {
          const { data } = await supabaseAdmin
            .from("public_clip_reports")
            .select("id, reporter_user_id, reason, details")
            .eq("user_clip_id", resolvedClipId)
            .eq("details", details)
            .maybeSingle();

          return data;
        },
        {
          timeout: 15_000,
          message: "Waiting for authenticated report to persist",
        },
      )
      .toBeTruthy();

    const { data: insertedReport } = await supabaseAdmin
      .from("public_clip_reports")
      .select("id, reporter_user_id, reason, details")
      .eq("user_clip_id", resolvedClipId)
      .eq("details", details)
      .maybeSingle();

    expect(insertedReport).toMatchObject({
      reporter_user_id: testUser.userId,
      reason: "misleading",
      details,
    });

    createdReportIds.push(insertedReport!.id);
  });

  test("dialog opens and closes via cancel", async ({
    page,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found for test user");

    await page.goto(`/clips/${clipId}`);
    await page.getByRole("button", { name: "Report clip" }).click();

    // Dialog should be visible
    await expect(
      page.getByRole("heading", { name: "Report This Clip" }),
    ).toBeVisible();

    // Click cancel
    await page.getByRole("button", { name: "Cancel" }).click();

    // Dialog should close
    await expect(
      page.getByRole("heading", { name: "Report This Clip" }),
    ).not.toBeVisible();
  });

  test("character counter updates as user types details", async ({
    page,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found for test user");

    await page.goto(`/clips/${clipId}`);
    await page.getByRole("button", { name: "Report clip" }).click();

    // Counter starts at 0
    await expect(page.getByText("0/2000")).toBeVisible();

    // Type some text and verify counter updates
    await page.getByLabel("Additional details").fill("Hello world");
    await expect(page.getByText("11/2000")).toBeVisible();
  });
});

test.describe("Public Clip Reporting — Expected Fail", () => {
  test("submit button is disabled when no reason is selected", async ({
    page,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found for test user");

    await page.goto(`/clips/${clipId}`);
    await page.getByRole("button", { name: "Report clip" }).click();

    // Submit should be disabled initially
    const submitButton = page.getByRole("button", { name: "Submit report" });
    await expect(submitButton).toBeDisabled();

    // Filling details without reason should keep it disabled
    await page
      .getByLabel("Additional details")
      .fill("Some details without reason");
    await expect(submitButton).toBeDisabled();

    // Selecting a reason should enable it
    await page.getByRole("radio", { name: "Other" }).click();
    await expect(submitButton).toBeEnabled();
  });

  test("reporting a deleted clip shows error toast", async ({
    page,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found for test user");
    const resolvedClipId = clipId!;

    // Navigate first while clip exists
    await page.goto(`/clips/${resolvedClipId}`);

    // Soft-delete the clip
    await supabaseAdmin
      .from("user_clips")
      .update({ is_deleted: true })
      .eq("id", resolvedClipId);

    try {
      await page.getByRole("button", { name: "Report clip" }).click();
      await page.getByRole("radio", { name: "Other" }).click();
      await page.getByRole("button", { name: "Submit report" }).click();

      // Should see error toast
      await expect(
        page.getByText("This clip is no longer available."),
      ).toBeVisible({ timeout: 10_000 });
    } finally {
      // Always restore the clip
      await supabaseAdmin
        .from("user_clips")
        .update({ is_deleted: false })
        .eq("id", resolvedClipId);
    }
  });
});

test.describe("Public Clip Reporting — Edge Cases", () => {
  let createdReportIds: string[] = [];

  test.afterEach(async ({ supabaseAdmin }) => {
    if (createdReportIds.length > 0) {
      await supabaseAdmin
        .from("public_clip_reports")
        .delete()
        .in("id", createdReportIds);
    }

    createdReportIds = [];
  });

  test("duplicate anonymous reports collapse into one open report", async ({
    page,
    supabaseAdmin,
    testUser,
  }) => {
    const clipId = await getTestUserClipId(supabaseAdmin, testUser.userId);
    test.skip(!clipId, "No completed clip found for test user");
    const resolvedClipId = clipId!;

    const details = `Duplicate e2e report ${Date.now()}`;
    const reason = "copyright_or_privacy";
    const { count: baselineCount } = await supabaseAdmin
      .from("public_clip_reports")
      .select("id", { count: "exact", head: true })
      .eq("user_clip_id", resolvedClipId)
      .eq("reason", reason);

    await page.goto(`/clips/${resolvedClipId}`);
    await page.getByRole("button", { name: "Report clip" }).click();
    await page
      .getByRole("radio", { name: "Copyright or privacy concern" })
      .click();
    await page.getByLabel("Additional details").fill(details);
    await page.getByRole("button", { name: "Submit report" }).click();

    await expect
      .poll(
        async () => {
          const { count } = await supabaseAdmin
            .from("public_clip_reports")
            .select("id", { count: "exact", head: true })
            .eq("user_clip_id", resolvedClipId)
            .eq("reason", reason);

          return count ?? 0;
        },
        {
          timeout: 15_000,
          message: "Waiting for first duplicate-test report",
        },
      )
      .toBe((baselineCount ?? 0) + 1);

    const { data: firstReport } = await supabaseAdmin
      .from("public_clip_reports")
      .select("id")
      .eq("user_clip_id", resolvedClipId)
      .eq("reason", reason)
      .eq("details", details)
      .maybeSingle();

    expect(firstReport?.id).toBeTruthy();
    createdReportIds.push(firstReport!.id);

    // Submit duplicate with same reason
    await page.getByRole("button", { name: "Report clip" }).click();
    await page
      .getByRole("radio", { name: "Copyright or privacy concern" })
      .click();
    await page
      .getByLabel("Additional details")
      .fill(`${details} second try`);
    await page.getByRole("button", { name: "Submit report" }).click();

    // Should show duplicate info toast
    await expect(
      page.getByText("You already reported this clip for that reason."),
    ).toBeVisible({ timeout: 10_000 });

    // Count should not have increased
    const { count: finalCount } = await supabaseAdmin
      .from("public_clip_reports")
      .select("id", { count: "exact", head: true })
      .eq("user_clip_id", resolvedClipId)
      .eq("reason", reason);

    expect(finalCount ?? 0).toBe((baselineCount ?? 0) + 1);
  });
});
