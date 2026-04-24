import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { getSessionDataFromEventPage } from "@/services/parliament/sessionDateScraper";

export async function backfillLiveEnded() {
  console.log("[Backfill Live/Ended] Starting backfill process...");

  let page = 0;
  const pageSize = 100;
  let hasMore = true;
  let totalProcessed = 0;
  let totalUpdated = 0;
  const totalSkipped = 0;
  let totalFailed = 0;

  while (hasMore) {
    console.log(
      `[Backfill Live/Ended] Fetching page ${page + 1} (offset: ${
        page * pageSize
      })...`
    );
    const { data: events, error } = await supabaseAdminClient
      .from("parliament_events")
      .select("id, event_url, is_live, has_ended")
      .or("is_live.is.null,has_ended.is.null")
      .order("created_at", { ascending: true })
      .range(page * pageSize, (page + 1) * pageSize - 1);

    if (error) {
      console.error("[Backfill Live/Ended] Error fetching events:", error);
      break;
    }

    type ParliamentEvent = {
      id: string;
      event_url: string;
      is_live: boolean | null;
      has_ended: boolean | null;
      [key: string]: unknown;
    };
    const rows: ParliamentEvent[] = (events as ParliamentEvent[]) || [];
    if (rows.length === 0) {
      console.log("[Backfill Live/Ended] No more events to process.");
      hasMore = false;
      break;
    }

    console.log(`[Backfill Live/Ended] Processing ${rows.length} events...`);

    for (const [idx, event] of rows.entries()) {
      // Rate limit: 500ms between requests
      if (idx > 0) {
        await new Promise((r) => setTimeout(r, 500));
      }

      totalProcessed++;

      try {
        const sessionData = await getSessionDataFromEventPage(event.event_url);

        // Build update payload per rule: always set has_ended, set is_live only if not ended
        const updateData: {
          has_ended: boolean;
          is_live?: boolean;
        } = {
          has_ended: sessionData.hasEnded,
        };
        if (sessionData.hasEnded) {
          // If event has ended, it cannot be live
          updateData.is_live = false;
        } else {
          updateData.is_live = sessionData.isLive;
        }

        const { error: updateError } = await supabaseAdminClient
          .from("parliament_events")
          .update(updateData)
          .eq("id", event.id);

        if (updateError) {
          totalFailed++;
          console.error(
            `[Backfill Live/Ended] Failed updating ${event.id}:`,
            updateError
          );
        } else {
          totalUpdated++;
          console.log(`[Backfill Live/Ended] Updated ${event.id}:`, updateData);
        }
      } catch (e) {
        totalFailed++;
        console.error(
          `[Backfill Live/Ended] Error processing ${event.id} (${event.event_url}):`,
          e
        );
      }
    }

    page++;
    if (rows.length < pageSize) {
      hasMore = false;
    }
  }

  console.log(
    `[Backfill Live/Ended] Done. processed=${totalProcessed}, updated=${totalUpdated}, skipped=${totalSkipped}, failed=${totalFailed}`
  );
}

if (require.main === module) {
  backfillLiveEnded().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
