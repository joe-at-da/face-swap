import "server-only";
import { chromium, Browser } from "playwright";

export interface SessionData {
  sessionDate: string | null;
  isLive: boolean;
  hasEnded: boolean;
}

// Shared browser instance for reuse across multiple calls
// This prevents spawning multiple heavy Chromium processes
let sharedBrowser: Browser | null = null;
let browserLaunchPromise: Promise<Browser> | null = null;

/**
 * Get or create a shared browser instance
 * Uses a launch promise to prevent race conditions when multiple calls try to launch simultaneously
 */
async function getSharedBrowser(): Promise<Browser> {
  // If browser exists and is connected, return it
  if (sharedBrowser && sharedBrowser.isConnected()) {
    return sharedBrowser;
  }

  // If browser is being launched, wait for it
  if (browserLaunchPromise) {
    return browserLaunchPromise;
  }

  // Launch new browser
  browserLaunchPromise = chromium.launch({ headless: true });
  try {
    sharedBrowser = await browserLaunchPromise;
    return sharedBrowser;
  } finally {
    browserLaunchPromise = null;
  }
}

/**
 * Close the shared browser instance
 * Should be called after batch processing is complete
 */
export async function closeSharedBrowser(): Promise<void> {
  if (sharedBrowser) {
    try {
      await sharedBrowser.close();
    } catch (error) {
      console.warn("[Session Date Scraper] Error closing shared browser:", error);
    } finally {
      sharedBrowser = null;
    }
  }
}

/**
 * Fetch URL with timeout using AbortController
 */
async function fetchWithTimeout(
  url: string,
  timeout: number
): Promise<string | null> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        Accept:
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.5",
      },
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      return null;
    }

    return await response.text();
  } catch {
    clearTimeout(timeoutId);
    return null;
  }
}

/**
 * Extract session data from raw HTML without browser rendering
 */
function extractDataFromHtml(html: string): {
  dateText: string | null;
  isLive: boolean;
  hasEnded: boolean;
} {
  // Extract h4 content using regex
  const h4Match = html.match(/<h4[^>]*>([\s\S]*?)<\/h4>/i);
  const headingText = h4Match
    ? h4Match[1].replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()
    : "";

  // Extract date from strong tag (primary method)
  const strongMatch = html.match(/<h4[^>]*>[\s\S]*?<strong>([^<]+)<\/strong>/i);
  let dateText = strongMatch ? strongMatch[1].trim() : null;

  // Fallback: extract date from heading text
  if (!dateText && headingText) {
    const datePattern = /([A-Za-z]+\s+)?(\d{1,2}\s+[A-Za-z]+\s+\d{4})/i;
    const match = headingText.match(datePattern);
    dateText = match ? match[0].trim() : null;
  }

  // Check live/ended status from heading text
  const hasEnded = headingText.toLowerCase().includes("ended");
  const isLive =
    !hasEnded &&
    headingText.toLowerCase().includes("started") &&
    !headingText.toLowerCase().includes("ended");

  return { dateText, isLive, hasEnded };
}

/**
 * Extracts session data (date, is_live, has_ended) from a Parliament Live TV event page
 * @param eventUrl - Full URL to the event page (e.g., https://parliamentlive.tv/Event/Index/session-uid)
 * @returns Session data object with sessionDate, isLive, and hasEnded
 */
