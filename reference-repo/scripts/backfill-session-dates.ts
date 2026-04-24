#!/usr/bin/env tsx

import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { getSessionDateFromEventPage } from "@/services/parliament/sessionDateScraper";

/**
 * Backfill script to update existing parliament_events rows with session dates
 * Usage: tsx scripts/backfill-session-dates.ts [event-id]
 *   - If event-id is provided, only process that specific event
 *   - Otherwise, process all events without session dates
 */
async function backfillSessionDates(specificEventId?: string) {
  console.log("[Backfill Session Dates] Starting backfill process...");
  if (specificEventId) {
    console.log(
      `[Backfill Session Dates] Processing specific event: ${specificEventId}`
    );
  }

  // Fetch all events without session dates
  const pageSize = 100;
  let page = 0;
  let hasMore = true;
  let totalProcessed = 0;
  let totalUpdated = 0;
  let totalFailed = 0;

  while (hasMore) {
    console.log(`[Backfill Session Dates] Fetching page ${page + 1}...`);

    let query = supabaseAdminClient
      .from("parliament_events")
      .select("id, event_id, event_url");

    if (specificEventId) {
      // Process specific event only (even if it has a session_date)
      query = query.eq("id", specificEventId);
    } else {
      // Process all events without session dates
      query = query.is("session_date", null);
    }

    const { data: events, error: fetchError } = await query
      .limit(pageSize)
      .range(page * pageSize, (page + 1) * pageSize - 1);

    if (fetchError) {
      console.error(
        "[Backfill Session Dates] Error fetching events:",
        fetchError
      );
      break;
    }

    if (!events || events.length === 0) {
      console.log("[Backfill Session Dates] No more events to process");
      hasMore = false;
      break;
    }

    console.log(
      `[Backfill Session Dates] Processing ${events.length} events...`
    );

    // Process each event
    for (let i = 0; i < events.length; i++) {
      const event = events[i];
      totalProcessed++;

      // Add rate limiting: 500ms delay between requests
      if (i > 0) {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }

      try {
        console.log(
          `[Backfill Session Dates] Processing event ${totalProcessed}: ${event.event_id} (${event.event_url})`
        );

        // Check if this is a specific event we want to debug
        const isDebugEvent =
          event.id === "64c5f111-b7bd-454d-8490-92532cae39c5";

        if (isDebugEvent) {
          console.log(
            `[Backfill Session Dates] DEBUG: Processing specific event with id ${event.id}`
          );
        }

        const sessionDate = await getSessionDateFromEventPage(event.event_url);

        if (sessionDate) {
          // Update the event with the session date
          const { error: updateError } = await supabaseAdminClient
            .from("parliament_events")
            .update({ session_date: sessionDate })
            .eq("id", event.id);

          if (updateError) {
            console.error(
              `[Backfill Session Dates] Error updating event ${event.event_id} (id: ${event.id}):`,
              updateError
            );
            totalFailed++;
          } else {
            console.log(
              `[Backfill Session Dates] Successfully updated event ${event.event_id} (id: ${event.id}) with session_date: ${sessionDate}`
            );
            totalUpdated++;
          }
        } else {
          console.warn(
            `[Backfill Session Dates] Could not extract session date for event ${event.event_id} (id: ${event.id}, url: ${event.event_url})`
          );
          if (isDebugEvent) {
            console.error(
              `[Backfill Session Dates] DEBUG: Scraper returned null for event ${event.id}. This could mean:`
            );
            console.error(`  - The h4 heading is missing on the page`);
            console.error(
              `  - The strong element with date is missing inside h4`
            );
            console.error(`  - The date format is not recognized`);
            console.error(`  - There was a timeout or error during scraping`);
          }
          totalFailed++;
        }
      } catch (error) {
        console.error(
          `[Backfill Session Dates] Error processing event ${event.event_id} (id: ${event.id}):`,
          error
        );
        if (event.id === "64c5f111-b7bd-454d-8490-92532cae39c5") {
          console.error(
            `[Backfill Session Dates] DEBUG: Full error stack for event ${event.id}:`,
            error instanceof Error ? error.stack : String(error)
          );
        }
        totalFailed++;
      }

      // Log progress every 10 events
      if (totalProcessed % 10 === 0) {
        console.log(
          `[Backfill Session Dates] Progress: ${totalProcessed} processed, ${totalUpdated} updated, ${totalFailed} failed`
        );
      }
    }

    // If processing a specific event, stop after first batch
    if (specificEventId) {
      hasMore = false;
    } else {
      // Move to next page
      page++;
      hasMore = events.length === pageSize;

      // Add a small delay between pages to be respectful
      if (hasMore) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }
  }

  console.log("[Backfill Session Dates] Backfill completed!");
  console.log(`[Backfill Session Dates] Summary:`);
  console.log(`  - Total processed: ${totalProcessed}`);
  console.log(`  - Successfully updated: ${totalUpdated}`);
  console.log(`  - Failed: ${totalFailed}`);
}

// Run the backfill script
if (require.main === module) {
  const specificEventId = process.argv[2]; // Get event ID from command line if provided
  backfillSessionDates(specificEventId)
    .then(() => {
      console.log("[Backfill Session Dates] Script finished successfully");
      process.exit(0);
    })
    .catch((error) => {
      console.error("[Backfill Session Dates] Script failed:", error);
      process.exit(1);
    });
}

export { backfillSessionDates };
