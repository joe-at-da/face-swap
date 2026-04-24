import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /dashboard/settings page.
 *
 * UI structure (from Playwright snapshot):
 * - Profile Information card with "Edit Profile" button
 * - Social Media Integration section
 * - Notification Preferences with toggle switch
 * - Delete Account section with "Delete My Account" button
 */
export class SettingsPage {
  readonly page: Page;

  // Page heading
  readonly heading: Locator;

  // Profile section
  readonly editProfileButton: Locator;
  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly saveButton: Locator;

  // Notifications
  readonly notificationToggle: Locator;

  // Danger zone
  readonly deleteAccountButton: Locator;
  readonly deleteDialog: Locator;
  readonly confirmInput: Locator;
  readonly confirmDeleteButton: Locator;

  // Avatar
  readonly avatarUpload: Locator;

  // Alerts
  readonly successToast: Locator;
  readonly errorAlert: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heading = page.getByRole("heading", { name: "Settings" });

    // Profile editing requires clicking "Edit Profile" first
    this.editProfileButton = page.getByRole("button", {
      name: "Edit Profile",
    });
    this.firstNameInput = page.getByLabel(/first name/i);
    this.lastNameInput = page.getByLabel(/last name/i);
    this.saveButton = page.getByRole("button", { name: /save/i });

    this.notificationToggle = page.getByRole("switch").first();

    this.deleteAccountButton = page.getByRole("button", {
      name: /delete.*account/i,
    });
    this.deleteDialog = page.getByRole("dialog");
    this.confirmInput = page.getByRole("textbox", {
      name: /DELETE_MY_ACCOUNT/i,
    });
    this.confirmDeleteButton = page
      .getByRole("dialog")
      .getByRole("button", { name: /delete account/i });

    this.avatarUpload = page.locator('input[type="file"]');

    this.successToast = page.getByText(/saved|updated|success/i);
    this.errorAlert = page.locator("[data-slot='alert'].text-destructive");
  }

  async navigate() {
    await this.page.goto("/dashboard/settings");
    await expect(this.heading).toBeVisible({ timeout: 20_000 });
  }

  async editProfile(data: { firstName?: string; lastName?: string }) {
    // Click "Edit Profile" to open the edit form
    await this.editProfileButton.click();
    // Wait for edit form inputs to appear
    await expect(this.firstNameInput).toBeVisible({ timeout: 10_000 });

    if (data.firstName) {
      await this.firstNameInput.clear();
      await this.firstNameInput.fill(data.firstName);
    }
    if (data.lastName) {
      await this.lastNameInput.clear();
      await this.lastNameInput.fill(data.lastName);
    }
    await this.saveButton.click();
  }

  async initiateDeleteAccount() {
    await this.deleteAccountButton.click();
    await expect(this.deleteDialog).toBeVisible();
  }

  async confirmDelete() {
    await this.confirmInput.fill("DELETE_MY_ACCOUNT");
    await this.confirmDeleteButton.click();
  }
}
