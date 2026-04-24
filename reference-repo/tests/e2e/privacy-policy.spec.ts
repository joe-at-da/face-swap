import { expect, test } from "@playwright/test";

test.describe("Privacy Policy Page", () => {
  test.skip(
    !process.env.FIBERY_API_KEY,
    "Fibery API key not configured — skipping Fibery-backed legal tests",
  );

  test("renders Fibery privacy content", async ({ page }) => {
    const response = await page.goto("/privacy-policy");

    expect(response?.status()).toBe(200);
    await expect(
      page.getByRole("heading", { name: "Privacy Policy" }),
    ).toBeVisible({ timeout: 20_000 });

    // Article exists and has non-trivial content (not an error/empty state)
    const legalArticle = page.locator("article");
    await expect(legalArticle).toBeVisible({ timeout: 20_000 });
    const text = await legalArticle.textContent();
    expect((text ?? "").trim().length).toBeGreaterThan(0);

    // Error fallback (border-dashed div) should NOT be present
    await expect(
      page.locator("div.border-dashed"),
    ).not.toBeVisible();
  });
});
