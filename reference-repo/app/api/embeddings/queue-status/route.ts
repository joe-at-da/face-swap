import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { Database } from "@/supabaseTypes";

type QueueStats = Database["public"]["Functions"]["get_embedding_queue_status"]["Returns"][0];

interface QueueHealth {
  status: 'idle' | 'normal' | 'high_load';
  backlog_age_minutes: number;
  processing_rate_24h: number;
  error_rate_24h: number;
  success_rate_percentage: number;
}

/**
 * API Route: GET /api/embeddings/queue-status
 * Returns detailed status of the PGMQ embedding queue
 */
export async function GET() {
  try {
    const supabase = await createSupabaseServerClient();

    // Get comprehensive queue status
    const { data, error } = await supabase.rpc('get_embedding_queue_status');

    if (error) {
      console.error("[Queue Status] Error fetching queue metrics:", error);
      return NextResponse.json(
        {
          success: false,
          error: "Failed to fetch queue status",
          timestamp: new Date().toISOString(),
        },
        { status: 500 }
      );
    }

    if (!data || data.length === 0) {
      return NextResponse.json(
        {
          success: false,
          error: "No queue status data returned",
          timestamp: new Date().toISOString(),
        },
        { status: 500 }
      );
    }

    const queueStats: QueueStats = data[0];

    // Calculate queue health metrics
    const queueHealth: QueueHealth = {
      status: queueStats.queue_length === 0 ? 'idle' : queueStats.queue_length < 100 ? 'normal' : 'high_load',
      backlog_age_minutes: queueStats.oldest_msg_age_sec ? Math.round(queueStats.oldest_msg_age_sec / 60) : 0,
      processing_rate_24h: queueStats.success_logs_count || 0,
      error_rate_24h: queueStats.failed_logs_count || 0,
      success_rate_percentage: queueStats.success_logs_count + queueStats.failed_logs_count > 0 
        ? Math.round((queueStats.success_logs_count / (queueStats.success_logs_count + queueStats.failed_logs_count)) * 100)
        : 100
    };

    return NextResponse.json({
      success: true,
      data: {
        queue_metrics: {
          current_length: queueStats.queue_length,
          total_messages_processed: queueStats.total_messages,
          oldest_message_age_seconds: queueStats.oldest_msg_age_sec,
          newest_message_age_seconds: queueStats.newest_msg_age_sec,
        },
        log_metrics_24h: {
          pending_jobs: queueStats.pending_logs_count,
          successful_jobs: queueStats.success_logs_count,
          failed_jobs: queueStats.failed_logs_count,
          total_jobs: queueStats.pending_logs_count + queueStats.success_logs_count + queueStats.failed_logs_count
        },
        health: queueHealth,
        recommendations: getRecommendations(queueStats, queueHealth)
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("[Queue Status] Unexpected error:", error);
    
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    
    return NextResponse.json(
      {
        success: false,
        error: `Queue status check failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

/**
 * Generate recommendations based on queue status
 */
function getRecommendations(queueStats: QueueStats, health: QueueHealth): string[] {
  const recommendations: string[] = [];

  if (health.status === 'high_load') {
    recommendations.push("Queue has high backlog - consider increasing batch processing frequency");
  }

  if (health.backlog_age_minutes > 10) {
    recommendations.push(`Oldest message is ${health.backlog_age_minutes} minutes old - check processing pipeline`);
  }

  if (health.error_rate_24h > health.processing_rate_24h * 0.1) {
    recommendations.push("High error rate detected - review failed job logs for common issues");
  }

  if (health.success_rate_percentage < 90) {
    recommendations.push(`Success rate is ${health.success_rate_percentage}% - investigate embedding API connectivity`);
  }

  if (queueStats.queue_length === 0 && queueStats.success_logs_count === 0) {
    recommendations.push("No recent activity - verify trigger function is working for new clips");
  }

  if (recommendations.length === 0) {
    recommendations.push("Queue is operating normally");
  }

  return recommendations;
}

/**
 * POST endpoint for manual queue operations (admin only)
 */
export async function POST(request: NextRequest) {
  try {
    // Verify CRON_SECRET authentication for admin operations
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret) {
      console.error("[Queue Status] CRON_SECRET not configured");
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
      console.warn("[Queue Status] Unauthorized queue operation request");
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
    const { action, table_name, limit } = body;

    const supabase = await createSupabaseServerClient();

    if (action === 'queue_missing_embeddings') {
      // Manually queue clips that are missing embeddings
      const { data, error } = await supabase.rpc('queue_missing_embeddings', {
        table_name_param: table_name || 'parliament_member_clips',
        limit_param: limit || 100
      });

      if (error) {
        console.error("[Queue Status] Error queuing missing embeddings:", error);
        return NextResponse.json(
          {
            success: false,
            error: `Failed to queue missing embeddings: ${error.message}`,
            timestamp: new Date().toISOString(),
          },
          { status: 500 }
        );
      }

      if (!data || !Array.isArray(data) || data.length === 0) {
        return NextResponse.json(
          {
            success: false,
            error: "No data returned from queue function",
            timestamp: new Date().toISOString(),
          },
          { status: 500 }
        );
      }

      type QueueMissingEmbeddingsResult = Database["public"]["Functions"]["queue_missing_embeddings"]["Returns"][0];
      const result: QueueMissingEmbeddingsResult = data[0];
      return NextResponse.json({
        success: true,
        action: 'queue_missing_embeddings',
        data: {
          clips_found: result.clips_found,
          clips_queued: result.clips_queued
        },
        timestamp: new Date().toISOString(),
      });
    }

    return NextResponse.json(
      {
        success: false,
        error: `Unknown action: ${action}`,
        available_actions: ['queue_missing_embeddings'],
        timestamp: new Date().toISOString(),
      },
      { status: 400 }
    );

  } catch (error) {
    console.error("[Queue Status] POST error:", error);
    
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    
    return NextResponse.json(
      {
        success: false,
        error: `Queue operation failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}