import { test, expect, type Page } from "@playwright/test";
import { ContactPage } from "../pages/contact.page";

// ─── Test Data ───────────────────────────────────────────────────────────────

const VALID_DATA = {
  name: "E2E Test User",
  email: "e2e-contact-test@example.com",
  phone: "+44 7700 900000",
  message: "This is a test message from the E2E test suite.",
};

// ─── RSC Mock Helpers ────────────────────────────────────────────────────────
// Next.js server actions are called as POST to the page URL with a Next-Action
// header. The response uses the RSC wire format (text/x-component).
// Format captured from real response:
//   :N<timestamp>
//   0:{"a":"$@1","f":"","b":"development"}
//   1:{"success":true}

/**
 * Build an RSC wire-format body for a mocked server action response.
 * Format captured from a real Next.js 15 / Turbopack server action response.
 */
function buildRscBody(result: object): string {
  const ts = Date.now();
  return `:N${ts}\n0:{"a":"$@1","f":"","b":"development"}\n1:D{"time":0.1}\n1:${JSON.stringify(result)}\n`;
}

/** RSC response headers required for Next.js to accept the server action result. */
const RSC_HEADERS = {
  "x-action-revalidated": "[[],0,0]",
  vary: "rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch",
  "cache-control": "no-store, must-revalidate",
};

/**
 * Intercept the contact form server action and return a mocked response.
 * This prevents any real Fibery API calls during testing.
 */
async function mockContactAction(
  page: Page,
  result: { success: true } | { success: false; error: string },
  options?: { delayMs?: number }
) {
  await page.route("**/contact", async (route) => {
    const req = route.request();
    if (req.method() === "POST" && req.headers()["next-action"]) {
      if (options?.delayMs) {
        await new Promise((r) => setTimeout(r, options.delayMs));
      }
      await route.fulfill({
        status: 200,
        contentType: "text/x-component",
        headers: RSC_HEADERS,
        body: buildRscBody(result),
      });
    } else {
      await route.continue();
    }
  });
}

// ─── Expected Pass ───────────────────────────────────────────────────────────

test.describe("Contact Form — Expected Pass", () => {
  let contactPage: ContactPage;

  test.beforeEach(async ({ page }) => {
    contactPage = new ContactPage(page);
    await contactPage.navigate();
  });

  test("page loads with form visible", async () => {
    await expect(contactPage.heading).toBeVisible();
    await expect(contactPage.subtitle).toBeVisible();
    await expect(contactPage.nameInput).toBeVisible();
    await expect(contactPage.emailInput).toBeVisible();
    await expect(contactPage.phoneInput).toBeVisible();
    await expect(contactPage.messageInput).toBeVisible();
    await expect(contactPage.submitButton).toBeVisible();
  });

  test("shows required indicators on name, email, and message", async ({
    page,
  }) => {
    // Name, Email, and Message labels have a red asterisk "*"
    const nameLabel = page.locator("label", { hasText: "Name" });
    const emailLabel = page.locator("label", { hasText: "Email" });
    const messageLabel = page.locator("label", { hasText: "Message" });
    const phoneLabel = page.locator("label", { hasText: "Phone" });

    await expect(nameLabel.locator(".text-destructive")).toBeVisible();
    await expect(emailLabel.locator(".text-destructive")).toBeVisible();
    await expect(messageLabel.locator(".text-destructive")).toBeVisible();

    // Phone should NOT have a required indicator
    await expect(phoneLabel.locator(".text-destructive")).not.toBeVisible();
  });

  test("successful submission shows thank you screen", async ({ page }) => {
    await mockContactAction(page, { success: true });

    await contactPage.fillAndSubmit(VALID_DATA);

    await expect(contactPage.successHeading).toBeVisible();
    await expect(contactPage.successMessage).toBeVisible();
    await expect(contactPage.sendAnotherButton).toBeVisible();

    // Form should no longer be visible
    await expect(contactPage.submitButton).not.toBeVisible();
  });

  test("submission works without phone number", async ({ page }) => {
    await mockContactAction(page, { success: true });

    await contactPage.fillAndSubmit({
      name: VALID_DATA.name,
      email: VALID_DATA.email,
      message: VALID_DATA.message,
    });

    await expect(contactPage.successHeading).toBeVisible();
  });

  test("send another message resets form", async ({ page }) => {
    await mockContactAction(page, { success: true });

    await contactPage.fillAndSubmit(VALID_DATA);
    await expect(contactPage.successHeading).toBeVisible();

    await contactPage.sendAnotherMessage();

    // Form should reappear with empty fields
    await expect(contactPage.submitButton).toBeVisible();
    await expect(contactPage.nameInput).toHaveValue("");
    await expect(contactPage.emailInput).toHaveValue("");
    await expect(contactPage.phoneInput).toHaveValue("");
    await expect(contactPage.messageInput).toHaveValue("");

    // Success screen should be gone
    await expect(contactPage.successHeading).not.toBeVisible();
  });

  test("inputs are disabled during submission", async ({ page }) => {
    // Use a long delay so we can inspect loading state
    await mockContactAction(page, { success: true }, { delayMs: 3000 });

    await contactPage.fillForm(VALID_DATA);
    await contactPage.submit();

    // All inputs should be disabled while submitting
    await expect(contactPage.nameInput).toBeDisabled();
    await expect(contactPage.emailInput).toBeDisabled();
    await expect(contactPage.phoneInput).toBeDisabled();
    await expect(contactPage.messageInput).toBeDisabled();

    // Button should show "Sending..." text
    await expect(contactPage.sendingButton).toBeVisible();
    await expect(contactPage.submitButton).not.toBeVisible();

    // Wait for submission to complete
    await expect(contactPage.successHeading).toBeVisible({ timeout: 10_000 });
  });

  test("form preserves data on server error", async ({ page }) => {
    await mockContactAction(page, {
      success: false,
      error: "Failed to send your message. Please try again.",
    });

    await contactPage.fillAndSubmit(VALID_DATA);

    // Error alert should be visible
    await expect(contactPage.errorAlert).toBeVisible();
    await expect(contactPage.errorAlertText).toContainText(
      "Failed to send your message"
    );

    // Form data should be preserved
    await expect(contactPage.nameInput).toHaveValue(VALID_DATA.name);
    await expect(contactPage.emailInput).toHaveValue(VALID_DATA.email);
    await expect(contactPage.phoneInput).toHaveValue(VALID_DATA.phone);
    await expect(contactPage.messageInput).toHaveValue(VALID_DATA.message);
  });
});

