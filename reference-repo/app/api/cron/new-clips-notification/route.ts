import { NextRequest, NextResponse } from "next/server";
import { createElement } from "react";
import { render } from "@react-email/components";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { ErrorLogger } from "@/lib/errorLogger";
import { sendHtmlEmail } from "@/lib/mailjet";
import { sleep } from "@/lib/sleep";
import {
  generateClipTitle,
  type MemberInfo,
} from "@/services/ai/generation-service";
import { NewContentAddedEmail } from "@/emails/new-content-added";
import type { ClipData } from "@/emails/_components/types";
import { formatDuration } from "@/lib/formatDuration";

const PLACEHOLDER_THUMBNAIL =
  "https://placehold.co/600x340/1c1a46/ffffff?text=Parliament+Connect";
const AI_DELAY_MS = 100;
const EMAIL_DELAY_MS = 200;

interface UnnotifiedClip {
  id: string;
  member_id: number;
  description: string;
  transcript: string;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  session_date: string | null;
}

interface EligibleUser {
  user_id: string;
  email: string;
}

function generateFallbackTitle(description: string): {
  title: string;
  remainingDescription: string;
} {
  const words = description.split(" ");
  if (words.length <= 8) {
    return { title: description, remainingDescription: "" };
  }
  const titleWords = words.slice(0, 8);
  const remainingWords = words.slice(8);
  return {
    title: titleWords.join(" ") + "...",
    remainingDescription: remainingWords.join(" "),
  };
}


async function getUnnotifiedClips(): Promise<UnnotifiedClip[]> {
  const { data, error } = await supabaseAdminClient
    .from("parliament_member_clips")
    .select(
      "id, member_id, description, transcript, thumbnail_url, duration_seconds, session_date"
    )
    .is("notification_sent_at", null)
    .not("description", "is", null)
    .eq("is_deleted", false)
    .order("created_at", { ascending: true });

  if (error) {
    throw new Error(`Failed to fetch unnotified clips: ${error.message}`);
  }

  return (data || []) as UnnotifiedClip[];
}

async function getMemberInfo(memberId: number): Promise<MemberInfo | null> {
  const { data, error } = await supabaseAdminClient
    .from("parliament_members")
    .select("display_name, party_abbreviation, constituency_name")
    .eq("member_id", memberId)
    .single();

  if (error) {
    // PGRST116 = row not found — member genuinely doesn't exist
    if (error.code === "PGRST116") return null;
    // Any other error is transient — let it bubble up so clips aren't marked prematurely
    throw new Error(`Failed to fetch member info for ${memberId}: ${error.message}`);
  }
  return data as MemberInfo;
}

async function getEligibleUsers(memberId: number): Promise<EligibleUser[]> {
  const userMap = new Map<string, EligibleUser>();

  // 1. Direct users: user_roles.member_id = memberId AND new_clips_available = true
  const { data: directUsers, error: directError } = await supabaseAdminClient
    .from("user_roles")
    .select("user_id, email")
    .eq("member_id", memberId)
    .eq("new_clips_available", true);

  if (directError) {
    throw new Error(`Failed to query direct users for member ${memberId}: ${directError.message}`);
  }

  for (const user of directUsers || []) {
    userMap.set(user.user_id, { user_id: user.user_id, email: user.email });
  }

  // 2. Find all user_ids whose member_id matches (owners of relevant teams)
  const { data: mpOwners, error: ownersError } = await supabaseAdminClient
    .from("user_roles")
    .select("user_id")
    .eq("member_id", memberId);

  if (ownersError) {
    throw new Error(`Failed to query MP owners for member ${memberId}: ${ownersError.message}`);
  }

  const ownerUserIds = (mpOwners || []).map((o) => o.user_id);

  if (ownerUserIds.length === 0) return Array.from(userMap.values());

  // 3. Find teams owned by these users
  const { data: teams, error: teamsError } = await supabaseAdminClient
    .from("teams")
    .select("id")
    .in("owner_id", ownerUserIds)
    .eq("is_deleted", false);

  if (teamsError) {
    throw new Error(`Failed to query teams for member ${memberId}: ${teamsError.message}`);
  }

  const teamIds = (teams || []).map((t) => t.id);

  if (teamIds.length === 0) return Array.from(userMap.values());

  // 4. Get team members
  const { data: teamMembers, error: membersError } = await supabaseAdminClient
    .from("team_members")
    .select("user_id")
    .in("team_id", teamIds);

  if (membersError) {
    throw new Error(`Failed to query team members for member ${memberId}: ${membersError.message}`);
  }

  const teamMemberUserIds = (teamMembers || []).map((m) => m.user_id);

  if (teamMemberUserIds.length === 0) return Array.from(userMap.values());

  // 5. Check their notification preferences
  const { data: eligibleTeamUsers, error: prefError } = await supabaseAdminClient
    .from("user_roles")
    .select("user_id, email")
    .in("user_id", teamMemberUserIds)
    .eq("new_clips_available", true);

  if (prefError) {
    throw new Error(`Failed to query team user preferences for member ${memberId}: ${prefError.message}`);
  }

  for (const user of eligibleTeamUsers || []) {
    userMap.set(user.user_id, { user_id: user.user_id, email: user.email });
  }

  return Array.from(userMap.values());
}

