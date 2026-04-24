import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { ErrorLogger } from "@/lib/errorLogger";

/**
 * Process Embedding Queue - runs every minute
 * Coolify Scheduled Task: * * * * *
 */
export async function POST(request: NextRequest) {
  try {
    // Verify CRON_SECRET for security
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
      console.warn("[Process Embedding Queue] Unauthorized request");
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const supabase = await createSupabaseServerClient();

    // Call the embedding queue processing function
    const { data, error } = await supabase.rpc('process_embedding_queue', {
      batch_size: 100,
      visibility_timeout: 300
    });

    if (error) {
      console.error("[Process Embedding Queue] Function error:", error);
      return NextResponse.json({ 
        success: false, 
        error: error.message,
        timestamp: new Date().toISOString()
      }, { status: 500 });
    }

    const result = data[0];
    
    return NextResponse.json({ 
      success: true, 
      data: {
        processed_count: result.processed_count,
        success_count: result.success_count,
        failed_count: result.failed_count,
        remaining_in_queue: result.remaining_in_queue
      },
      message: result.processed_count > 0 
        ? `Processed ${result.processed_count} embedding jobs` 
        : "No embedding jobs to process",
      timestamp: new Date().toISOString() 
    });

  } catch (error) {
    console.error("[Process Embedding Queue] Error:", error);

    // Log to GlitchTip for error tracking
    ErrorLogger.logError(error, {
      component: "cron/process-embedding-queue",
      action: "process-embedding-queue-job",
      route: "/api/cron/process-embedding-queue",
    });

    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json({
      success: false,
      error: `Embedding queue processing failed: ${errorMessage}`,
      timestamp: new Date().toISOString()
    }, { status: 500 });
  }
}