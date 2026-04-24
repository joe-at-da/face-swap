import { NextRequest, NextResponse } from "next/server";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

/**
 * API Route: POST /api/embeddings/batch-process
 * Processes queued embeddings in batches - called after RunPod bulk insertions
 * Requires CRON_SECRET authentication
 */
export async function POST(request: NextRequest) {
  try {
    // Verify CRON_SECRET authentication
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret) {
      console.error("[Batch Embeddings] CRON_SECRET not configured");
      return NextResponse.json(
        {
          success: false,
          error: "Server configuration error",
          timestamp: new Date().toISOString(),
        },
        { status: 500 }
      );
    }

    if (authHeader !== `Bearer ${cronSecret}`) {
      console.warn("[Batch Embeddings] Unauthorized batch process request");
      return NextResponse.json(
        {
          success: false,
          error: "Unauthorized",
          timestamp: new Date().toISOString(),
        },
        { status: 401 }
      );
    }

    // Parse request body (optional parameters)
    let body: {
      batch_size?: number;
      max_batches?: number;
      visibility_timeout?: number;
    } = {};

    try {
      const requestText = await request.text();
      if (requestText) {
        body = JSON.parse(requestText);
      }
    } catch (error) {
      console.error("[Batch Embeddings] Invalid JSON in request body:", error);
      // Continue with default values
    }

    const batchSize = Math.min(body.batch_size || 25, 50); // Max 50 per batch
    const maxBatches = Math.min(body.max_batches || 10, 20); // Max 20 batches per request
    const visibilityTimeout = Math.min(body.visibility_timeout || 300, 3600); // Max 1 hour

    let totalProcessed = 0;
    let totalSucceeded = 0;
    let totalFailed = 0;
    let remainingQueued = 0;
    let batchCount = 0;

    // Process multiple batches
    while (batchCount < maxBatches) {
      batchCount++;

      // Call the Supabase function to process a batch using PGMQ
      const { data, error } = await supabaseAdminClient.rpc(
        "process_embedding_queue",
        {
          batch_size: batchSize,
          visibility_timeout: visibilityTimeout,
        }
      );

      if (error) {
        console.error(
          `[Batch Embeddings] Error in batch ${batchCount}:`,
          error
        );
        return NextResponse.json(
          {
            success: false,
            error: `Batch processing failed: ${error.message}`,
            batches_completed: batchCount - 1,
            total_processed: totalProcessed,
            total_succeeded: totalSucceeded,
            total_failed: totalFailed,
            timestamp: new Date().toISOString(),
          },
          { status: 500 }
        );
      }

      const result = data[0];
      totalProcessed += result.processed_count;
      totalSucceeded += result.success_count;
      totalFailed += result.failed_count;
      remainingQueued = result.remaining_in_queue;

      if (result.remaining_in_queue === 0) {
        break;
      }

      // If this batch processed nothing, stop to avoid infinite loop
      if (result.processed_count === 0) {
        break;
      }

      // Small delay between batches to avoid overwhelming the API
      await new Promise((resolve) => setTimeout(resolve, 200));
    }

    return NextResponse.json({
      success: true,
      data: {
        batches_processed: batchCount,
        total_processed: totalProcessed,
        total_succeeded: totalSucceeded,
        total_failed: totalFailed,
        remaining_queued: remainingQueued,
        completion_percentage:
          totalProcessed > 0
            ? Math.round((totalSucceeded / totalProcessed) * 100)
            : 0,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[Batch Embeddings] Unexpected error:", error);

    return NextResponse.json(
      {
        success: false,
        error: "Batch embedding processing failed",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

/**
 * GET endpoint for health check and status
 */
export async function GET() {
  try {
    // Get PGMQ queue status
    const { data, error } = await supabaseAdminClient.rpc(
      "get_embedding_queue_status"
    );

    if (error) {
      console.error("[Batch Embeddings] Error checking queue status:", error);
      return NextResponse.json(
        {
          success: false,
          error: "Failed to check queue status",
          timestamp: new Date().toISOString(),
        },
        { status: 500 }
      );
    }

    const queueStats = data[0];
    const totalQueued = queueStats.queue_length;

    return NextResponse.json({
      success: true,
      message: "Batch Embedding Processing API is running",
      endpoint: "/api/embeddings/batch-process",
      method: "POST",
      auth: "Bearer CRON_SECRET",
      queue_status: {
        total_queued: totalQueued,
        pending_logs: queueStats.pending_logs_count,
        failed_logs: queueStats.failed_logs_count,
        success_logs: queueStats.success_logs_count,
        total_messages: queueStats.total_messages,
        oldest_msg_age_sec: queueStats.oldest_msg_age_sec,
      },
      parameters: {
        batch_size: "Optional: 1-50 (default: 10)",
        max_batches: "Optional: 1-20 (default: 10)",
        visibility_timeout:
          "Optional: Timeout in seconds for PGMQ visibility (default: 300)",
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[Batch Embeddings] Health check error:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Health check failed",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
