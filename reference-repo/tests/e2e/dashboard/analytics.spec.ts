import { expect } from "@playwright/test";
import { test } from "../fixtures/test-fixtures";
import type { TestSupabaseAdmin } from "../helpers/supabase-admin";
import {
  TEST_USERS,
  getWorkerEmail,
} from "../helpers/test-users";

async function setPostizCredentialsForEmail(
  supabaseAdmin: TestSupabaseAdmin,
  email: string,
  credentials: {
    postiz_email: string | null;
    postiz_password: string | null;
  }
) {
  const { error } = await supabaseAdmin
    .from("user_roles")
    .update(credentials)
    .eq("email", email);

  if (error) {
    throw new Error(`Failed to update Postiz credentials for ${email}: ${error.message}`);
  }
}

const isCI = !!process.env.CI;

test.describe("dashboard analytics -- Expected Pass", () => {
  test.afterEach(async ({ supabaseAdmin }, testInfo) => {
    const mpEmail = getWorkerEmail(
      TEST_USERS.mpCompletedUser.email,
      testInfo.parallelIndex
    );
    await setPostizCredentialsForEmail(supabaseAdmin, mpEmail, {
      postiz_email: null,
      postiz_password: null,
    });
  });

  test("eligible user sees the default all-channels overview", async ({
    mpAuthenticatedPage,
    supabaseAdmin,
  }, testInfo) => {
    test.skip(isCI, "Postiz fixture tests require local dev environment");

    const mpEmail = getWorkerEmail(
      TEST_USERS.mpCompletedUser.email,
      testInfo.parallelIndex
    );

    await setPostizCredentialsForEmail(supabaseAdmin, mpEmail, {
      postiz_email: "fixture:happy",
      postiz_password: "fixture-password",
    });

    await mpAuthenticatedPage.goto("/dashboard");
    await expect(
      mpAuthenticatedPage.getByRole("link", { name: /view analytics/i })
    ).toBeVisible();

    await mpAuthenticatedPage.goto("/dashboard/analytics");

    await expect(mpAuthenticatedPage).toHaveURL(/\/dashboard\/analytics\?date=7$/);
    await expect(
      mpAuthenticatedPage.getByRole("heading", { name: /social analytics/i })
    ).toBeVisible();
    await expect(
      mpAuthenticatedPage.getByRole("heading", { name: /all channels/i })
    ).toBeVisible();
    await expect(mpAuthenticatedPage.getByText("Impression")).toBeVisible();
    await expect(mpAuthenticatedPage.getByText("Like")).toBeVisible();

    // Verify at least one formatted metric total is rendered
    await expect(
      mpAuthenticatedPage.getByText(/channels? in this rollup/)
    ).toBeVisible();
    await expect(
      mpAuthenticatedPage.locator("[class*='text-4xl']").first()
    ).not.toHaveText("");

    // Verify channel picker lists expected channels
    await mpAuthenticatedPage.getByRole("combobox").click();
    await expect(
      mpAuthenticatedPage.getByText("MP AI Facebook · Facebook")
    ).toBeVisible();
    await expect(
      mpAuthenticatedPage.getByText("MP AI Campaign Page · Facebook")
    ).toBeVisible();
  });

  test("eligible user sees a no-postiz-account empty state", async ({
    mpAuthenticatedPage,
    supabaseAdmin,
  }, testInfo) => {
    const mpEmail = getWorkerEmail(
      TEST_USERS.mpCompletedUser.email,
      testInfo.parallelIndex
    );

    await setPostizCredentialsForEmail(supabaseAdmin, mpEmail, {
      postiz_email: null,
      postiz_password: null,
    });

    await mpAuthenticatedPage.goto("/dashboard/analytics?date=7");

    await expect(
      mpAuthenticatedPage.getByText("Postiz isn't configured for this account")
    ).toBeVisible();
  });

  test("eligible user sees a no-supported-channels empty state", async ({
    mpAuthenticatedPage,
    supabaseAdmin,
  }, testInfo) => {
    test.skip(isCI, "Postiz fixture tests require local dev environment");

    const mpEmail = getWorkerEmail(
      TEST_USERS.mpCompletedUser.email,
      testInfo.parallelIndex
    );

    await setPostizCredentialsForEmail(supabaseAdmin, mpEmail, {
      postiz_email: "fixture:no-supported-channels",
      postiz_password: "fixture-password",
    });

    await mpAuthenticatedPage.goto("/dashboard/analytics?date=7");

    await expect(
      mpAuthenticatedPage.getByText("No supported analytics channels found")
    ).toBeVisible();
  });
});

test.describe("dashboard analytics -- Expected Fail", () => {
  test("ineligible user is redirected away and does not see the analytics quick action", async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto("/dashboard");
    await expect(
      authenticatedPage.getByRole("link", { name: /view analytics/i })
    ).toHaveCount(0);

    await authenticatedPage.goto("/dashboard/analytics?date=7");
    await expect(authenticatedPage).toHaveURL(/\/dashboard$/, { timeout: 10_000 });
  });
});

test.describe("dashboard analytics -- Edge Cases", () => {
  // Future: date range switching, single-channel selection, partial failures
});