async function filterAlreadyNotifiedUsers(
  clipIds: string[],
  users: EligibleUser[]
): Promise<EligibleUser[]> {
  if (users.length === 0 || clipIds.length === 0) return users;

  const { data: existingLogs, error } = await supabaseAdminClient
    .from("clip_notification_log")
    .select("user_id, clip_id")
    .in("clip_id", clipIds)
    .in(
      "user_id",
      users.map((u) => u.user_id)
    );

  if (error) {
    throw new Error(`Failed to query notification log: ${error.message}`);
  }

  if (!existingLogs || existingLogs.length === 0) return users;

  // A user is filtered out if they've been notified for ALL clips in this batch
  const notifiedClipsByUser = new Map<string, Set<string>>();
  for (const log of existingLogs) {
    if (!notifiedClipsByUser.has(log.user_id)) {
      notifiedClipsByUser.set(log.user_id, new Set());
    }
    notifiedClipsByUser.get(log.user_id)!.add(log.clip_id);
  }

  const clipIdSet = new Set(clipIds);
  return users.filter((user) => {
    const notifiedClips = notifiedClipsByUser.get(user.user_id);
    if (!notifiedClips) return true;
    // Keep user if they haven't been notified for at least one clip
    for (const clipId of clipIdSet) {
      if (!notifiedClips.has(clipId)) return true;
    }
    return false;
  });
}

async function generateTitlesForClips(
  clips: UnnotifiedClip[],
  memberInfo: MemberInfo
): Promise<Map<string, { title: string; description: string }>> {
  const titleMap = new Map<string, { title: string; description: string }>();

  for (const clip of clips) {
    const result = await generateClipTitle(clip.transcript, memberInfo);

    if (result.data) {
      titleMap.set(clip.id, {
        title: result.data,
        description: clip.description,
      });
    } else {
      // Fallback: use first few words of description as title
      const fallback = generateFallbackTitle(clip.description);
      titleMap.set(clip.id, {
        title: fallback.title,
        description: fallback.remainingDescription,
      });
    }

    if (clips.indexOf(clip) < clips.length - 1) {
      await sleep(AI_DELAY_MS);
    }
  }

  return titleMap;
}

