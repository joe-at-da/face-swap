import { NextRequest, NextResponse } from "next/server";

interface RetryQueueStats {
  queue_length: number;
  oldest_msg_age_sec: number | null;
  newest_msg_age_sec: number | null;
  total_messages: number;
  pending_retries: number;
  failed_after_retries: number;
  success_after_retries: number;
}

interface RetryQueueHealth {
  status: "idle" | "normal" | "high_load" | "critical";
  backlog_age_minutes: number;
  retry_success_rate: number;
  permanent_failure_rate: number;
  pending_retries: number;
}

/**
 * API Route: GET /api/runpod/retry-status
 * Returns detailed status of the RunPod retry queue and statistics
 */
export async function GET() {
  try {
    // TODO: Implement get_runpod_retry_status function
    // For now, return placeholder data
    console.log(
      "[RunPod Retry Status] Function not yet implemented, returning placeholder data"
    );

    const retryStats: RetryQueueStats = {
      queue_length: 0,
      oldest_msg_age_sec: null,
      newest_msg_age_sec: null,
      total_messages: 0,
      pending_retries: 0,
      failed_after_retries: 0,
      success_after_retries: 0,
    };

    // Calculate retry health metrics
    const retryHealth: RetryQueueHealth = {
      status: getQueueHealthStatus(retryStats),
      backlog_age_minutes: retryStats.oldest_msg_age_sec
        ? Math.round(retryStats.oldest_msg_age_sec / 60)
        : 0,
      retry_success_rate: calculateRetrySuccessRate(retryStats),
      permanent_failure_rate: calculatePermanentFailureRate(retryStats),
      pending_retries: retryStats.pending_retries || 0,
    };

    return NextResponse.json({
      success: true,
      data: {
        queue_metrics: {
          current_length: retryStats.queue_length,
          total_messages_processed: retryStats.total_messages,
          oldest_message_age_seconds: retryStats.oldest_msg_age_sec,
          newest_message_age_seconds: retryStats.newest_msg_age_sec,
        },
        retry_metrics_24h: {
          pending_retries: retryStats.pending_retries,
          successful_retries: retryStats.success_after_retries,
          permanent_failures: retryStats.failed_after_retries,
          total_retry_jobs:
            retryStats.pending_retries +
            retryStats.success_after_retries +
            retryStats.failed_after_retries,
        },
        health: retryHealth,
        recommendations: getRetryRecommendations(retryStats, retryHealth),
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[RunPod Retry Status] Unexpected error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Retry status check failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

/**
 * POST endpoint for manual retry operations (admin only)
 */
export async function POST(request: NextRequest) {
  try {
    // Verify CRON_SECRET authentication for admin operations
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret) {
      console.error("[RunPod Retry Status] CRON_SECRET not configured");
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
      console.warn(
        "[RunPod Retry Status] Unauthorized retry operation request"
      );
      return NextResponse.json(
        {
          success: false,
          error: "Unauthorized",
          timestamp: new Date().toISOString(),
        },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { action } = body;

    if (action === "process_retries") {
      // TODO: Implement process_runpod_retry_queue function
      // For now, return placeholder response
      console.log(
        "[RunPod Retry Status] Manual retry processing not yet implemented"
      );

      return NextResponse.json({
        success: true,
        action: "process_retries",
        data: {
          processed_count: 0,
          success_count: 0,
          failed_count: 0,
          permanent_failures: 0,
          remaining_in_queue: 0,
        },
        message: "Manual retry processing not yet implemented",
        timestamp: new Date().toISOString(),
      });
    }

    return NextResponse.json(
      {
        success: false,
        error: `Unknown action: ${action}`,
        available_actions: ["process_retries"],
        timestamp: new Date().toISOString(),
      },
      { status: 400 }
    );
  } catch (error) {
    console.error("[RunPod Retry Status] POST error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Retry operation failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

/**
 * Determine queue health status based on metrics
 */
function getQueueHealthStatus(
  stats: RetryQueueStats
): "idle" | "normal" | "high_load" | "critical" {
  if (stats.queue_length === 0 && stats.pending_retries === 0) {
    return "idle";
  }

  if (stats.queue_length > 50 || stats.pending_retries > 100) {
    return "critical";
  }

  if (stats.queue_length > 10 || stats.pending_retries > 20) {
    return "high_load";
  }

  return "normal";
}

/**
 * Calculate retry success rate
 */
function calculateRetrySuccessRate(stats: RetryQueueStats): number {
  const totalCompleted =
    stats.success_after_retries + stats.failed_after_retries;
  if (totalCompleted === 0) return 100;

  return Math.round((stats.success_after_retries / totalCompleted) * 100);
}

/**
 * Calculate permanent failure rate
 */
function calculatePermanentFailureRate(stats: RetryQueueStats): number {
  const totalAttempts =
    stats.success_after_retries +
    stats.failed_after_retries +
    stats.pending_retries;
  if (totalAttempts === 0) return 0;

  return Math.round((stats.failed_after_retries / totalAttempts) * 100);
}

/**
 * Generate recommendations based on retry status
 */
function getRetryRecommendations(
  retryStats: RetryQueueStats,
  health: RetryQueueHealth
): string[] {
  const recommendations: string[] = [];

  if (health.status === "critical") {
    recommendations.push(
      "Critical: High number of pending retries - investigate RunPod API issues"
    );
  }

  if (health.status === "high_load") {
    recommendations.push(
      "High retry load detected - monitor RunPod service health"
    );
  }

  if (health.backlog_age_minutes > 30) {
    recommendations.push(
      `Oldest retry is ${health.backlog_age_minutes} minutes old - check retry processing`
    );
  }

  if (health.permanent_failure_rate > 20) {
    recommendations.push(
      `High permanent failure rate (${health.permanent_failure_rate}%) - review job requests and RunPod configuration`
    );
  }

  if (
    health.retry_success_rate < 70 &&
    retryStats.success_after_retries + retryStats.failed_after_retries > 0
  ) {
    recommendations.push(
      `Low retry success rate (${health.retry_success_rate}%) - investigate RunPod API reliability`
    );
  }

  if (
    retryStats.queue_length === 0 &&
    retryStats.pending_retries === 0 &&
    retryStats.success_after_retries === 0
  ) {
    recommendations.push("No retry activity - system is idle");
  }

  if (recommendations.length === 0) {
    recommendations.push("Retry system is operating normally");
  }

  return recommendations;
}
