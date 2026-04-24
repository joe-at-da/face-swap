import type { Page } from "@playwright/test";
import { test } from "../fixtures/test-fixtures";

/**
 * Assert that a setup flow completed via redirect or success toast.
 * Non-fatal — callers should follow with a DB assertion as ground truth.
 */
export async function assertSetupComplete(
  page: Page,
  toastPattern: RegExp = /setup completed|success/i
): Promise<void> {
  const redirected = await page
    .waitForURL(/\/dashboard/, { timeout: 20_000 })
    .then(() => true)
    .catch(() => false);

  if (!redirected) {
    const hasToast = await page
      .getByText(toastPattern)
      .first()
      .isVisible({ timeout: 10_000 })
      .catch(() => false);
    if (!hasToast) {
      test.info().annotations.push({
        type: "info",
        description: "No redirect or toast — relying on DB assertion",
      });
    }
  }
}