async function renderEmailHtml(clipDataList: ClipData[], date: string): Promise<string> {
  const appUrl =
    (process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3000") +
    "/dashboard/create-clips";

  const element = createElement(NewContentAddedEmail, {
    clips: clipDataList,
    date,
    appUrl,
  });

  return await render(element);
}

export async function POST(request: NextRequest) {
  try {
    // Verify cron auth
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // console.log("[New Clips Notification] Starting...");

    // 1. Get unnotified clips
    const clips = await getUnnotifiedClips();

    if (clips.length === 0) {
      // console.log("[New Clips Notification] No unnotified clips found");
      return NextResponse.json({
        success: true,
        message: "No unnotified clips",
        timestamp: new Date().toISOString(),
      });
    }

    // console.log(
    //   `[New Clips Notification] Found ${clips.length} unnotified clips`
    // );

    // 2. Group clips by member_id
    const clipsByMember = new Map<number, UnnotifiedClip[]>();
    for (const clip of clips) {
      const existing = clipsByMember.get(clip.member_id) || [];
      existing.push(clip);
      clipsByMember.set(clip.member_id, existing);
    }

    let totalEmailsSent = 0;
    let totalClipsProcessed = 0;
    const errors: string[] = [];
    let rateLimited = false;

    // 3. Process each member group
    for (const [memberId, memberClips] of clipsByMember) {
      if (rateLimited) break;
      try {
        // Get MP info for AI title generation
        const memberInfo = await getMemberInfo(memberId);
        const clipIds = memberClips.map((c) => c.id);
        if (!memberInfo) {
          console.warn(
            `[New Clips Notification] No member info for member_id ${memberId}, marking clips as notified`
          );
          const { error: markError } = await supabaseAdminClient
            .from("parliament_member_clips")
            .update({ notification_sent_at: new Date().toISOString() })
            .in("id", clipIds);
          if (markError) {
            console.error(
              `[New Clips Notification] Failed to mark clips for member ${memberId}: ${markError.message}`
            );
          }
          totalClipsProcessed += clipIds.length;
          continue;
        }

        // Get eligible users
        const allUsers = await getEligibleUsers(memberId);
        const users = await filterAlreadyNotifiedUsers(clipIds, allUsers);

        if (users.length === 0) {
          // No users to notify — mark clips as notified
          const { error: markError } = await supabaseAdminClient
            .from("parliament_member_clips")
            .update({ notification_sent_at: new Date().toISOString() })
            .in("id", clipIds);
          if (markError) {
            console.error(
              `[New Clips Notification] Failed to mark clips for member ${memberId}: ${markError.message}`
            );
          }
          totalClipsProcessed += clipIds.length;
          continue;
        }

        // Generate AI titles
        const titleMap = await generateTitlesForClips(memberClips, memberInfo);

        // Build clip data for email template
        const clipDataList: ClipData[] = memberClips.map((clip) => {
          const titleInfo = titleMap.get(clip.id)!;
          return {
            title: titleInfo.title,
            description: titleInfo.description,
            image: clip.thumbnail_url || PLACEHOLDER_THUMBNAIL,
            duration: formatDuration(clip.duration_seconds),
          };
        });

        // Render email HTML once per member group (all users get the same clips)
        const today = new Date().toISOString().split("T")[0];
        const htmlContent = await renderEmailHtml(clipDataList, today);

        // Send to each user
        for (const user of users) {
          try {
            const result = await sendHtmlEmail({
              recipientEmail: user.email,
              subject: "New content added to your Parliament Connect account",
              htmlContent,
            });

            if (result.success) {
              // Log successful send for all clips in a single batch upsert
              const logEntries = clipIds.map((clipId) => ({
                clip_id: clipId,
                user_id: user.user_id,
                sent_at: new Date().toISOString(),
              }));
              const { error: logError } = await supabaseAdminClient
                .from("clip_notification_log")
                .upsert(logEntries, { onConflict: "clip_id,user_id" });
              if (logError) {
                console.error(
                  `[New Clips Notification] Failed to log notification for ${user.email}: ${logError.message}`
                );
              }
              totalEmailsSent++;
              // console.log(
              //   `[New Clips Notification] Sent email to ${user.email} for member ${memberId}`
              // );
            } else {
              console.error(
                `[New Clips Notification] Failed to send to ${user.email}: ${result.error}`
              );
              // Check for rate limit — stop sending if rate limited
              if (result.error?.includes("rate limit") || result.error?.includes("429")) {
                errors.push(`Mailjet rate limit hit, stopping sends`);
                rateLimited = true;
                break;
              }
            }
          } catch (emailError) {
            console.error(
              `[New Clips Notification] Error sending to ${user.email}:`,
              emailError
            );
          }

          await sleep(EMAIL_DELAY_MS);
        }

        // Mark clips as notified unless we were rate-limited mid-batch.
        // Rate limiting is transient — the next cron run should retry unsent users.
        // For permanent failures (bad email), marking is fine because
        // clip_notification_log + filterAlreadyNotifiedUsers prevent dupes
        // for users who already received the email.
        if (!rateLimited) {
          const { error: markError } = await supabaseAdminClient
            .from("parliament_member_clips")
            .update({ notification_sent_at: new Date().toISOString() })
            .in("id", clipIds);
          if (markError) {
            console.error(
              `[New Clips Notification] Failed to mark clips for member ${memberId}: ${markError.message}`
            );
          }
          totalClipsProcessed += clipIds.length;
        }
      } catch (memberError) {
        const msg = `Error processing member ${memberId}: ${memberError instanceof Error ? memberError.message : "Unknown error"}`;
        console.error(`[New Clips Notification] ${msg}`);
        errors.push(msg);
      }
    }

    // console.log(
    //   `[New Clips Notification] Complete. Emails sent: ${totalEmailsSent}, Clips processed: ${totalClipsProcessed}`
    // );

    return NextResponse.json({
      success: true,
      message: "New clips notification processed",
      data: {
        totalClips: clips.length,
        totalClipsProcessed,
        totalEmailsSent,
        memberGroups: clipsByMember.size,
        errors: errors.length > 0 ? errors : undefined,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[New Clips Notification] Fatal error:", error);

    ErrorLogger.logError(
      error instanceof Error ? error : new Error("Unknown error"),
      {
        action: "new_clips_notification_cron",
        route: "/api/cron/new-clips-notification",
      }
    );

    return NextResponse.json(
      {
        success: false,
        error: `New clips notification failed: ${error instanceof Error ? error.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
