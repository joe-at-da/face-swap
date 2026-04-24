import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test("should be reachable", async ({ page }) => {
    // Navigate to the home page and verify it loads successfully
    const response = await page.goto("/");

    // Verify the page returns a successful status code
    expect(response?.status()).toBe(200);

    // Verify meaningful landing page content loaded
    await expect(
      page.getByRole("heading", { level: 1 })
    ).toBeVisible({ timeout: 20_000 });
  });

  test("footer privacy policy link routes internally", async ({ page }) => {
    await page.goto("/");

    const privacyPolicyLink = page.getByRole("link", {
      name: "Privacy Policy",
    });

    await privacyPolicyLink.scrollIntoViewIfNeeded();
    await expect(privacyPolicyLink).toHaveAttribute("href", "/privacy-policy");

    await privacyPolicyLink.click();

    await expect(page).toHaveURL(/\/privacy-policy$/);
    await expect(
      page.getByRole("heading", { name: "Privacy Policy" }),
    ).toBeVisible({ timeout: 20_000 });
  });
});
