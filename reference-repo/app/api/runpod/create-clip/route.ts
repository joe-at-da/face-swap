import { NextRequest, NextResponse } from "next/server";
import { RunPodService } from "@/services/runpod/runpod-service";
import { CreateClipRequest, ApiResponse } from "@/services/runpod/runpod-types";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";

/**
 * API Route: POST /api/runpod/create-clip
 * Create a user clip using RunPod's clip creator
 * Supports automatic retry mechanism with max 3 attempts
 * Requires CRON_SECRET authentication
 */
export async function POST(request: NextRequest) {
  try {
    // Verify CRON_SECRET authentication
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret) {
      console.error("[RunPod API] CRON_SECRET not configured");
      return NextResponse.json(
        {
          success: false,
          error: "Server configuration error",
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 500 }
      );
    }

    if (authHeader !== `Bearer ${cronSecret}`) {
      console.warn("[RunPod API] Unauthorized create-clip request");
      return NextResponse.json(
        {
          success: false,
          error: "Unauthorized",
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 401 }
      );
    }

    // Parse request body
    let body: CreateClipRequest;
    try {
      body = await request.json();
    } catch (error) {
      console.error("[RunPod API] Invalid JSON in request body:", error);
      return NextResponse.json(
        {
          success: false,
          error: "Invalid JSON in request body",
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 400 }
      );
    }

    // Validate request
    if (!body.user_clip_id) {
      return NextResponse.json(
        {
          success: false,
          error: "user_clip_id is required",
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 400 }
      );
    }

    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(body.user_clip_id)) {
      return NextResponse.json(
        {
          success: false,
          error: "Invalid user_clip_id format (must be UUID)",
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 400 }
      );
    }

    console.log(`[RunPod API] Submitting clip creation job for user clip: ${body.user_clip_id}`);

    // Get current retry count by counting failed attempts
    const supabase = await createSupabaseServerClient();
    const { data: retryData } = await supabase
      .from('runpod_processing_logs')
      .select('status')
      .eq('table_name', 'user_clips')
      .eq('record_id', body.user_clip_id)
      .eq('endpoint', '/api/runpod/create-clip')
      .eq('status', 'failed');

    const currentRetryCount = retryData?.length || 0;
    const maxRetries = 3;

    // Check if we've exceeded max retries
    if (currentRetryCount >= maxRetries) {
      console.warn(`[RunPod API] Max retries (${maxRetries}) exceeded for clip: ${body.user_clip_id}`);
      return NextResponse.json(
        {
          success: false,
          error: `Max retries (${maxRetries}) exceeded`,
          retry_count: currentRetryCount,
          max_retries: maxRetries,
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 429 } // Too Many Requests
      );
    }

    // Create service and submit clip creation to queue (async)
    const runPodService = new RunPodService();
    const result = await runPodService.createUserClip(body.user_clip_id);

    if (!result.success) {
      console.error(`[RunPod API] Clip creation submission failed (attempt ${currentRetryCount + 1}):`, result.error);

      // Determine if we should queue for retry
      const shouldRetry = shouldQueueRetry(result.error, currentRetryCount, maxRetries);

      if (shouldRetry) {
        // Queue for retry (this will be handled by the database trigger)
        console.log(`[RunPod API] Queuing for retry (attempt ${currentRetryCount + 1}/${maxRetries})`);

        return NextResponse.json(
          {
            success: false,
            error: result.error,
            queued_for_retry: true,
            retry_count: currentRetryCount,
            max_retries: maxRetries,
            next_retry_in_minutes: 10,
            timestamp: new Date().toISOString(),
          } as ApiResponse,
          { status: 503 } // Service Unavailable - will retry
        );
      } else {
        // Don't retry - permanent failure
        console.log(`[RunPod API] Permanent failure - not retrying: ${result.error}`);

        return NextResponse.json(
          {
            success: false,
            error: result.error,
            permanent_failure: true,
            retry_count: currentRetryCount,
            timestamp: new Date().toISOString(),
          } as ApiResponse,
          { status: 400 } // Bad Request - permanent failure
        );
      }
    }

    console.log(`[RunPod API] Clip creation job submitted: ${result.job_id}`);

    return NextResponse.json({
      success: true,
      data: {
        job_id: result.job_id,
        user_clip_id: body.user_clip_id,
        status: "IN_QUEUE",
      },
      retry_count: currentRetryCount,
      timestamp: new Date().toISOString(),
    } as ApiResponse);

  } catch (error) {
    console.error("[RunPod API] Create clip error:", error);

    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Create clip failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      } as ApiResponse,
      { status: 500 }
    );
  }
}

/**
 * Determine if a failed job should be queued for retry
 */
function shouldQueueRetry(error: string | undefined, currentRetryCount: number, maxRetries: number): boolean {
  // Don't retry if we've hit max retries
  if (currentRetryCount >= maxRetries) {
    return false;
  }

  if (!error) {
    return true; // Unknown error - retry
  }

  const errorLower = error.toLowerCase();

  // Don't retry for client errors (4xx equivalent)
  if (
    errorLower.includes('invalid') ||
    errorLower.includes('malformed') ||
    errorLower.includes('bad request') ||
    errorLower.includes('unauthorized') ||
    errorLower.includes('forbidden') ||
    errorLower.includes('not found') ||
    errorLower.includes('user_clip_id') ||
    errorLower.includes('uuid') ||
    errorLower.includes('not configured')
  ) {
    return false;
  }

  // Retry for server errors (5xx equivalent), network issues, and RunPod queue errors
  if (
    errorLower.includes('timeout') ||
    errorLower.includes('network') ||
    errorLower.includes('connection') ||
    errorLower.includes('server error') ||
    errorLower.includes('internal') ||
    errorLower.includes('service unavailable') ||
    errorLower.includes('bad gateway') ||
    errorLower.includes('gateway timeout') ||
    errorLower.includes('runpod') // RunPod service issues
  ) {
    return true;
  }

  // Default: retry unknown errors
  return true;
}

/**
 * GET endpoint for health check
 */
export async function GET() {
  return NextResponse.json({
    success: true,
    message: "RunPod Create Clip API is running (queue mode)",
    endpoint: "/api/runpod/create-clip",
    method: "POST",
    auth: "Bearer CRON_SECRET",
    mode: "serverless_queue",
    runpod_endpoint: "/run",
    description: "Submits clip creation job to RunPod serverless queue. Returns job_id for tracking.",
    route_retry_system: {
      max_retries: 3,
      retry_delay_minutes: 10,
      automatic_queue: true,
    },
    response: {
      job_id: "RunPod job ID for status tracking",
      status: "IN_QUEUE (initial status)",
    },
    timestamp: new Date().toISOString(),
  });
}