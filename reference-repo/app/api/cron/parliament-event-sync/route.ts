import { NextRequest, NextResponse } from "next/server";
import { ParliamentEventSyncService } from "@/services/parliament/parliament-event-sync-service";
import { ErrorLogger } from "@/lib/errorLogger";

/**
 * Parliament Event Daily Sync - runs daily at 3:30 AM UTC
 * Coolify Scheduled Task: 30 3 * * *
 *
 * Syncs parliament events from the RSS/Atom feed
 */
export async function POST(request: NextRequest) {
  try {
    // Verify CRON_SECRET for security
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
      console.warn("[Parliament Event Sync] Unauthorized request");
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    console.log(
      "[Parliament Event Sync] Starting daily parliament event sync..."
    );

    // Call the parliament event sync service directly
    const syncService = new ParliamentEventSyncService();
    const result = await syncService.syncEvents();

    console.log("[Parliament Event Sync] Success:", result);
    return NextResponse.json({
      success: true,
      data: result,
      message: "Parliament event sync completed successfully",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[Parliament Event Sync] Error:", error);

    // Log to GlitchTip for error tracking
    ErrorLogger.logError(error, {
      component: "cron/parliament-event-sync",
      action: "parliament-event-sync-job",
      route: "/api/cron/parliament-event-sync",
    });

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Parliament event sync failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
