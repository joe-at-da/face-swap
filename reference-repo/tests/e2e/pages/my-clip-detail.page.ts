import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Model for the /dashboard/my-clips/[userClipId] page.
 */
export class MyClipDetailPage {
  readonly page: Page;

  readonly backButton: Locator;
  readonly clipTitle: Locator;
  readonly horizontalTab: Locator;
  readonly verticalTab: Locator;
  readonly transcript: Locator;
  readonly editTitleButton: Locator;
  readonly editTitleDialog: Locator;
  readonly titleInput: Locator;
  readonly saveTitleButton: Locator;

  readonly copyVideoLinkButton: Locator;
  readonly downloadSection: Locator;
  readonly processingStatus: Locator;

  readonly clipDetailsToggle: Locator;
  readonly videoSizeRow: Locator;

  constructor(page: Page) {
    this.page = page;

    this.backButton = page.getByRole("link", { name: /back|my clips/i });
    this.clipTitle = page.getByRole("heading").first();
    this.horizontalTab = page.getByRole("tab", { name: /horizontal/i });
    this.verticalTab = page.getByRole("tab", { name: /vertical/i });
    this.transcript = page.getByText(/transcript/i);
    this.editTitleButton = page.getByRole("button", {
      name: /edit.*title|rename/i,
    });
    this.editTitleDialog = page.getByRole("dialog");
    this.titleInput = page.getByRole("textbox", { name: /clip title/i });
    this.saveTitleButton = page.getByRole("button", { name: /save/i });

    this.copyVideoLinkButton = page.getByRole("button", {
      name: /copy video link/i,
    });
    this.downloadSection = page.getByText(/download/i);
    this.processingStatus = page.getByText(/processing|rendering/i);

    this.clipDetailsToggle = page.getByRole("button", {
      name: /clip details/i,
    });
    this.videoSizeRow = page.getByText(/video size/i);
  }

  async navigate(clipId: string) {
    await this.page.goto(`/dashboard/my-clips/${clipId}`);
  }

  async verifyClipLoaded() {
    await expect(this.clipTitle).toBeVisible({ timeout: 20_000 });
  }

  async expandClipDetails() {
    await this.clipDetailsToggle.click();
  }

  async editTitle(newTitle: string) {
    await this.editTitleButton.click();
    await expect(this.editTitleDialog).toBeVisible();
    await this.titleInput.clear();
    await this.titleInput.fill(newTitle);
    await this.saveTitleButton.click();
  }

}
