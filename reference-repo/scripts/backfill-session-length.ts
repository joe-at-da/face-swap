import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { chromium } from "playwright";

export function parseHMS(text: string): number | null {
  // Supports HH:MM:SS
  const m = text.trim().match(/^(\d{1,2}):(\d{2}):(\d{2})$/);
  if (!m) return null;
  const h = parseInt(m[1], 10);
  const mm = parseInt(m[2], 10);
  const ss = parseInt(m[3], 10);
  if (isNaN(h) || isNaN(mm) || isNaN(ss)) return null;
  return h * 3600 + mm * 60 + ss;
}

/**
 * Converts a time string with am/pm to HH:MM:SS format (24-hour)
 * @param timeStr - Time string like "11.33am" or "11:33am" or "7.50pm"
 * @param ap - "am" or "pm"
 * @returns Time in HH:MM:SS format (24-hour), e.g., "11:33:00" or "19:50:00"
 */
function convertToHHMMSS(timeStr: string, ap: string): string {
  const separator = timeStr.includes(".") ? "." : ":";
  const [hhStr, mmStr] = timeStr.split(separator);
  let hh = parseInt(hhStr, 10);
  const mm = parseInt(mmStr, 10);
  const isPM = ap.toLowerCase() === "pm";

  // Convert 12-hour to 24-hour format
  if (hh === 12) {
    hh = isPM ? 12 : 0;
  } else if (isPM) {
    hh += 12;
  }

  // Format as HH:MM:SS
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}:00`;
}

export async function getDurationFromPlayer(eventUrl: string): Promise<{
  seconds: number | null;
  method: "player" | "header" | "none";
  startTime?: string | null;
}> {
  let browser;
  const debug =
    eventUrl.includes("5dd1a2b9-4dcb-470c-8a6c-06b5df19b819") ||
    process.env.DEBUG_DURATION === "true";

  try {
    browser = await chromium.launch({ headless: !debug });
    const context = await browser.newContext({
      userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    });
    const page = await context.newPage();

    if (debug) {
      console.log(`[Duration Scraper] Navigating to: ${eventUrl}`);
    }

    await page.goto(eventUrl, {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });

    // Wait for page to load and iframes to appear
    await page.waitForTimeout(2000); // Increased wait time for player to load

    // Try to locate any frame that contains two time labels (start and end)
    const frames = page.frames();

    if (debug) {
      console.log(`[Duration Scraper] Found ${frames.length} frames`);
    }

    for (let i = 0; i < frames.length; i++) {
      const f = frames[i];
      try {
        // Look for two timestamp elements near the timeline; the earlier browser exploration
        // shows two numbers like 11:34:06 and 19:50:02 rendered as plain text nodes.
        const texts = await f
          .locator("text=/^\\d{1,2}:[0-5]\\d:[0-5]\\d$/")
          .allTextContents();

        if (debug && i === 0) {
          console.log(`[Duration Scraper] Frame ${i} timestamps found:`, texts);
        }

        if (texts && texts.length >= 2) {
          // choose first and last as start and end
          const startLabel = texts[0];
          const endLabel = texts[texts.length - 1];
          const startS = parseHMS(startLabel);
          const endS = parseHMS(endLabel);

          if (debug) {
            console.log(
              `[Duration Scraper] Parsed timestamps: start=${startLabel} (${startS}s), end=${endLabel} (${endS}s)`
            );
          }

          if (startS !== null && endS !== null && endS > startS) {
            return {
              seconds: endS - startS,
              method: "player",
              startTime: startLabel,
            };
          }
        }

        // Alternative: Look for duration/time information in other formats
        // Sometimes the player shows duration or remaining time differently
        const allText = await f
          .locator("body")
          .textContent()
          .catch(() => null);
        if (allText && debug) {
          // Look for patterns like "Duration: 1:23:45" or similar
          const durationPatterns = [
            /(?:duration|length|time)[:\s]+(\d{1,2}):(\d{2}):(\d{2})/i,
            /(\d{1,2}):(\d{2}):(\d{2})\s*(?:duration|total|length)/i,
          ];

          for (const pattern of durationPatterns) {
            const match = allText.match(pattern);
            if (match) {
              const hours = parseInt(match[1], 10);
              const minutes = parseInt(match[2], 10);
              const seconds = parseInt(match[3], 10);
              if (!isNaN(hours) && !isNaN(minutes) && !isNaN(seconds)) {
                const totalSeconds = hours * 3600 + minutes * 60 + seconds;
                if (debug) {
                  console.log(
                    `[Duration Scraper] Found duration pattern: ${totalSeconds}s`
                  );
                }
                return {
                  seconds: totalSeconds,
                  method: "player",
                  startTime: null,
                };
              }
            }
          }
        }
      } catch (e) {
        if (debug) {
          console.log(`[Duration Scraper] Error in frame ${i}:`, e);
        }
        // ignore and try next frame
      }
    }

    // Fallback: parse header h4 content if available
    const header = await page
      .locator("h4")
      .first()
      .textContent()
      .catch(() => null);

    if (debug) {
      console.log(`[Duration Scraper] H4 header text:`, header);
    }

    if (header) {
      // Try multiple patterns for start/end times
      const patterns = [
        // Pattern 1: Multi-day - "started at 2.33pm, ended Tuesday 10 June 2025 12.00am"
        /started at\s+(\d{1,2}\.\d{2})(am|pm).*?ended\s+[A-Za-z]+\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}\s+(\d{1,2}\.\d{2})(am|pm)/i,
        // Pattern 2: Multi-day - "started at 2:33pm, ended Tuesday 10 June 2025 12:00am"
        /started at\s+(\d{1,2}:\d{2})(am|pm).*?ended\s+[A-Za-z]+\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}\s+(\d{1,2}:\d{2})(am|pm)/i,
        // Pattern 3: Same day - "started at 11.34am...ended 7.50pm"
        /started at\s+(\d{1,2}\.\d{2})(am|pm).*?ended\s+(\d{1,2}\.\d{2})(am|pm)/i,
        // Pattern 4: Same day - "started at 11:34am...ended 7:50pm"
        /started at\s+(\d{1,2}:\d{2})(am|pm).*?ended\s+(\d{1,2}:\d{2})(am|pm)/i,
        // Pattern 5: "started 11.34am...ended 7.50pm" (without "at")
        /started\s+(\d{1,2}\.\d{2})(am|pm).*?ended\s+(\d{1,2}\.\d{2})(am|pm)/i,
        // Pattern 6: "Meeting started at 2.33pm, ended Tuesday 10 June 2025 12.00am" (more flexible)
        /started at\s+(\d{1,2}[.:]\d{2})(am|pm).*?ended\s+[A-Za-z]+\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}\s+(\d{1,2}[.:]\d{2})(am|pm)/i,
      ];

      for (const pattern of patterns) {
        const m = header.match(pattern);
        if (m) {
          const toSeconds = (timeStr: string, ap: string): number => {
            const separator = timeStr.includes(".") ? "." : ":";
            const [hhStr, mmStr] = timeStr.split(separator);
            let hh = parseInt(hhStr, 10);
            const mm = parseInt(mmStr, 10);
            const isPM = ap.toLowerCase() === "pm";
            if (hh === 12) {
              hh = isPM ? 12 : 0;
            } else if (isPM) {
              hh += 12;
            }
            return hh * 3600 + mm * 60;
          };

          const start = toSeconds(m[1], m[2]);
          const end = toSeconds(m[3], m[4]);
          const startTime = convertToHHMMSS(m[1], m[2]);

          if (debug) {
            console.log(
              `[Duration Scraper] Parsed header times: start=${m[1]}${m[2]} (${start}s, ${startTime}), end=${m[3]}${m[4]} (${end}s)`
            );
          }

          // For multi-day sessions, if end time is less than start time (e.g., 00:00 vs 14:33),
          // add 24 hours to the end time
          let endSeconds = end;
          if (end <= start) {
            // Likely spans midnight, so add 24 hours
            endSeconds = end + 24 * 3600;
            if (debug) {
              console.log(
                `[Duration Scraper] Detected multi-day session, adding 24 hours to end time`
              );
            }
          }

          const duration = endSeconds - start;

          if (duration > 0) {
            if (debug) {
              console.log(
                `[Duration Scraper] Calculated duration: ${duration}s (${Math.floor(
                  duration / 3600
                )}h ${Math.floor((duration % 3600) / 60)}m)`
              );
            }
            return { seconds: duration, method: "header", startTime };
          }
        }
      }
    }

    // Additional fallback: check if session_length_seconds might be in page metadata or JSON-LD
    try {
      const jsonLd = await page
        .locator('script[type="application/ld+json"]')
        .textContent()
        .catch(() => null);
      if (jsonLd) {
        const data = JSON.parse(jsonLd);
        if (data.duration) {
          // ISO 8601 duration format (PT1H23M45S) or seconds
          if (typeof data.duration === "number") {
            return {
              seconds: data.duration,
              method: "header",
              startTime: null,
            };
          }
        }
      }
    } catch {
      // ignore JSON-LD parsing errors
    }

    if (debug) {
      console.log(`[Duration Scraper] All methods failed, returning null`);
      // Take a screenshot for debugging
      await page
        .screenshot({ path: "/tmp/duration-debug.png" })
        .catch(() => {});
      console.log(
        `[Duration Scraper] Screenshot saved to /tmp/duration-debug.png`
      );
    }

    return { seconds: null, method: "none", startTime: null };
  } catch (e) {
    console.error("[Backfill Session Length] Error scraping:", e);
    if (debug) {
      console.error(
        "[Backfill Session Length] Full error:",
        e instanceof Error ? e.stack : String(e)
      );
    }
    return { seconds: null, method: "none", startTime: null };
  } finally {
    if (browser) await browser.close();
  }
}

export async function backfillSessionLength(specificEventId?: string) {
  console.log("[Backfill Session Length] Starting backfill process...");
  if (specificEventId) {
    console.log(
      `[Backfill Session Length] Processing specific event: ${specificEventId}`
    );
  }

  const pageSize = 50; // smaller batch due to heavier player loads
  let lastCreatedAt: string | null = null;
  let lastId: string | null = null;
  let hasMore = true;
  let totalProcessed = 0;
  let totalUpdated = 0;
  let totalFailed = 0;
  let totalSkipped = 0;
  let page = 0;

  while (hasMore) {
    page++;
    console.log(
      `[Backfill Session Length] Fetching page ${page}${
        lastCreatedAt && lastId
          ? ` (after ${lastCreatedAt}, id: ${lastId})`
          : ""
      }...`
    );

    let query = supabaseAdminClient
      .from("parliament_events")
      .select("id, event_url, session_length_seconds, has_ended, created_at")
      .order("created_at", { ascending: true })
      .order("id", { ascending: true })
      .limit(pageSize);

    if (specificEventId) {
      // Process specific event only (even if it has a session_length_seconds)
      query = query.eq("id", specificEventId);
    } else {
      // Process all events without session length
      query = query.is("session_length_seconds", null);
      if (lastCreatedAt && lastId) {
        // Use composite cursor: (created_at > lastCreatedAt) OR (created_at = lastCreatedAt AND id > lastId)
        // PostgREST filter syntax: comma-separated conditions in .or(), with and() for nested AND
        query = query.or(
          `created_at.gt.${lastCreatedAt},and(created_at.eq.${lastCreatedAt},id.gt.${lastId})`
        );
      }
    }

    const { data: events, error } = await query;

    if (error) {
      console.error("[Backfill Session Length] Error fetching events:", error);
      break;
    }

    type ParliamentEvent = {
      id: string;
      event_url: string;
      session_length_seconds: number | null;
      has_ended: boolean | null;
      created_at: string;
      [key: string]: unknown;
    };
    const rows: ParliamentEvent[] = (events as ParliamentEvent[]) || [];
    if (rows.length === 0) {
      console.log("[Backfill Session Length] No more events to process.");
      hasMore = false;
      break;
    }

    console.log(
      `[Backfill Session Length] Processing ${rows.length} events...`
    );

    for (const [idx, event] of rows.entries()) {
      // Rate limiting: 1000ms
      if (idx > 0) await new Promise((r) => setTimeout(r, 1000));

      totalProcessed++;

      // Only compute for ended sessions to ensure full duration
      if (!event.has_ended) {
        totalSkipped++;
        console.log(
          `[Backfill Session Length] Skipping ${event.id} (not ended)`
        );
        continue;
      }

      try {
        const { seconds, method } = await getDurationFromPlayer(
          event.event_url
        );
        if (seconds && seconds > 0) {
          const { error: updateError } = await supabaseAdminClient
            .from("parliament_events")
            .update({ session_length_seconds: seconds })
            .eq("id", event.id);

          if (updateError) {
            totalFailed++;
            console.error(
              `[Backfill Session Length] Failed updating ${event.id}:`,
              updateError
            );
          } else {
            totalUpdated++;
            console.log(
              `[Backfill Session Length] Updated ${event.id} to ${seconds}s (method=${method})`
            );
          }
        } else {
          totalSkipped++;
          console.warn(
            `[Backfill Session Length] Could not determine duration for ${event.id} (method=${method}, url=${event.event_url})`
          );

          // Debug specific event
          if (event.id === "5dd1a2b9-4dcb-470c-8a6c-06b5df19b819") {
            console.error(
              `[Backfill Session Length] DEBUG: Event ${event.id} failed to extract duration`
            );
            console.error(
              `[Backfill Session Length] DEBUG: URL: ${event.event_url}`
            );
            console.error(
              `[Backfill Session Length] DEBUG: Method returned: ${method}`
            );
          }
        }
      } catch (e) {
        totalFailed++;
        console.error(
          `[Backfill Session Length] Error processing ${event.id}:`,
          e
        );
      }
    }

    // If processing a specific event, stop after first batch
    if (specificEventId) {
      hasMore = false;
    } else {
      // Update cursor to the last event's created_at and id in this batch
      // This ensures we don't reprocess the same events in the next iteration
      if (rows.length > 0) {
        const lastRow = rows[rows.length - 1];
        lastCreatedAt = lastRow.created_at;
        lastId = lastRow.id;
      }

      // Continue if we got a full page, otherwise we're done
      if (rows.length < pageSize) {
        hasMore = false;
      }
    }
  }

  console.log(
    `[Backfill Session Length] Done. processed=${totalProcessed}, updated=${totalUpdated}, skipped=${totalSkipped}, failed=${totalFailed}`
  );
}

if (require.main === module) {
  const specificEventId = process.argv[2]; // Get event ID from command line if provided
  backfillSessionLength(specificEventId).catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
