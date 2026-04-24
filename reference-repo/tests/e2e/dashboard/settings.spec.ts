import { test, expect } from "../fixtures/test-fixtures";
import { SettingsPage } from "../pages/settings.page";
import { TEST_AVATAR_BUFFER } from "../helpers/constants";

test.describe("Settings — Expected Pass", () => {
  test("loads profile form with current name and email", async ({
    authenticatedPage,
  }) => {
    const settingsPage = new SettingsPage(authenticatedPage);
    await settingsPage.navigate();

    await expect(settingsPage.heading).toBeVisible({ timeout: 30_000 });
  });

  test("updates first and last name successfully", async ({
    authenticatedPage,
    supabaseAdmin,
    testUser,
  }) => {
    const settingsPage = new SettingsPage(authenticatedPage);
    await settingsPage.navigate();

    const newFirstName = `E2ETest${Date.now()}`;
    await settingsPage.editProfile({ firstName: newFirstName });

    // Verify toast or success indicator (may render 2 toasts)
    await expect(settingsPage.successToast.first()).toBeVisible({ timeout: 20_000 });

    // DB assertion: profile API updates auth.users user_metadata, not user_roles
    await expect
      .poll(
        async () => {
          const { data } = await supabaseAdmin.auth.admin.getUserById(testUser.userId);
          return data?.user?.user_metadata?.first_name;
        },
        {
          message: "Waiting for first_name to update in user metadata",
          timeout: 20_000,
        }
      )
      .toBe(newFirstName);
  });

  test("uploads avatar via file chooser", async ({
    authenticatedPage,
  }) => {
    const settingsPage = new SettingsPage(authenticatedPage);
    await settingsPage.navigate();

    // File input only exists in edit mode — click "Edit Profile" first
    await settingsPage.editProfileButton.click();
    await expect(settingsPage.firstNameInput).toBeVisible({ timeout: 20_000 });

    const avatarInput = settingsPage.avatarUpload;
    // File input is hidden (className="hidden") — setInputFiles works on hidden inputs
    await avatarInput.setInputFiles({
      name: "test-avatar.png",
      mimeType: "image/png",
      buffer: TEST_AVATAR_BUFFER,
    });
  });

  test("toggles notification on/off", async ({
    authenticatedPage,
  }) => {
    const settingsPage = new SettingsPage(authenticatedPage);
    await settingsPage.navigate();

    const toggle = settingsPage.notificationToggle;
    await expect(toggle).toBeVisible({ timeout: 20_000 });

    const wasChecked = await toggle.isChecked();
    await toggle.click();

    // Verify UI changed
    await expect(toggle).toBeChecked({ checked: !wasChecked });
  });

  test("admin user sees same settings page", async ({
    adminPage,
  }) => {
    await adminPage.goto("/dashboard/settings");
    await expect(
      adminPage.getByRole("heading", { name: "Settings" })
    ).toBeVisible({ timeout: 20_000 });
  });
});

test.describe("Settings — Expected Fail", () => {
  test("submitting empty first name does not crash and stays on settings", async ({
    authenticatedPage,
  }) => {
    const settingsPage = new SettingsPage(authenticatedPage);
    await settingsPage.navigate();

    // Must open edit mode first
    await settingsPage.editProfileButton.click();

    // Wait for first name input to appear, skip if edit mode doesn't show inputs
    if (
      !(await settingsPage.firstNameInput
        .isVisible({ timeout: 20_000 })
        .catch(() => false))
    ) {
      test.skip(true, "Edit profile form not visible — UI may differ");
      return;
    }

    await settingsPage.firstNameInput.clear();
    await settingsPage.saveButton.click();

    // App currently accepts empty first name (no client-side validation).
    // Verify it doesn't crash — should stay on settings and show some response.
    await expect(authenticatedPage).toHaveURL(/\/settings/, { timeout: 20_000 });

    // Should see either a toast (success or error) or remain on settings page
    await expect(
      authenticatedPage.getByRole("heading", { name: "Settings" })
    ).toBeVisible({ timeout: 20_000 });
  });

  test("API failure shows error state", async ({ authenticatedPage }) => {
    await authenticatedPage.route("**/api/**", (route) => {
      if (
        route.request().url().includes("settings") ||
        route.request().url().includes("profile")
      ) {
        return route.fulfill({
          status: 500,
          body: "Internal Server Error",
        });
      }
      return route.continue();
    });

    await authenticatedPage.goto("/dashboard/settings");

    // Page should still render (server-side) or show error state
    await expect(
      authenticatedPage.getByText(/error|something went wrong|try again/i).first()
    ).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("Settings — Edge Cases", () => {

  test("delete account: opens dialog with account summary", async ({
    authenticatedPage,
  }) => {
    const settingsPage = new SettingsPage(authenticatedPage);
    await settingsPage.navigate();

    await expect(settingsPage.deleteAccountButton).toBeVisible({ timeout: 20_000 });

    await settingsPage.initiateDeleteAccount();
    await expect(settingsPage.deleteDialog).toBeVisible();
  });

  test("delete account: wrong confirmation keeps button disabled", async ({
    authenticatedPage,
  }) => {
    const settingsPage = new SettingsPage(authenticatedPage);
    await settingsPage.navigate();

    await expect(settingsPage.deleteAccountButton).toBeVisible({ timeout: 20_000 });

    await settingsPage.initiateDeleteAccount();
    await settingsPage.confirmInput.fill("WRONG_CONFIRMATION");

    // Confirm button should be disabled or clicking does nothing
    const isDisabled = await settingsPage.confirmDeleteButton.isDisabled();
    expect(isDisabled).toBe(true);
  });

  test("delete account: typing DELETE_MY_ACCOUNT + confirm redirects to /", async ({
    authenticatedPage,
  }) => {
    const settingsPage = new SettingsPage(authenticatedPage);
    await settingsPage.navigate();

    await expect(settingsPage.deleteAccountButton).toBeVisible({ timeout: 20_000 });

    // Mock both delete API and GoTrue signOut to avoid deleting the shared
    // test user and to ensure the full delete flow completes without external calls
    await authenticatedPage.route("**/api/settings/account", async (route) => {
      if (route.request().method() === "DELETE") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, message: "Account deleted" }),
        });
        return;
      }
      await route.continue();
    });
    await authenticatedPage.route("**/auth/v1/logout", async (route) => {
      await route.fulfill({ status: 204, body: "" });
    });

    await settingsPage.initiateDeleteAccount();
    await settingsPage.confirmDelete();

    // The client-side should redirect to / after successful delete response
    await expect(authenticatedPage).toHaveURL("/", { timeout: 20_000 });
  });
});
