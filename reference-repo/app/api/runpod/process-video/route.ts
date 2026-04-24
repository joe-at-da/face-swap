import { NextRequest, NextResponse } from "next/server";
import { RunPodService } from "@/services/runpod/runpod-service";
import { ProcessVideoRequest, ApiResponse } from "@/services/runpod/runpod-types";

/**
 * API Route: POST /api/runpod/process-video
 * Process a parliament video using RunPod's video processor
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
      console.warn("[RunPod API] Unauthorized process-video request");
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
    let body: ProcessVideoRequest;
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
    if (!body.parliament_event_id) {
      return NextResponse.json(
        {
          success: false,
          error: "parliament_event_id is required",
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 400 }
      );
    }

    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(body.parliament_event_id)) {
      return NextResponse.json(
        {
          success: false,
          error: "Invalid parliament_event_id format (must be UUID)",
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 400 }
      );
    }

    console.log(`[RunPod API] Processing video for parliament event: ${body.parliament_event_id}`);

    // Create service and process video
    const runPodService = new RunPodService();
    const result = await runPodService.processParliamentVideo(body.parliament_event_id);

    if (!result.success) {
      console.error(`[RunPod API] Video processing failed:`, result.error);
      return NextResponse.json(
        {
          success: false,
          error: result.error,
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 500 }
      );
    }

    console.log(`[RunPod API] Video processing completed successfully`);

    return NextResponse.json({
      success: true,
      data: { job_id: result.job_id },
      timestamp: new Date().toISOString(),
    } as ApiResponse);

  } catch (error) {
    console.error("[RunPod API] Process video error:", error);

    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Process video failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      } as ApiResponse,
      { status: 500 }
    );
  }
}

/**
 * GET endpoint for health check
 */
export async function GET() {
  return NextResponse.json({
    success: true,
    message: "RunPod Process Video API is running",
    endpoint: "/api/runpod/process-video",
    method: "POST",
    auth: "Bearer CRON_SECRET",
    timestamp: new Date().toISOString(),
  });
}