// ─── Expected Fail (Client-Side Validation) ──────────────────────────────────

test.describe("Contact Form — Expected Fail", () => {
  let contactPage: ContactPage;

  test.beforeEach(async ({ page }) => {
    contactPage = new ContactPage(page);
    await contactPage.navigate();
  });

  test("empty name shows validation error on blur", async ({ page }) => {
    await contactPage.nameInput.focus();
    await contactPage.blurActiveField();

    await expect(page.getByText("Name is required")).toBeVisible();
  });

  test("empty email shows validation error on blur", async ({ page }) => {
    await contactPage.emailInput.focus();
    await contactPage.blurActiveField();

    await expect(page.getByText("Email is required")).toBeVisible();
  });

  test("invalid email shows validation error on blur", async ({ page }) => {
    await contactPage.fillEmail("not-an-email");
    await contactPage.blurActiveField();

    await expect(
      page.getByText("Please enter a valid email address")
    ).toBeVisible();
  });

  test("empty message shows validation error on blur", async ({ page }) => {
    await contactPage.messageInput.focus();
    await contactPage.blurActiveField();

    await expect(page.getByText("Message is required")).toBeVisible();
  });

  test("invalid phone number shows validation error", async ({ page }) => {
    await contactPage.fillPhone("abc!@#");
    await contactPage.blurActiveField();

    await expect(
      page.getByText("Please enter a valid phone number")
    ).toBeVisible();
  });

  test("name exceeding 200 chars shows error", async ({ page }) => {
    await contactPage.fillName("a".repeat(201));
    await contactPage.blurActiveField();

    await expect(
      page.getByText("Name must be under 200 characters")
    ).toBeVisible();
  });

  test("server error displays alert with error message", async ({ page }) => {
    const errorMessage = "Custom server error for testing.";
    await mockContactAction(page, { success: false, error: errorMessage });

    await contactPage.fillAndSubmit(VALID_DATA);

    await expect(contactPage.errorAlert).toBeVisible();
    await expect(contactPage.errorAlertText).toContainText(errorMessage);
  });
});

// ─── Edge Cases ──────────────────────────────────────────────────────────────

test.describe("Contact Form — Edge Cases", () => {
  let contactPage: ContactPage;

  test.beforeEach(async ({ page }) => {
    contactPage = new ContactPage(page);
    await contactPage.navigate();
  });

  test("whitespace-only name is rejected", async ({ page }) => {
    await contactPage.fillName("   ");
    await contactPage.blurActiveField();

    await expect(page.getByText("Name is required")).toBeVisible();
  });

  test("whitespace-only message is rejected", async ({ page }) => {
    await contactPage.fillMessage("   ");
    await contactPage.blurActiveField();

    await expect(page.getByText("Message is required")).toBeVisible();
  });

  test("double submission is prevented", async ({ page }) => {
    await mockContactAction(page, { success: true }, { delayMs: 2000 });

    await contactPage.fillForm(VALID_DATA);
    await contactPage.submit();

    // Button should be disabled during submission
    await expect(contactPage.sendingButton).toBeVisible();
    await expect(contactPage.sendingButton).toBeDisabled();

    // Wait for completion
    await expect(contactPage.successHeading).toBeVisible({ timeout: 10_000 });
  });

  test("special characters in name and message are handled", async ({
    page,
  }) => {
    await mockContactAction(page, { success: true });

    await contactPage.fillAndSubmit({
      name: "<script>alert('xss')</script>",
      email: "test@example.com",
      message: "Unicode: 你好 🎉 & <b>HTML</b> entities",
    });

    await expect(contactPage.successHeading).toBeVisible();
  });

  test("error then retry succeeds", async ({ page }) => {
    // First mock: error
    await mockContactAction(page, {
      success: false,
      error: "Temporary failure.",
    });

    await contactPage.fillAndSubmit(VALID_DATA);
    await expect(contactPage.errorAlert).toBeVisible();

    // Clear route and set success mock
    await page.unroute("**/contact");
    await mockContactAction(page, { success: true });

    // Retry submission
    await contactPage.submit();
    await expect(contactPage.successHeading).toBeVisible();
  });

  test("message at max length (5000 chars) is accepted", async ({ page }) => {
    await mockContactAction(page, { success: true });

    await contactPage.fillAndSubmit({
      name: VALID_DATA.name,
      email: VALID_DATA.email,
      message: "a".repeat(5000),
    });

    await expect(contactPage.successHeading).toBeVisible();
  });
});
