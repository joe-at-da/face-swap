import { NextRequest, NextResponse } from "next/server";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

interface MPIdentificationEmailRequest {
  userId: string;
  userEmail: string;
  memberId: number;
  mpName: string;
  clipId: string;
  notificationType: "individual" | "team";
  teamId?: string;
}

export async function POST(request: NextRequest) {
  try {
    // Verify CRON_SECRET for security
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
      console.warn("[MP Identification Email] Unauthorized request");
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Parse request body
    const body: MPIdentificationEmailRequest = await request.json();

    const {
      userId,
      userEmail,
      memberId,
      mpName,
      clipId,
      notificationType,
      teamId,
    } = body;

    // Validate required fields
    if (
      !userId ||
      !userEmail ||
      !memberId ||
      !mpName ||
      !clipId ||
      !notificationType
    ) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 },
      );
    }

    console.log(
      `[MP Identification Email] Processing ${notificationType} notification for user ${userId} (${userEmail}) - MP: ${mpName} (${memberId})`,
    );

    // Get clip details for the email content
    const { data: clip, error: clipError } = await supabaseAdminClient
      .from("parliament_member_clips")
      .select(
        `
        id,
        transcript,
        start_timestamp,
        end_timestamp,
        session_date,
        session_type,
        thumbnail_url,
        clip_url
      `,
      )
      .eq("id", clipId)
      .single();

    if (clipError || !clip) {
      console.error("[MP Identification Email] Clip not found:", clipError);
      return NextResponse.json({ error: "Clip not found" }, { status: 404 });
    }

    // Get MP details for email content
    const { data: mp, error: mpError } = await supabaseAdminClient
      .from("parliament_members")
      .select(
        `
        member_id,
        display_name,
        party_name,
        constituency_name,
        parliament_member_portraits!inner (
          image_url,
          is_primary
        )
      `,
      )
      .eq("member_id", memberId)
      .eq("parliament_member_portraits.is_primary", true)
      .single();

    if (mpError || !mp) {
      console.error("[MP Identification Email] MP not found:", mpError);
      return NextResponse.json({ error: "MP not found" }, { status: 404 });
    }

    // Get team details if this is a team notification
    let teamName = null;
    if (notificationType === "team" && teamId) {
      const { data: team } = await supabaseAdminClient
        .from("teams")
        .select("name")
        .eq("id", teamId)
        .single();

      teamName = team?.name || null;
    }

    // Prepare email data
    const emailData = {
      to: userEmail,
      subject: `New clip from ${mpName}${
        teamName ? ` (${teamName} team)` : ""
      }`,
      template: "mp-identification-email",
      data: {
        userEmail,
        mpName: mp.display_name,
        mpParty: mp.party_name,
        mpConstituency: mp.constituency_name,
        mpImage: mp.parliament_member_portraits?.[0]?.image_url,
        clipId: clip.id,
        clipTranscript: clip.transcript,
        clipStartTime: clip.start_timestamp,
        clipEndTime: clip.end_timestamp,
        sessionDate: clip.session_date,
        sessionType: clip.session_type,
        clipThumbnail: clip.thumbnail_url,
        clipUrl: clip.clip_url,
        notificationType,
        teamName,
        appUrl: process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3000",
      },
    };

    // Send email using your email service
    // This is a placeholder - replace with your actual email service integration
    const emailResult = await sendMPIdentificationEmail(emailData);

    if (!emailResult.success) {
      console.error(
        "[MP Identification Email] Failed to send email:",
        emailResult.error,
      );
      return NextResponse.json(
        {
          success: false,
          error: "Failed to send email",
          details: emailResult.error,
        },
        { status: 500 },
      );
    }

    console.log(
      `[MP Identification Email] Successfully sent ${notificationType} notification to ${userEmail}`,
    );

    return NextResponse.json({
      success: true,
      message: "Email notification sent successfully",
      data: {
        userId,
        userEmail,
        memberId,
        mpName,
        clipId,
        notificationType,
        teamId,
        emailId: emailResult.emailId,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[MP Identification Email] Error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `MP identification email failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 },
    );
  }
}

// Mailjet email service integration
interface EmailData {
  to: string;
  subject: string;
  template: string;
  data: {
    userEmail: string;
    mpName: string | null;
    mpParty: string | null;
    mpConstituency: string | null;
    mpImage: string | null;
    clipId: string;
    clipTranscript: string;
    clipStartTime: string;
    clipEndTime: string;
    sessionDate: string | null;
    sessionType: string | null;
    clipThumbnail: string | null;
    clipUrl: string | null;
    notificationType: string;
    teamName: string | null;
    appUrl: string;
  };
}

async function sendMPIdentificationEmail(emailData: EmailData) {
  try {
    if (!process.env.MAILJET_API_KEY || !process.env.MAILJET_SECRET_KEY) {
      throw new Error(
        "Mailjet API credentials not found in environment variables",
      );
    }

    // Use the correct Mailjet v6 initialization
    const MailjetModule = await import("node-mailjet");
    const Mailjet = MailjetModule.default;
    const mailjet = new Mailjet({
      apiKey: process.env.MAILJET_API_KEY,
      apiSecret: process.env.MAILJET_SECRET_KEY,
    });

    console.log("[Mailjet] Initialized successfully with v6 API");
    console.log("[Mailjet] Mailjet object type:", typeof mailjet);
    console.log(
      "[Mailjet] Available methods:",
      Object.getOwnPropertyNames(mailjet),
    );

    // Determine which template to use based on notification type
    const templateId =
      emailData.data.notificationType === "individual"
        ? process.env.MAILJET_INDIVIDUAL_TEMPLATE_ID
        : process.env.MAILJET_TEAM_TEMPLATE_ID;

    if (!templateId) {
      throw new Error(
        `Template ID not found for notification type: ${emailData.data.notificationType}`,
      );
    }

    console.log(
      `[Mailjet] Sending ${emailData.data.notificationType} email using template ID: ${templateId}`,
    );

    // Prepare the email data object
    const emailPayload = {
      Messages: [
        {
          From: {
            Email:
              process.env.MAILJET_FROM_EMAIL || "notifications@yourdomain.com",
            Name: process.env.MAILJET_FROM_NAME || "Parliament AI",
          },
          To: [
            {
              Email: emailData.to,
              Name: emailData.data.userEmail,
            },
          ],
          TemplateID: parseInt(templateId),
          TemplateLanguage: true,
          Subject: emailData.subject,
          Variables: {
            // MP Information
            mp_name: emailData.data.mpName || "",
            mp_party: emailData.data.mpParty || "",
            mp_constituency: emailData.data.mpConstituency || "",
            mp_image: emailData.data.mpImage || "",

            // Clip Information
            clip_id: emailData.data.clipId || "",
            clip_transcript: emailData.data.clipTranscript || "",
            clip_start_time: emailData.data.clipStartTime || "",
            clip_end_time: emailData.data.clipEndTime || "",
            clip_thumbnail: emailData.data.clipThumbnail || "",
            clip_url: emailData.data.clipUrl || "",

            // Session Information
            session_date: emailData.data.sessionDate || "",
            session_type: emailData.data.sessionType || "",

            // Team Information (only for team notifications)
            team_name: emailData.data.teamName || "",

            // App Information
            app_url: emailData.data.appUrl || "http://localhost:3000",
            user_email: emailData.data.userEmail || "",

            // Notification Type
            notification_type: emailData.data.notificationType || "individual",
          },
        },
      ],
    };

    console.log(
      "[Mailjet] Sending email with payload:",
      JSON.stringify(emailPayload, null, 2),
    );

    // Send the email using Mailjet v6 API format
    const result = await mailjet
      .post("send", { version: "v3.1" })
      .request(emailPayload);

    console.log(
      `[Mailjet] Email sent successfully. Message ID: ${
        (result.body as { Messages: { To: { MessageID: string }[] }[] })
          .Messages[0].To[0].MessageID
      }`,
    );

    return {
      success: true,
      emailId: (result.body as { Messages: { To: { MessageID: string }[] }[] })
        .Messages[0].To[0].MessageID,
      message: "Email sent successfully via Mailjet",
    };
  } catch (error) {
    console.error("[Mailjet] Error:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown Mailjet error",
    };
  }
}

// GET endpoint for health check
export async function GET() {
  return NextResponse.json({
    success: true,
    message: "MP Identification Email API is running",
    endpoint: "/api/notifications/mp-identification-email",
    methods: ["POST"],
    auth: "Required (CRON_SECRET)",
    timestamp: new Date().toISOString(),
  });
}
