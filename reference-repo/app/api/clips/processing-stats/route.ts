import { NextResponse } from "next/server";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

/**
 * GET /api/clips/processing-stats
 * Returns average processing time for clips, excluding extreme 10% outliers
 */
export async function GET() {
  try {
    // Get average processing time excluding extreme 10% from both sides
    // Type assertion used because RPC function may not exist in generated types
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data, error } = await (supabaseAdminClient as any).rpc(
      "get_average_processing_time"
    );

    if (error) {
      // If RPC function doesn't exist, calculate it directly
      const { data: statsData, error: statsError } = await supabaseAdminClient
        .from("user_clips")
        .select("processing_time_total")
        .not("processing_time_total", "is", null)
        .order("processing_time_total");

      if (statsError || !statsData || statsData.length === 0) {
        console.error("Error fetching processing stats:", statsError);
        // Return a sensible default if no data
        return NextResponse.json({
          success: true,
          data: {
            average_processing_time_seconds: 60, // 1 minute default
            sample_size: 0,
          },
        });
      }

      // Calculate percentiles and average manually
      const values = statsData
        .map((row) => row.processing_time_total)
        .filter((val): val is number => val !== null);
      const p10Index = Math.floor(values.length * 0.1);
      const p90Index = Math.floor(values.length * 0.9);

      const filteredValues = values.slice(p10Index, p90Index + 1);
      const average =
        filteredValues.reduce((sum, val) => sum + val, 0) /
        filteredValues.length;

      return NextResponse.json({
        success: true,
        data: {
          average_processing_time_seconds: Math.round(average),
          sample_size: filteredValues.length,
        },
      });
    }

    return NextResponse.json({
      success: true,
      data: {
        average_processing_time_seconds: Math.round(data),
        sample_size: data?.sample_size || 0,
      },
    });
  } catch (error) {
    console.error("Processing stats API error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch processing stats: ${errorMessage}`,
      },
      { status: 500 }
    );
  }
}
