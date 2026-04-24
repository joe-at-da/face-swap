import { expect, test } from "@playwright/test";

test.describe("Terms & Conditions Page", () => {
  test.skip(
    !process.env.FIBERY_API_KEY,
    "Fibery API key not configured — skipping Fibery-backed legal tests",
  );

  test("preserves alt text on rendered legal images", async ({ page }) => {
    const response = await page.goto("/terms-and-conditions");

    expect(response?.status()).toBe(200);
    await expect(
      page.getByRole("heading", { name: "Terms & Conditions" }),
    ).toBeVisible({ timeout: 20_000 });

    const images = page.locator("article img[alt]");
    const imageCount = await images.count();

    test.skip(imageCount === 0, "No images in current T&C content");

    await expect(images.first()).toBeVisible({ timeout: 20_000 });
    await expect(images.first()).toHaveAttribute("alt", /.+/);
  });
});
