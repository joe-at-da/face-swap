import "server-only";

// Type definitions for the scraper module
interface ScrapedEvent {
  eventId: string;
  status: string;
  title: string;
  title_type: string;
  event_url: string;
  updated_at: string;
  sessionDate?: string | null; // Date in YYYY-MM-DD format, extracted from event page
}

interface ScraperModule {
  scrapeParliamentLive: (
    startDate: string,
    endDate: string
  ) => Promise<ScrapedEvent[]>;
  eventsToCSV: (events: ScrapedEvent[]) => string;
}

// Import the JavaScript scraper module
import scraperModuleRaw from "@/scripts/scrape-parliament-live.js";
const scraperModule = scraperModuleRaw as ScraperModule;

/**
 * Scrapes Parliament Live TV for House of Commons events
 * @param startDate - Start date in YYYY-MM-DD format
 * @param endDate - End date in YYYY-MM-DD format (inclusive)
 * @returns Array of scraped parliament events
 */
export async function scrapeParliamentEvents(
  startDate: string,
  endDate: string
): Promise<ScrapedEvent[]> {
  try {
    console.log(
      `[Parliament Scraper] Scraping events from ${startDate} to ${endDate}`
    );

    const events = await scraperModule.scrapeParliamentLive(startDate, endDate);

    // Remove duplicates based on eventId
    const uniqueEvents = events.filter(
      (event, index, self) =>
        index === self.findIndex((e) => e.eventId === event.eventId)
    );

    console.log(
      `[Parliament Scraper] Found ${events.length} events (${uniqueEvents.length} unique)`
    );

    return uniqueEvents;
  } catch (error) {
    console.error("[Parliament Scraper] Error:", error);
    throw new Error(
      `Failed to scrape parliament events: ${
        error instanceof Error ? error.message : "Unknown error"
      }`
    );
  }
}

/**
 * Formats date to YYYY-MM-DD string
 */
export function formatDateToISO(date: Date): string {
  return date.toISOString().split("T")[0];
}

/**
 * Calculates the date range for the last N days, including today
 * @param days - Number of days to go back (default: 30)
 * @returns Object with startDate and endDate as YYYY-MM-DD strings
 */
export function calculateDateRange(days: number = 30): {
  startDate: string;
  endDate: string;
} {
  const today = new Date();

  // End date is today (include today)
  const endDate = new Date(today);

  // Start date is N days before today (inclusive, so N days total including today)
  const startDate = new Date(today);
  startDate.setDate(startDate.getDate() - (days - 1)); // -1 because we want N days inclusive

  return {
    startDate: formatDateToISO(startDate),
    endDate: formatDateToISO(endDate),
  };
}

export type { ScrapedEvent };