/**
 * Retry wrapper with exponential backoff
 */
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error | unknown;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (attempt < maxAttempts) {
        const delay = baseDelay * Math.pow(2, attempt - 1); // 1s, 2s, 4s
        console.log(
          `[Session Date Scraper] Attempt ${attempt} failed, retrying in ${delay}ms...`
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

export async function getSessionDataFromEventPage(
  eventUrl: string
): Promise<SessionData> {
  const startTime = Date.now();

  // FAST PATH: Try HTTP fetch first (static HTML contains the session data)
  try {
    const html = await fetchWithTimeout(eventUrl, 5000);
    if (html) {
      const data = extractDataFromHtml(html);
      if (data.dateText) {
        const parsedDate = parseUKDateString(data.dateText);
        if (parsedDate) {
          const loadTime = Date.now() - startTime;
          console.log(
            `[Session Date Scraper] Fast path succeeded for ${eventUrl} (${loadTime}ms):`,
            {
              sessionDate: formatDateToISO(parsedDate),
              isLive: data.isLive,
              hasEnded: data.hasEnded,
              dateText: data.dateText,
            }
          );
          return {
            sessionDate: formatDateToISO(parsedDate),
            isLive: data.isLive,
            hasEnded: data.hasEnded,
          };
        }
      }
    }
    console.log(
      `[Session Date Scraper] Fast path failed for ${eventUrl}, falling back to Playwright...`
    );
  } catch (error) {
    console.log(
      `[Session Date Scraper] Fast path error for ${eventUrl}:`,
      error instanceof Error ? error.message : error
    );
  }

  // SLOW PATH: Fall back to Playwright if HTTP fetch fails
  return retryWithBackoff(
    async () => {
      const playwrightStartTime = Date.now();
      let context = null;

      try {
        // Use shared browser instance to avoid spawning multiple Chromium processes
        const browser = await getSharedBrowser();
        context = await browser.newContext({
          userAgent:
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          viewport: { width: 1920, height: 1080 },
        });
        const page = await context.newPage();

        // Navigate to the event page with timeout - wait for DOM to be parsed (not full load)
        // Using domcontentloaded instead of load to avoid waiting for heavy video player resources
        await page.goto(eventUrl, { waitUntil: "domcontentloaded", timeout: 15000 });

        // Try to wait for h4 element with multiple strategies
        let h4Found = false;
        try {
          // First try: wait for h4 to be attached (not necessarily visible)
          // Reduced timeout since DOM should already be parsed
          await page.waitForSelector("h4", {
            state: "attached",
            timeout: 10000,
          });
          h4Found = true;
        } catch {
          // Fallback: check if h4 exists via evaluate
          h4Found = await page.evaluate(() => {
            return document.querySelector("h4") !== null;
          });

          if (!h4Found) {
            console.warn(
              `[Session Date Scraper] No h4 element found on page ${eventUrl}, proceeding with fallback extraction`
            );
          }
        }

        // Extract all data from the page
        const pageData = await page.evaluate(() => {
          const heading = document.querySelector("h4");
          const headingText = heading?.textContent?.trim() || "";
          const h4Count = document.querySelectorAll("h4").length;

          // Check live/ended status from heading text
          // More efficient than scanning all DOM elements with querySelectorAll("*")
          const hasEnded = headingText.toLowerCase().includes("ended");
          const isLive =
            !hasEnded &&
            (headingText.toLowerCase().includes("started") ||
              headingText.toLowerCase().includes("live"));

          // Extract date from h4 > strong element (primary method)
          let dateText: string | null = null;
          if (heading) {
            const strong = heading.querySelector("strong");
            if (strong) {
              dateText = strong.textContent?.trim() || null;
            }

            // Fallback: if no strong element, try to extract date from the full heading text
            if (!dateText) {
              // Look for date patterns in the heading text
              // Pattern: "Wednesday 2 April 2025" or "2 April 2025" etc.
              const datePattern =
                /([A-Za-z]+\s+)?(\d{1,2}\s+[A-Za-z]+\s+\d{4})/i;
              const match = headingText.match(datePattern);
              if (match) {
                dateText = match[0].trim();
              }
            }
          }

          // Additional fallback: search entire page for date patterns
          if (!dateText) {
            const datePattern = /([A-Za-z]+\s+)?(\d{1,2}\s+[A-Za-z]+\s+\d{4})/i;
            const allText = document.body.textContent || "";
            const match = allText.match(datePattern);
            if (match) {
              dateText = match[0].trim();
            }
          }

          return {
            dateText,
            isLive,
            hasEnded,
            headingText,
            pageHtml: heading ? heading.innerHTML : null,
            h4Count,
            pageTitle: document.title,
          };
        });

        // Parse the date string (format: "Wednesday 2 April 2025")
        let sessionDate: string | null = null;
        if (pageData.dateText) {
          const parsedDate = parseUKDateString(pageData.dateText);
          if (parsedDate) {
            sessionDate = formatDateToISO(parsedDate);
          }
        }

        const loadTime = Date.now() - playwrightStartTime;
        console.log(`[Session Date Scraper] Playwright path extracted from ${eventUrl}:`, {
          sessionDate,
          isLive: pageData.isLive,
          hasEnded: pageData.hasEnded,
          dateText: pageData.dateText,
          headingText: pageData.headingText,
          h4Count: pageData.h4Count,
          pageTitle: pageData.pageTitle,
          loadTimeMs: loadTime,
        });

        // Log debug info if date extraction failed
        if (!sessionDate && pageData.dateText) {
          console.warn(
            `[Session Date Scraper] Date text found but parsing failed: "${pageData.dateText}" from ${eventUrl}`
          );
        } else if (!sessionDate) {
          console.warn(
            `[Session Date Scraper] No date text found on page ${eventUrl}`
          );
          console.warn(
            `[Session Date Scraper] Heading text: "${pageData.headingText}"`
          );
          console.warn(
            `[Session Date Scraper] Page title: "${pageData.pageTitle}"`
          );
          console.warn(
            `[Session Date Scraper] H4 elements found: ${pageData.h4Count}`
          );
        }

        return {
          sessionDate,
          isLive: pageData.isLive,
          hasEnded: pageData.hasEnded,
        };
      } catch (error) {
        const loadTime = Date.now() - playwrightStartTime;
        const errorMessage =
          error instanceof Error ? error.message : String(error);
        const isTimeoutError =
          errorMessage.includes("Timeout") || errorMessage.includes("timeout");

        console.error(
          `[Session Date Scraper] Playwright error extracting data from ${eventUrl}:`,
          error
        );
        console.error(
          `[Session Date Scraper] Error type: ${
            isTimeoutError ? "Timeout" : "Other"
          }`
        );
        console.error(
          `[Session Date Scraper] Playwright load time before error: ${loadTime}ms`
        );

        // For timeout errors, try to get partial data using a new context
        if (isTimeoutError) {
          try {
            const browser = await getSharedBrowser();
            const fallbackContext = await browser.newContext();
            const fallbackPage = await fallbackContext.newPage();

            try {
              await fallbackPage
                .goto(eventUrl, { waitUntil: "domcontentloaded", timeout: 10000 })
                .catch(() => {});

              const fallbackData = await fallbackPage
                .evaluate(() => {
                  const datePattern =
                    /([A-Za-z]+\s+)?(\d{1,2}\s+[A-Za-z]+\s+\d{4})/i;
                  const allText = document.body.textContent || "";
                  const match = allText.match(datePattern);
                  return {
                    dateText: match ? match[0].trim() : null,
                    isLive: false,
                    hasEnded: false,
                  };
                })
                .catch(() => null);

              if (fallbackData?.dateText) {
                const parsedDate = parseUKDateString(fallbackData.dateText);
                if (parsedDate) {
                  console.log(
                    `[Session Date Scraper] Fallback extraction succeeded for ${eventUrl}`
                  );
                  return {
                    sessionDate: formatDateToISO(parsedDate),
                    isLive: fallbackData.isLive,
                    hasEnded: fallbackData.hasEnded,
                  };
                }
              }
            } finally {
              await fallbackContext.close();
            }
          } catch {
            console.warn(
              `[Session Date Scraper] Playwright fallback extraction also failed for ${eventUrl}`
            );
          }
        }

        // Re-throw to allow retry mechanism to work
        throw error;
      } finally {
        // Close context but keep browser open for reuse
        if (context) {
          await context.close();
        }
      }
    },
    3,
    1000
  ).catch((error) => {
    // Final fallback if all retries fail
    console.error(
      `[Session Date Scraper] All retry attempts failed for ${eventUrl}:`,
      error
    );
    return {
      sessionDate: null,
      isLive: false,
      hasEnded: false,
    };
  });
}

/**
 * Extracts the session date from a Parliament Live TV event page
 * @param eventUrl - Full URL to the event page (e.g., https://parliamentlive.tv/Event/Index/session-uid)
 * @returns Date string in YYYY-MM-DD format, or null if extraction fails
 * @deprecated Use getSessionDataFromEventPage instead for better performance
 */
export async function getSessionDateFromEventPage(
  eventUrl: string
): Promise<string | null> {
  const data = await getSessionDataFromEventPage(eventUrl);
  return data.sessionDate;
}

/**
 * Parses a UK date string (e.g., "Wednesday 2 April 2025") to a Date object
 * @param dateString - Date string in UK format
 * @returns Date object or null if parsing fails
 */
function parseUKDateString(dateString: string): Date | null {
  try {
    // Remove day name prefix (e.g., "Wednesday ")
    const withoutDayName = dateString.replace(/^[A-Za-z]+\s+/, "");

    // Parse the date (format: "2 April 2025")
    const date = new Date(withoutDayName);

    // Check if date is valid
    if (isNaN(date.getTime())) {
      return null;
    }

    return date;
  } catch (error) {
    console.error(
      `[Session Date Scraper] Error parsing date string "${dateString}":`,
      error
    );
    return null;
  }
}

/**
 * Formats a Date object to YYYY-MM-DD string
 * @param date - Date object to format
 * @returns Date string in YYYY-MM-DD format
 */
function formatDateToISO(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
