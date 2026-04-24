import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

export async function GET(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Parse query parameters
    const searchParams = request.nextUrl.searchParams;
    const limit = parseInt(searchParams.get("limit") || "10");

    // Get user's member_id from user_roles
    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select(`
        member_id,
        parliament_members(display_name)
      `)
      .eq("user_id", user.id)
      .single();

    if (userRoleError) {
      console.error("Error fetching user role:", userRoleError);
      return NextResponse.json(
        { error: "Failed to fetch user data" },
        { status: 500 }
      );
    }

    // Check if user follows an MP
    const hasFollowedMP = userRole?.member_id != null;

    // User's created clips (last 30 days) - only personal clips (no team_id)
    const userClipsQuery = supabaseAdminClient
      .from("user_clips")
      .select(`
        id,
        created_at,
        updated_at,
        status,
        parliament_member_clips!inner(
          parliament_members!inner(display_name)
        )
      `)
      .eq("user_id", user.id)
      .is("team_id", null)
      .eq("is_deleted", false)
      .gte("created_at", new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString())
      .order("created_at", { ascending: false })
      .limit(limit);

    // MP clips query (only if user follows an MP)
    const mpClipsQuery = hasFollowedMP
      ? supabaseAdminClient
          .from("parliament_member_clips")
          .select(`
            id,
            created_at,
            parliament_members!inner(display_name)
          `)
          .eq("member_id", userRole.member_id!)
          .eq("is_deleted", false)
          .gte("created_at", new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString())
          .order("created_at", { ascending: false })
          .limit(limit)
      : null;

    // Fetch recent activity from multiple sources
    const [userClipsResult, mpClipsResult] = await Promise.allSettled([
      userClipsQuery,
      ...(mpClipsQuery ? [mpClipsQuery] : []),
    ]);

    const userClips = userClipsResult?.status === 'fulfilled' ? userClipsResult.value.data || [] : [];
    const mpClips = hasFollowedMP && mpClipsResult?.status === 'fulfilled' ? mpClipsResult.value.data || [] : [];

    // Transform user clips into activity items
    const userClipActivities = userClips.map((clip: {
      id: string;
      created_at: string | null;
      status: string | null;
      parliament_member_clips: {
        parliament_members: {
          display_name: string | null;
        };
      };
    }) => ({
      id: `user-clip-${clip.id}`,
      type: "clip_created",
      title: "Created new clip",
      description: `From ${clip.parliament_member_clips.parliament_members.display_name || "Unknown MP"}`,
      time: clip.created_at || new Date().toISOString(),
      status: clip.status || "unknown",
      metadata: {
        clip_id: clip.id,
        mp_name: clip.parliament_member_clips.parliament_members.display_name || "Unknown MP",
        user_created: true,
      }
    }));

    // Transform MP clips into activity items
    const mpClipActivities = mpClips.map((clip: {
      id: string;
      created_at: string | null;
      parliament_members: {
        display_name: string | null;
      };
    }) => ({
      id: `mp-clip-${clip.id}`,
      type: "new_mp_clip",
      title: "New clip available",
      description: `${clip.parliament_members.display_name || "Unknown MP"} spoke in Parliament`,
      time: clip.created_at || new Date().toISOString(),
      status: "available",
      metadata: {
        clip_id: clip.id,
        mp_name: clip.parliament_members.display_name || "Unknown MP",
        source_clip: true,
      }
    }));

    // Add some mock social media activities
    const mockSocialActivities = userClips
      .filter((clip: {
        status: string | null;
        updated_at: string | null;
        id: string;
      }) => clip.status === 'completed')
      .slice(0, 3)
      .map((clip: {
        id: string;
        updated_at: string | null;
      }, index: number) => ({
        id: `social-${clip.id}-${index}`,
        type: "social_scheduled",
        title: "Clip shared to social media",
        description: `Scheduled post for ${["Facebook", "Twitter", "Instagram"][index % 3]} (Demo)`,
        time: new Date(new Date(clip.updated_at || new Date()).getTime() + 60000).toISOString(), // 1 minute after clip completion
        status: "scheduled",
        metadata: {
          platform: ["Facebook", "Twitter", "Instagram"][index % 3],
          clip_id: clip.id,
          mock: true,
        }
      }));

    // Combine and sort all activities
    const allActivities = [
      ...userClipActivities,
      ...mpClipActivities,
      ...mockSocialActivities,
    ]
      .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
      .slice(0, limit);

    // Add some system notifications
    if (allActivities.length < limit) {
      const systemActivities = [
        {
          id: "system-welcome",
          type: "system_notification",
          title: "Welcome to Parliament Connect!",
          description: hasFollowedMP && userRole.parliament_members
            ? `You're now following ${userRole.parliament_members.display_name}`
            : "Get started by following an MP to see their parliamentary activity",
          time: user.created_at,
          status: "info",
          metadata: {
            system: true,
          } as Record<string, unknown>
        }
      ];

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (allActivities as any).push(...systemActivities);
    }

    return NextResponse.json({
      success: true,
      data: allActivities,
      metadata: {
        user_clips_count: userClips.length,
        mp_clips_count: mpClips.length,
        social_activities_count: mockSocialActivities.length,
        followed_mp: hasFollowedMP && userRole.parliament_members
          ? userRole.parliament_members.display_name
          : null,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Dashboard activity error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch dashboard activity: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}