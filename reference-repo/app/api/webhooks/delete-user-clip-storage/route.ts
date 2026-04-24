import { NextRequest, NextResponse } from "next/server";
import { deleteVideoFromStorageByPath } from "@/lib/deleteVideoFromStorage";
import { ErrorLogger } from "@/lib/errorLogger";

/**
 * Webhook endpoint for deleting video files from storage when user_clips are deleted
 * Called directly by the Supabase AFTER DELETE trigger
 *
 * NOTE: This endpoint does not require authentication as it is only accessible
 * internally via database triggers, not exposed to external clients.
 */
export async function POST(request: NextRequest) {
  try {
    // Parse request body
    let body: {
      userId?: string;
      clipId?: string;
    };

    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { userId, clipId } = body;

    // Validate required parameters
    if (!userId || !clipId) {
      return NextResponse.json(
        { error: "Missing userId or clipId in request body" },
        { status: 400 }
      );
    }

    console.log(`[Storage Deletion] Starting deletion for user ${userId}, clip ${clipId}`);

    // Delete video files from storage directory: user_clips/{userId}/{clipId}/
    const result = await deleteVideoFromStorageByPath(userId, clipId);

    if (!result.success) {
      console.error(`[Storage Deletion] Failed for user ${userId}, clip ${clipId}:`, result.errors);

      ErrorLogger.logError(
        new Error(`Storage deletion failed for user ${userId}, clip ${clipId}`),
        {
          action: "delete-user-clip-storage",
          route: "/api/webhooks/delete-user-clip-storage",
          additionalContext: {
            userId,
            clipId,
            errors: result.errors,
            failedFiles: result.failedFiles,
          },
        }
      );

      return NextResponse.json(
        {
          success: false,
          error: "Failed to delete some files from storage",
          details: {
            deletedFiles: result.deletedFiles,
            failedFiles: result.failedFiles,
            errors: result.errors,
          },
        },
        { status: 500 }
      );
    }

    console.log(
      `[Storage Deletion] Successfully deleted ${result.deletedFiles.length} file(s) for user ${userId}, clip ${clipId}:`,
      result.deletedFiles
    );

    // Log successful deletion
    ErrorLogger.logEvent("Storage files deleted successfully", {
      action: "delete-user-clip-storage",
      route: "/api/webhooks/delete-user-clip-storage",
      additionalContext: {
        userId,
        clipId,
        deletedFiles: result.deletedFiles,
        filesCount: result.deletedFiles.length,
      },
    });

    return NextResponse.json({
      success: true,
      message: "Video files deleted successfully",
      details: {
        deletedFiles: result.deletedFiles,
        filesCount: result.deletedFiles.length,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[Storage Deletion] Webhook error:", error);

    ErrorLogger.logError(
      error instanceof Error ? error : new Error("Unknown error"),
      {
        action: "delete-user-clip-storage",
        route: "/api/webhooks/delete-user-clip-storage",
      }
    );

    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to delete video files: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
