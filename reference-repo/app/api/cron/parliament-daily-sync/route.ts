import { NextRequest, NextResponse } from "next/server";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { ErrorLogger } from "@/lib/errorLogger";
import {
  scrapeParliamentEvents,
  formatDateToISO,
  type ScrapedEvent,
} from "@/services/parliament/scraper";
import {
  getSessionDataFromEventPage,
  closeSharedBrowser,
} from "@/services/parliament/sessionDateScraper";
import { getDurationFromPlayer } from "@/scripts/backfill-session-length";
import { Database } from "@/supabaseTypes";

type ParliamentEventInsert =
  Database["public"]["Tables"]["parliament_events"]["Insert"];

/**
 * Parliament Daily Sync - runs daily at 2 AM UTC
 * Coolify Scheduled Task: 0 2 * * *
 *
 * Syncs parliament events from September 1, 2024 to today from Parliament Live TV
 * Only inserts NEW events - existing events are skipped entirely (no updates)
 */
export async function POST(request: NextRequest) {
  try {
    // Verify CRON_SECRET for security
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
      console.warn("[Parliament Daily Sync] Unauthorized request");
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Verify Supabase configuration
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const serviceRoleKey = process.env.SUPABASE_SERVICE_KEY;

    if (!supabaseUrl || !serviceRoleKey) {
      console.error("[Parliament Daily Sync] Missing Supabase configuration");
      console.error("NEXT_PUBLIC_SUPABASE_URL exists:", !!supabaseUrl);
      console.error("SUPABASE_SERVICE_KEY exists:", !!serviceRoleKey);
      return NextResponse.json(
        {
          success: false,
          error: "Supabase configuration missing - check environment variables",
          timestamp: new Date().toISOString(),
        },
        { status: 500 },
      );
    }

    // Calculate date range: last 72 hours (3 days) including today
    const today = new Date();
    const threeDaysAgo = new Date(today);
    threeDaysAgo.setDate(threeDaysAgo.getDate() - 2);
    const startDate = formatDateToISO(threeDaysAgo);
    const endDate = formatDateToISO(today);

    // Scrape parliament events
    let scrapedEvents: ScrapedEvent[];
    try {
      scrapedEvents = await scrapeParliamentEvents(startDate, endDate);
    } catch (scrapeError) {
      console.error("[Parliament Daily Sync] Scraping error:", scrapeError);
      return NextResponse.json(
        {
          success: false,
          error: `Failed to scrape parliament events: ${
            scrapeError instanceof Error ? scrapeError.message : "Unknown error"
          }`,
          timestamp: new Date().toISOString(),
        },
        { status: 500 },
      );
    }

    if (scrapedEvents.length === 0) {
      return NextResponse.json({
        success: true,
        message: "No parliament events found to sync",
        dateRange: { startDate, endDate },
        eventsProcessed: 0,
        timestamp: new Date().toISOString(),
      });
    }

    // Get existing events to determine which are new vs updates
    const eventIds = scrapedEvents.map((e) => e.eventId);
    const BATCH_SIZE = 50;
    const existingEvents: Array<{ event_id: string; status: string }> = [];

    for (let i = 0; i < eventIds.length; i += BATCH_SIZE) {
      const batch = eventIds.slice(i, i + BATCH_SIZE);
      const { data: batchData, error: batchError } = await supabaseAdminClient
        .from("parliament_events")
        .select("event_id, status")
        .in("event_id", batch);

      if (batchError) {
        console.error(
          `[Parliament Daily Sync] Error fetching batch ${
            Math.floor(i / BATCH_SIZE) + 1
          }:`,
          batchError,
        );
        return NextResponse.json(
          {
            success: false,
            error: `Database fetch error: ${batchError.message}`,
            timestamp: new Date().toISOString(),
          },
          { status: 500 },
        );
      }

      if (batchData) {
        existingEvents.push(...batchData);
      }
    }

    const existingEventIds = new Set(existingEvents.map((e) => e.event_id));
    const newEvents = scrapedEvents.filter(
      (e) => !existingEventIds.has(e.eventId),
    );
    const skippedEvents = scrapedEvents.filter((e) =>
      existingEventIds.has(e.eventId),
    );

    // If no new events to insert, return early
    if (newEvents.length === 0) {
      return NextResponse.json({
        success: true,
        message: "No new parliament events to insert",
        summary: {
          totalEventsFound: scrapedEvents.length,
          newEventsCreated: 0,
          existingEventsSkipped: skippedEvents.length,
          dateRange: { startDate, endDate },
        },
        timestamp: new Date().toISOString(),
      });
    }

    // Filter to only process House of Commons events
    const houseOfCommonsEvents = newEvents.filter(
      (e) => e.title_type === "House of Commons",
    );
    const filteredOutEvents = newEvents.filter(
      (e) => e.title_type !== "House of Commons",
    );

    // Fetch session data for new House of Commons events
    const CONCURRENCY_LIMIT = 3;

    type EventWithData = ScrapedEvent & {
      sessionDate: string | null;
      isLive: boolean;
      hasEnded: boolean;
      sessionLengthSeconds: number | null;
      sessionStartTime: string | null;
    };

    const eventsWithData: EventWithData[] = [];

    // Helper function to process a single event
    async function processEvent(event: ScrapedEvent): Promise<EventWithData> {
      try {
        const sessionData = await getSessionDataFromEventPage(event.event_url);

        // If session has ended, also fetch session length and start time
        let sessionLengthSeconds: number | null = null;
        let sessionStartTime: string | null = null;

        if (sessionData.hasEnded) {
          try {
            const { seconds, startTime } = await getDurationFromPlayer(
              event.event_url,
            );
            if (seconds && seconds > 0) {
              sessionLengthSeconds = seconds;
            }
            if (startTime) {
              sessionStartTime = startTime;
            }
          } catch (durationError) {
            console.warn(
              `[Parliament Daily Sync] Error fetching duration/start time for new event ${event.eventId}:`,
              durationError,
            );
          }
        }

        return {
          ...event,
          sessionDate: sessionData.sessionDate,
          isLive: sessionData.isLive,
          hasEnded: sessionData.hasEnded,
          sessionLengthSeconds,
          sessionStartTime,
        };
      } catch (error) {
        console.warn(
          `[Parliament Daily Sync] Failed to fetch session data for ${event.event_url}:`,
          error,
        );
        return {
          ...event,
          sessionDate: null,
          isLive: false,
          hasEnded: false,
          sessionLengthSeconds: null,
          sessionStartTime: null,
        };
      }
    }

    // Process events in batches of CONCURRENCY_LIMIT
    for (let i = 0; i < houseOfCommonsEvents.length; i += CONCURRENCY_LIMIT) {
      const batch = houseOfCommonsEvents.slice(i, i + CONCURRENCY_LIMIT);

      const batchResults = await Promise.all(batch.map(processEvent));
      eventsWithData.push(...batchResults);

      // Rate limit: 1 second delay between batches (except after last one)
      if (i + CONCURRENCY_LIMIT < houseOfCommonsEvents.length) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }

    // Close shared browser after all scraping is complete to free memory
    await closeSharedBrowser();

    // Combine House of Commons events (with session data) and filtered out events (without session data)
    const allEventsToInsert = [
      ...eventsWithData,
      ...filteredOutEvents.map((event) => ({
        ...event,
        sessionDate: null,
        isLive: false,
        hasEnded: false,
        sessionLengthSeconds: null,
        sessionStartTime: null,
      })),
    ];

    const sessionDatesFetched = eventsWithData.filter(
      (e) => e.sessionDate !== null,
    ).length;

    // Only prepare NEW events for insertion
    const eventsToInsert: ParliamentEventInsert[] = allEventsToInsert.map(
      (event) => ({
        event_id: event.eventId,
        title: event.title,
        title_type: event.title_type,
        event_url: event.event_url,
        updated_at: event.updated_at,
        status: "pending" as const,
        session_date: event.sessionDate || null,
        is_live: event.isLive,
        has_ended: event.hasEnded,
        session_length_seconds: event.sessionLengthSeconds || null,
        session_start_time: event.sessionStartTime || null,
      }),
    );

    // Insert events in batches to avoid database statement timeout
    const INSERT_BATCH_SIZE = 25;
    const insertedData: ParliamentEventInsert[] = [];
    const insertErrors: string[] = [];

    for (let i = 0; i < eventsToInsert.length; i += INSERT_BATCH_SIZE) {
      const batch = eventsToInsert.slice(i, i + INSERT_BATCH_SIZE);
      const batchNumber = Math.floor(i / INSERT_BATCH_SIZE) + 1;

      const { data: batchData, error: batchError } = await supabaseAdminClient
        .from("parliament_events")
        .insert(batch)
        .select();

      if (batchError) {
        console.error(
          `[Parliament Daily Sync] Batch ${batchNumber} insert error:`,
          batchError,
        );
        insertErrors.push(`Batch ${batchNumber}: ${batchError.message}`);
        // Continue with other batches instead of failing completely
      } else if (batchData) {
        insertedData.push(...batchData);
      }

      // Small delay between batches to avoid overwhelming the database
      if (i + INSERT_BATCH_SIZE < eventsToInsert.length) {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
    }

    // Report any errors but don't fail if some batches succeeded
    if (insertErrors.length > 0) {
      console.error(
        `[Parliament Daily Sync] ${insertErrors.length} batch(es) failed:`,
        insertErrors,
      );
    }

    // Verify data was actually inserted
    if (insertedData.length === 0 && eventsToInsert.length > 0) {
      console.error(
        "[Parliament Daily Sync] WARNING: No data was returned from insert operations",
      );
      console.error(
        "[Parliament Daily Sync] Attempted to insert:",
        JSON.stringify(eventsToInsert.slice(0, 2), null, 2),
      );
      return NextResponse.json(
        {
          success: false,
          error: `All insert batches failed: ${insertErrors.join("; ")}`,
          timestamp: new Date().toISOString(),
        },
        { status: 500 },
      );
    }

    // Update existing events where has_ended = false
    const { data: eventsToUpdate, error: fetchUpdateError } =
      await supabaseAdminClient
        .from("parliament_events")
        .select("id, event_id, event_url, title_type")
        .eq("has_ended", false)
        .limit(100); // Limit to avoid overwhelming the system

    if (fetchUpdateError) {
      console.error(
        "[Parliament Daily Sync] Error fetching events to update:",
        fetchUpdateError,
      );
    } else if (eventsToUpdate && eventsToUpdate.length > 0) {
      // Filter to only update House of Commons events
      const houseOfCommonsEventsToUpdate = eventsToUpdate.filter(
        (e) => e.title_type === "House of Commons",
      );
      for (const [index, event] of houseOfCommonsEventsToUpdate.entries()) {
        // Add rate limiting: 1000ms (1 second) delay between requests
        if (index > 0) {
          await new Promise((resolve) => setTimeout(resolve, 1000));
        }

        try {
          const sessionData = await getSessionDataFromEventPage(
            event.event_url,
          );

          const updateData: {
            has_ended: boolean;
            is_live?: boolean;
            session_length_seconds?: number;
            session_start_time?: string | null;
          } = {
            has_ended: sessionData.hasEnded,
          };

          // If session has ended, update is_live to false and fetch session length and start time
          if (sessionData.hasEnded) {
            updateData.is_live = false;

            // Fetch session length and start time for ended sessions
            try {
              const { seconds, startTime } = await getDurationFromPlayer(
                event.event_url,
              );
              if (seconds && seconds > 0) {
                updateData.session_length_seconds = seconds;
              } else {
                console.warn(
                  `[Parliament Daily Sync] Could not determine session length for event ${event.id}`,
                );
              }
              if (startTime) {
                updateData.session_start_time = startTime;
              } else {
                console.warn(
                  `[Parliament Daily Sync] Could not determine session start time for event ${event.id}`,
                );
              }
            } catch (durationError) {
              console.warn(
                `[Parliament Daily Sync] Error fetching session length/start time for event ${event.id}:`,
                durationError,
              );
              // Continue with update even if duration fetch fails
            }
          } else {
            // Only update is_live if session hasn't ended
            updateData.is_live = sessionData.isLive;
          }

          const { error: updateError } = await supabaseAdminClient
            .from("parliament_events")
            .update(updateData)
            .eq("id", event.id);

          if (updateError) {
            console.error(
              `[Parliament Daily Sync] Error updating event ${event.id}:`,
              updateError,
            );
          }
        } catch (error) {
          console.error(
            `[Parliament Daily Sync] Error fetching session data for event ${event.id}:`,
            error,
          );
        }
      }

    }

    const summary = {
      totalEventsFound: scrapedEvents.length,
      newEventsCreated: newEvents.length,
      existingEventsSkipped: skippedEvents.length,
      sessionDatesFetched,
      dateRange: { startDate, endDate },
      newEventIds: newEvents.map((e) => e.eventId).slice(0, 10), // Show first 10 for brevity
      skippedEventIds: skippedEvents.map((e) => e.eventId).slice(0, 10), // Show first 10 skipped
    };

    return NextResponse.json({
      success: true,
      message: "Parliament daily sync completed successfully",
      summary,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[Parliament Daily Sync] Unexpected error:", error);

    // Log to GlitchTip for error tracking
    ErrorLogger.logError(error, {
      component: "cron/parliament-daily-sync",
      action: "parliament-daily-sync-job",
      route: "/api/cron/parliament-daily-sync",
    });

    return NextResponse.json(
      {
        success: false,
        error: "Parliament daily sync failed",
        timestamp: new Date().toISOString(),
      },
      { status: 500 },
    );
  }
}
