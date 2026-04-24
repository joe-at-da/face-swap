import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { Database } from "@/supabaseTypes";
import { XMLParser } from "fast-xml-parser";
import { getSessionDataFromEventPage } from "@/services/parliament/sessionDateScraper";
import { getDurationFromPlayer } from "@/scripts/backfill-session-length";

type ParliamentEventInsert =
  Database["public"]["Tables"]["parliament_events"]["Insert"];
type ParliamentEvent = Database["public"]["Tables"]["parliament_events"]["Row"];

interface AtomEvent {
  id: string;
  title: {
    "#text": string;
    "@_type": string;
  };
  updated: string;
  author: {
    name: string;
  };
  content: {
    "#text": string;
    "@_type": string;
  };
  "@_xml:base": string;
}

// Sync events starting from January 1st, 2025
const SYNC_START_DATE = "2025-01-01";

export class ParliamentEventSyncService {
  private supabase = supabaseAdminClient;
  private baseRssUrl = "http://data.parliamentlive.tv/api/event/feed";

  // Build RSS URL with date filter
  private get rssUrl(): string {
    return `${this.baseRssUrl}?fromDate=${SYNC_START_DATE}`;
  }

  async syncEvents(): Promise<{
    message: string;
    processed: number;
    filtered: number;
    existing: number;
  }> {

    try {
      // Fetch Atom feed
      const feedData = await this.fetchAtomFeed();

      // Parse XML
      const events = await this.parseAtomFeed(feedData);

      let processed = 0;
      let filtered = 0;
      let existing = 0;

      for (const [index, event] of events.entries()) {
        // Rate limiting: 500ms delay between requests
        if (index > 0) {
          await new Promise((resolve) => setTimeout(resolve, 500));
        }

        // Filter out BSL events
        if (this.containsBSL(event.title["#text"])) {
          filtered++;
          continue;
        }

        // Check if event already exists
        const eventExists = await this.eventExists(event.id);
        if (eventExists) {
          existing++;
          continue;
        }

        // Transform event
        const transformedEvent = this.transformEvent(event);

        // Fetch session data (date, is_live, has_ended) for new events
        try {
          const sessionData = await getSessionDataFromEventPage(
            transformedEvent.event_url
          );

          // Add session data to the event
          transformedEvent.session_date = sessionData.sessionDate || null;
          transformedEvent.is_live = sessionData.isLive;
          transformedEvent.has_ended = sessionData.hasEnded;

          // If session has ended, also fetch session length and start time
          if (sessionData.hasEnded) {
            try {
              const { seconds, startTime } = await getDurationFromPlayer(
                transformedEvent.event_url
              );
              if (seconds && seconds > 0) {
                transformedEvent.session_length_seconds = seconds;
              }
              if (startTime) {
                transformedEvent.session_start_time = startTime;
              }
            } catch (durationError) {
              console.warn(
                `[Parliament Event Sync] Error fetching duration/start time for event ${event.id}:`,
                durationError
              );
              // Continue with insertion even if duration fetch fails
            }
          }
        } catch (sessionError) {
          console.warn(
            `[Parliament Event Sync] Failed to fetch session data for ${transformedEvent.event_url}:`,
            sessionError
          );
          // Continue with insertion even if session data fetch fails
          transformedEvent.session_date = null;
          transformedEvent.is_live = false;
          transformedEvent.has_ended = false;
        }

        // Insert event with session data
        await this.insertEvent(transformedEvent);
        processed++;
      }

      return {
        message: "Events sync completed",
        processed,
        filtered,
        existing,
      };
    } catch (error) {
      console.error("Error during events sync:", error);
      throw error;
    }
  }

  private async fetchAtomFeed(): Promise<string> {
    const response = await fetch(this.rssUrl, {
      method: "GET",
      headers: {
        "User-Agent": "Parliament-Event-Sync-Bot/1.0",
        Accept: "application/atom+xml, application/xml, text/xml",
      },
    });

    if (!response.ok) {
      throw new Error(
        `Failed to fetch Atom feed: ${response.status} ${response.statusText}`
      );
    }

    const feedData = await response.text();

    return feedData;
  }

  private async parseAtomFeed(feedData: string): Promise<AtomEvent[]> {
    const parser = new XMLParser({
      ignoreAttributes: false,
      attributeNamePrefix: "@_",
      textNodeName: "#text",
    });

    const parsedData = parser.parse(feedData);

    if (!parsedData.feed?.entry) {
      throw new Error("Invalid Atom feed structure - no entries found");
    }

    // Handle both single entry and array of entries
    const entries = Array.isArray(parsedData.feed.entry)
      ? parsedData.feed.entry
      : [parsedData.feed.entry];

    return entries;
  }

  private containsBSL(title: string): boolean {
    return title.toLowerCase().includes("bsl");
  }

  private async eventExists(eventId: string): Promise<boolean> {
    const { data, error } = await this.supabase
      .from("parliament_events")
      .select("event_id")
      .eq("event_id", eventId)
      .single();

    if (error && error.code !== "PGRST116") {
      // PGRST116 is "not found"
      console.error("Error checking if event exists:", error);
      throw error;
    }

    return !!data;
  }

  private transformEvent(atomEvent: AtomEvent): ParliamentEventInsert {
    // Extract event ID
    const eventId = atomEvent.id;

    // Parse date
    const updatedDate = new Date(atomEvent.updated);

    // Extract title text
    const title = atomEvent.title["#text"];

    return {
      event_id: eventId,
      event_url:
        atomEvent["@_xml:base"] ||
        `https://parliamentlive.tv/event/index/${eventId}`,
      title: title,
      updated_at: updatedDate.toISOString(),
      author_name: atomEvent.author?.name || null,
      content_text: this.extractContentText(atomEvent.content["#text"]),
      content_type: atomEvent.content["@_type"] || null,
      title_type: this.extractTitleType(title),
      created_at: updatedDate.toISOString(),
      updated_at_local: updatedDate.toISOString(),
      is_deleted: false,
      status: "pending" as const,
    };
  }

  private extractContentText(content?: string): string | null {
    if (!content) return null;

    // Remove HTML tags and decode entities
    const textContent = content
      .replace(/<[^>]*>/g, "") // Remove HTML tags
      .replace(/&nbsp;/g, " ") // Replace &nbsp; with space
      .replace(/&amp;/g, "&") // Replace &amp; with &
      .replace(/&lt;/g, "<") // Replace &lt; with <
      .replace(/&gt;/g, ">") // Replace &gt; with >
      .trim();

    return textContent || null;
  }

  private extractTitleType(title: string): string | null {
    // Extract committee or house type from title
    if (title.includes("Committee")) {
      return "Committee";
    } else if (title.includes("House of Commons")) {
      return "House of Commons";
    } else if (title.includes("House of Lords")) {
      return "House of Lords";
    } else if (title.includes("Westminster Hall")) {
      return "Westminster Hall";
    }

    return null;
  }

  private async insertEvent(event: ParliamentEventInsert): Promise<void> {
    const { error } = await this.supabase
      .from("parliament_events")
      .insert(event);

    if (error) {
      console.error("Error inserting event:", error);
      throw error;
    }
  }

  async getRecentEvents(limit: number = 10): Promise<ParliamentEvent[]> {
    const { data, error } = await this.supabase
      .from("parliament_events")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(limit);

    if (error) {
      console.error("Error fetching recent events:", error);
      throw error;
    }

    return data || [];
  }
}
