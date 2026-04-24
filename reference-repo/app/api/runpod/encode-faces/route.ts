import { NextRequest, NextResponse } from "next/server";
import { RunPodService } from "@/services/runpod/runpod-service";
import { ApiResponse } from "@/services/runpod/runpod-types";

// Request body interface for encode-faces endpoint
interface EncodeFacesRequestBody {
  detection_threshold?: number; // Default: 0.65
}

/**
 * API Route: POST /api/runpod/encode-faces
 * Process face encodings using RunPod's face encoder load-balancing endpoint
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
      console.warn("[RunPod API] Unauthorized encode-faces request");
      return NextResponse.json(
        {
          success: false,
          error: "Unauthorized",
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 401 }
      );
    }

    // Parse request body (optional parameters)
    let body: EncodeFacesRequestBody = {};
    try {
      const requestBody = await request.text();
      if (requestBody.trim()) {
        body = JSON.parse(requestBody);
      }
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

    // Validate detection_threshold parameter (default: 0.65)
    const detectionThreshold = body.detection_threshold ?? 0.65;
    if (
      typeof detectionThreshold !== "number" ||
      detectionThreshold < 0 ||
      detectionThreshold > 1
    ) {
      return NextResponse.json(
        {
          success: false,
          error: "detection_threshold must be a number between 0 and 1",
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 400 }
      );
    }

    console.log(
      `[RunPod API] Submitting face encodings job with detection_threshold: ${detectionThreshold}`
    );

    // Create service and submit face encodings to queue (async)
    const runPodService = new RunPodService();
    const result = await runPodService.processFaceEncodings(detectionThreshold);

    if (!result.success) {
      console.error(`[RunPod API] Face encoding submission failed:`, result.error);
      return NextResponse.json(
        {
          success: false,
          error: result.error,
          timestamp: new Date().toISOString(),
        } as ApiResponse,
        { status: 500 }
      );
    }

    console.log(`[RunPod API] Face encoding job submitted: ${result.job_id}`);

    return NextResponse.json({
      success: true,
      data: {
        job_id: result.job_id,
        detection_threshold: detectionThreshold,
        status: "IN_QUEUE",
      },
      timestamp: new Date().toISOString(),
    } as ApiResponse);

  } catch (error) {
    console.error("[RunPod API] Encode faces error:", error);

    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Encode faces failed: ${errorMessage}`,
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
    message: "RunPod Encode Faces API is running (queue mode)",
    endpoint: "/api/runpod/encode-faces",
    method: "POST",
    auth: "Bearer CRON_SECRET",
    mode: "serverless_queue",
    runpod_endpoint: "/run",
    description: "Submits face encoding job to RunPod serverless queue. Returns job_id for tracking.",
    parameters: {
      detection_threshold: "optional number (0-1, default: 0.65)",
    },
    response: {
      job_id: "RunPod job ID for status tracking",
      status: "IN_QUEUE (initial status)",
    },
    timestamp: new Date().toISOString(),
  });
}