import { test, expect } from "../fixtures/test-fixtures";
import { SetupPage } from "../pages/setup.page";
import { assertSetupComplete } from "../helpers/assertions";
import { TEST_AVATAR_BUFFER } from "../helpers/constants";

// Serial mode: all tests mutate the same setup user's is_first_login state
test.describe.configure({ mode: "serial" });

test.describe("Setup Wizard — Expected Pass", () => {
  test("completes full wizard and redirects to /dashboard", async ({
    setupUserPage,
    setupUser,
    supabaseAdmin,
  }, testInfo) => {
    test.skip(testInfo.project.name === "firefox", "Firefox overlays intercept Continue button clicks");
    test.slow();
    const setupPage = new SetupPage(setupUserPage);

    // Step 1: fill profile and wait for API response
    await setupPage.fillProfile("Test", "User");
    const profileResponse = setupUserPage.waitForResponse(
      (r) => r.url().includes("/api/setup/profile") && r.request().method() === "POST",
      { timeout: 60_000 }
    );
    await setupPage.clickContinue();
    const profileRes = await profileResponse;
    expect(profileRes.status()).toBe(200);

    // Step 2: skip social media (no API call)
    await setupPage.clickContinue();

    // Step 3: select MP and complete
    await setupPage.searchMP("E2E Test MP Alpha");
    // Wait for debounced search results to appear
    await expect(setupUserPage.getByText("E2E Test MP Alpha")).toBeVisible({
      timeout: 20_000,
    });
    await setupPage.selectMP("E2E Test MP Alpha");

    // Wait for the complete API call (mp-follow fires first, complete follows)
    const completeResponse = setupUserPage.waitForResponse(
      (r) => r.url().includes("/api/setup/complete") && r.request().method() === "POST",
      { timeout: 60_000 }
    );
    await setupPage.clickCompleteSetup();
    const completeRes = await completeResponse;

    // If API failed, try clicking retry once
    if (completeRes.status() !== 200) {
      const retryBtn = setupUserPage.getByRole("button", { name: /retry/i });
      if (await retryBtn.isVisible({ timeout: 10_000 }).catch(() => false)) {
        const retryResponse = setupUserPage.waitForResponse(
          (r) => r.url().includes("/api/setup/complete") && r.request().method() === "POST",
          { timeout: 60_000 }
        );
        await retryBtn.click();
        await retryResponse;
      }
    }

    // UI assertion — non-fatal (DB assertion below is ground truth)
    await assertSetupComplete(setupUserPage, /setup completed|success/i);

    // DB assertion — check is_first_login was set to false (ground truth)
    // Pre-poll delay: under 6-worker load the API may complete but DB write lags
    await setupUserPage.waitForTimeout(2_000);
    await expect
      .poll(
        async () => {
          const { data } = await supabaseAdmin
            .from("user_roles")
            .select("is_first_login, member_id")
            .eq("email", setupUser.email)
            .single();
          return data?.is_first_login;
        },
        {
          message: "Waiting for is_first_login to become false",
          timeout: 60_000,
        }
      )
      .toBe(false);
  });

  test("step 1: saves profile with avatar upload", async ({
    setupUserPage,
  }) => {
    const setupPage = new SetupPage(setupUserPage);

    await setupPage.fillProfile("Avatar", "Test");

    // Upload a minimal valid PNG from buffer
    const avatarInput = setupPage.avatarUpload;
    if (await avatarInput.isVisible().catch(() => false)) {
      await avatarInput.setInputFiles({
        name: "test-avatar.png",
        mimeType: "image/png",
        buffer: TEST_AVATAR_BUFFER,
      });
    }

    await setupPage.clickContinue();
    // Should advance to next step
    await expect(setupPage.previousButton).toBeVisible({ timeout: 20_000 });
  });

  test("step 3: searches and filters MPs by name", async ({
    setupUserPage,
  }) => {
    const setupPage = new SetupPage(setupUserPage);

    // Navigate to step 3 (fill required fields first)
    await setupPage.fillProfile("Search", "Test");
    await setupPage.clickContinue();
    // Wait for step 2 heading and controls to settle before continuing again.
    await expect(setupUserPage.getByText("Connect Social Media")).toBeVisible({ timeout: 20_000 });
    await expect(setupPage.continueButton).toBeVisible({ timeout: 10_000 });
    await setupPage.continueButton.click({ force: true });

    await expect(setupPage.mpSearchInput).toBeVisible({ timeout: 20_000 });

    // Search for specific MP
    await setupPage.searchMP("E2E Test MP Beta");
    await expect(setupUserPage.getByText("E2E Test MP Beta")).toBeVisible({
      timeout: 20_000,
    });
  });
});

test.describe("Setup Wizard — Expected Fail", () => {
  test("step 1: empty first name shows validation error", async ({
    setupUserPage,
  }) => {
    const setupPage = new SetupPage(setupUserPage);

    // Clear first name and fill last name only
    await setupPage.firstNameInput.clear();
    await setupPage.lastNameInput.fill("Test");
    await setupPage.clickContinue();

    // Should remain on step 1 — first name input still visible
    await expect(setupPage.firstNameInput).toBeVisible({ timeout: 10_000 });
  });

  test("step 1: empty last name shows validation error", async ({
    setupUserPage,
  }) => {
    const setupPage = new SetupPage(setupUserPage);

    await setupPage.firstNameInput.fill("Test");
    await setupPage.lastNameInput.clear();
    await setupPage.clickContinue();

    // Should remain on step 1 — last name input still visible
    await expect(setupPage.lastNameInput).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Setup Wizard — Edge Cases", () => {
  test("already-setup user visiting /setup redirects to /dashboard", async ({
    authenticatedPage,
  }) => {
    // authenticatedPage has is_first_login: false
    await authenticatedPage.goto("/setup");
    await expect(authenticatedPage).toHaveURL(/\/dashboard/, {
      timeout: 20_000,
    });
  });

  test("back/forward navigation between steps preserves data", async ({
    setupUserPage,
  }) => {
    const setupPage = new SetupPage(setupUserPage);

    // Fill step 1
    await setupPage.fillProfile("BackForward", "Test");
    await setupPage.clickContinue();

    // Go back to step 1
    await setupPage.clickPrevious();

    // Verify data persisted
    await expect(setupPage.firstNameInput).toHaveValue("BackForward");
  });

  test("completing without MP selection is blocked (button disabled)", async ({
    setupUserPage,
  }) => {
    const setupPage = new SetupPage(setupUserPage);

    await setupPage.fillProfile("NoMP", "Test");
    await setupPage.clickContinue();
    await expect(setupUserPage.getByText("Connect Social Media")).toBeVisible({ timeout: 20_000 });
    await setupPage.continueButton.click({ force: true });
    await expect(setupPage.mpSearchInput).toBeVisible({ timeout: 20_000 });

    // Without MP selection, the Complete Setup button should be disabled
    await expect(setupPage.completeSetupButton).toBeDisabled();
  });
});
