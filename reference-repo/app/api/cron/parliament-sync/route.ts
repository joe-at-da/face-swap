import { NextRequest, NextResponse } from "next/server";
import { ParliamentSyncService } from "@/services/parliament/parliament-sync-service";
import { ErrorLogger } from "@/lib/errorLogger";
import { SyncStatusRecord } from "@/services/parliament/parliament-api-types";

export async function POST(request: NextRequest) {
  try {
    // Verify this is a legitimate cron request
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET || "your-secret-key";

    if (authHeader !== `Bearer ${cronSecret}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const syncService = new ParliamentSyncService();

    // Get sync type from query params (optional)
    const { searchParams } = new URL(request.url);
    const syncType = searchParams.get("type");

    let result: { message?: string; status?: SyncStatusRecord[] };

    switch (syncType) {
      case "members":
        await syncService.syncMembers();
        result = { message: "Members sync completed" };
        break;

      case "contacts":
        await syncService.syncMemberContacts();
        result = { message: "Contacts sync completed" };
        break;

      case "portraits":
        await syncService.syncMemberPortraits();
        result = { message: "Portraits sync completed" };
        break;

      case "voting-history":
        // DISABLED: Voting history sync temporarily disabled
        // const limit = parseInt(searchParams.get("limit") || "10");
        // await syncService.syncMemberVotingHistory(limit);
        result = {
          message: "Voting history sync is currently disabled",
        };
        break;

      case "status": {
        const status = await syncService.getSyncStatus();
        result = { status: status as SyncStatusRecord[] };
        break;
      }

      default:
        // Full sync (excluding voting history - temporarily disabled)
        await syncService.syncAllData();
        result = { message: "Full sync completed (voting history disabled)" };
        break;
    }

    // After successful sync, trigger face encoder processing
    // This call blocks until face encoding completes (can take up to 10 minutes)
    let faceEncoderResult: { success: boolean; error?: string } = {
      success: false,
    };
    try {
      const baseUrl = process.env.VERCEL_URL
        ? `https://${process.env.VERCEL_URL}`
        : process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

      const response = await fetch(`${baseUrl}/api/runpod/encode-faces`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${cronSecret}`,
        },
        body: JSON.stringify({ detection_threshold: 0.65 }),
      });

      if (response.ok) {
        await response.json();
        faceEncoderResult = { success: true };
      } else {
        const errorText = await response.text();
        console.warn("Face encoder request failed:", response.status, errorText);
        faceEncoderResult = {
          success: false,
          error: `Face encoder failed: ${response.status}`,
        };
      }
    } catch (encoderError) {
      console.warn("Failed to run face encoder:", encoderError);
      faceEncoderResult = {
        success: false,
        error:
          encoderError instanceof Error
            ? encoderError.message
            : "Unknown error",
      };
      // Don't fail the main sync if face encoder fails
    }

    return NextResponse.json({
      success: true,
      timestamp: new Date().toISOString(),
      ...result,
      face_encoder: faceEncoderResult,
    });
  } catch (error) {
    console.error("Parliament sync failed:", error);

    // Log to GlitchTip for error tracking
    ErrorLogger.logError(error, {
      component: "cron/parliament-sync",
      action: "parliament-sync-job",
      route: "/api/cron/parliament-sync",
    });

    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

// GET endpoint to check sync status
export async function GET() {
  try {
    const syncService = new ParliamentSyncService();
    const status = await syncService.getSyncStatus();

    return NextResponse.json({
      success: true,
      status,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Failed to get sync status:", error);

    // Log to GlitchTip for error tracking
    ErrorLogger.logError(error, {
      component: "cron/parliament-sync",
      action: "get-sync-status",
      route: "/api/cron/parliament-sync",
    });

    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
