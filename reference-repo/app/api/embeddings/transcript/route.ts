import { NextRequest, NextResponse } from "next/server";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { generateAndFormatEmbedding } from "@/services/ai/embedding-service";
import { EMBEDDING_DIMENSIONS } from "@/services/ai/providers/openai";
import {
  generateClipDescription,
  generateClipTitle,
  generateFallbackDescription,
  type MemberInfo,
} from "@/services/ai/generation-service";

interface EmbeddingRequestBody {
  parliament_clip_id?: string;
  user_clip_id?: string;
}

export async function POST(request: NextRequest) {
  try {
    // Verify CRON_SECRET authentication
    const authHeader = request.headers.get("authorization");
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Parse request body
    const body: EmbeddingRequestBody = await request.json();

    const { parliament_clip_id, user_clip_id } = body;

    // Validate that exactly one clip ID is provided
    if (
      (!parliament_clip_id && !user_clip_id) ||
      (parliament_clip_id && user_clip_id)
    ) {
      return NextResponse.json(
        {
          error:
            "Must provide exactly one of: parliament_clip_id or user_clip_id",
        },
        { status: 400 }
      );
    }

    const supabase = supabaseAdminClient;

    let transcript: string | null = null;
    let clipData: {
      id: string;
      transcript: string | null;
      transcript_embedding: string | null;
      description: string | null;
      description_embedding: string | null;
      title?: string | null;
      title_embedding?: string | null;
      clip_id?: string;
      member_id?: number;
      parliament_member_clips?: {
        parliament_members: {
          display_name: string | null;
          party_abbreviation: string | null;
          constituency_name: string | null;
        };
      };
      parliament_members?: {
        display_name: string | null;
        party_abbreviation: string | null;
        constituency_name: string | null;
      };
    } | null = null;
    let memberInfo: MemberInfo | null = null;

    // Fetch clip data based on type (with member info for parliament clips)
    if (parliament_clip_id) {
      const { data, error } = await supabase
        .from("parliament_member_clips")
        .select(
          `
          id,
          transcript,
          transcript_embedding,
          description,
          description_embedding,
          member_id,
          parliament_members (
            display_name,
            party_abbreviation,
            constituency_name
          )
        `
        )
        .eq("id", parliament_clip_id)
        .single();

      if (error) {
        console.error("Failed to fetch parliament clip:", error);
        return NextResponse.json(
          { error: "Parliament clip not found" },
          { status: 404 }
        );
      }

      clipData = data;
      transcript = data.transcript;

      // Extract member info
      const memberData = Array.isArray(data.parliament_members)
        ? data.parliament_members[0]
        : data.parliament_members;

      if (memberData) {
        memberInfo = {
          display_name: memberData.display_name,
          party_abbreviation: memberData.party_abbreviation,
          constituency_name: memberData.constituency_name,
        };
      }
    } else if (user_clip_id) {
      const { data, error } = await supabase
        .from("user_clips")
        .select(
          `
          id,
          transcript,
          transcript_embedding,
          description,
          description_embedding,
          title,
          title_embedding,
          clip_id,
          parliament_member_clips!inner(
            parliament_members!inner(
              display_name,
              party_abbreviation,
              constituency_name
            )
          )
        `
        )
        .eq("id", user_clip_id)
        .single();

      if (error) {
        console.error("Failed to fetch user clip:", error);
        return NextResponse.json(
          { error: "User clip not found" },
          { status: 404 }
        );
      }

      clipData = data;
      transcript = data.transcript;

      // Extract parliament member info from joined data
      const parliamentMemberData = Array.isArray(data.parliament_member_clips)
        ? data.parliament_member_clips[0]
        : data.parliament_member_clips;

      if (parliamentMemberData) {
        const memberData = Array.isArray(
          parliamentMemberData.parliament_members
        )
          ? parliamentMemberData.parliament_members[0]
          : parliamentMemberData.parliament_members;

        if (memberData) {
          memberInfo = {
            display_name: memberData.display_name,
            party_abbreviation: memberData.party_abbreviation || "",
            constituency_name: memberData.constituency_name || "",
          };
        }
      }
    }

    // Check if clip has a transcript
    if (!transcript || transcript.trim().length === 0) {
      return NextResponse.json(
        { error: "Clip does not have a transcript" },
        { status: 400 }
      );
    }

    const transcriptEmbeddingResult = await generateAndFormatEmbedding(
      transcript
    );

    if (!transcriptEmbeddingResult.data) {
      console.error(
        "Failed to generate transcript embedding:",
        transcriptEmbeddingResult.error
      );
      return NextResponse.json(
        {
          error: "Failed to generate transcript embedding",
          details: transcriptEmbeddingResult.error,
        },
        { status: 500 }
      );
    }

    // Generate AI description (always regenerate when processing - transcript changed or new clip)
    let description: string | null = null;
    let descriptionEmbedding: string | null = null;
    let descriptionGenerated = false;

    // Generate AI title (for user clips only - always regenerate when processing)
    let title: string | null = null;
    let titleEmbedding: string | null = null;
    let titleGenerated = false;

    if (parliament_clip_id && memberInfo) {
      const descriptionResult = await generateClipDescription(
        transcript,
        memberInfo
      );

      if (!descriptionResult.data) {
        console.warn(
          "AI description generation failed, using fallback:",
          descriptionResult.error
        );
        // Use fallback description
        description = generateFallbackDescription(transcript, memberInfo);
        descriptionGenerated = true;
      } else {
        description = descriptionResult.data;
        descriptionGenerated = true;
      }

      if (description) {
        const descEmbeddingResult = await generateAndFormatEmbedding(
          description
        );

        if (descEmbeddingResult.data) {
          descriptionEmbedding = descEmbeddingResult.data;
        } else {
          console.warn(
            "Failed to generate description embedding:",
            descEmbeddingResult.error
          );
        }
      }
    } else if (user_clip_id && memberInfo) {
      const descriptionResult = await generateClipDescription(
        transcript,
        memberInfo
      );

      if (!descriptionResult.data) {
        console.warn(
          "AI description generation failed, using fallback:",
          descriptionResult.error
        );
        // Use fallback description
        description = generateFallbackDescription(transcript, memberInfo);
        descriptionGenerated = true;
      } else {
        description = descriptionResult.data;
        descriptionGenerated = true;
      }

      if (description) {
        const descEmbeddingResult = await generateAndFormatEmbedding(
          description
        );

        if (descEmbeddingResult.data) {
          descriptionEmbedding = descEmbeddingResult.data;
        } else {
          console.warn(
            "Failed to generate description embedding:",
            descEmbeddingResult.error
          );
        }
      }

      if (clipData?.parliament_member_clips) {

        const parliamentMemberData = Array.isArray(
          clipData.parliament_member_clips
        )
          ? clipData.parliament_member_clips[0]
          : clipData.parliament_member_clips;

        const memberData = parliamentMemberData?.parliament_members
          ? Array.isArray(parliamentMemberData.parliament_members)
            ? parliamentMemberData.parliament_members[0]
            : parliamentMemberData.parliament_members
          : null;

        if (memberData) {
          const titleResult = await generateClipTitle(
            transcript,
            {
              display_name: memberData.display_name,
              party_abbreviation: memberData.party_abbreviation,
              constituency_name: memberData.constituency_name,
            }
          );

          if (titleResult.data) {
            title = titleResult.data;
            titleGenerated = true;

            const titleEmbeddingResult = await generateAndFormatEmbedding(
              title
            );

            if (titleEmbeddingResult.data) {
              titleEmbedding = titleEmbeddingResult.data;
            } else {
              console.warn(
                "Failed to generate title embedding:",
                titleEmbeddingResult.error
              );
            }
          } else {
            console.warn("Failed to generate title:", titleResult.error);
          }
        }
      }
    }

    // Store both transcript embedding and description in database
    let updateResult;
    if (parliament_clip_id) {
      const parliamentUpdateData: {
        transcript_embedding: string;
        updated_at: string;
        description?: string | null;
        description_embedding?: string | null;
      } = {
        transcript_embedding: transcriptEmbeddingResult.data,
        updated_at: new Date().toISOString(),
      };

      // Only update description if it was generated (avoid overwriting existing with null)
      if (descriptionGenerated) {
        parliamentUpdateData.description = description;
        parliamentUpdateData.description_embedding = descriptionEmbedding;
      }

      updateResult = await supabase
        .from("parliament_member_clips")
        .update(parliamentUpdateData)
        .eq("id", parliament_clip_id);
    } else if (user_clip_id) {
      const updateData: {
        transcript_embedding: string;
        updated_at: string;
        description?: string | null;
        description_embedding?: string | null;
        title?: string | null;
        title_embedding?: string | null;
      } = {
        transcript_embedding: transcriptEmbeddingResult.data,
        updated_at: new Date().toISOString(),
      };

      // Only update description and title if they were generated
      if (descriptionGenerated) {
        updateData.description = description;
        updateData.description_embedding = descriptionEmbedding;
      }

      if (titleGenerated) {
        updateData.title = title;
        updateData.title_embedding = titleEmbedding;
      }

      updateResult = await supabase
        .from("user_clips")
        .update(updateData)
        .eq("id", user_clip_id);
    }

    if (updateResult?.error) {
      console.error(
        "Failed to update clip with embeddings:",
        updateResult.error
      );
      return NextResponse.json(
        { error: "Failed to store embeddings" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      message: "Embeddings and metadata generated successfully",
      clip_id: clipData?.id,
      clip_type: parliament_clip_id ? "parliament_clip" : "user_clip",
      transcript_length: transcript.length,
      transcript_embedding_dimensions: EMBEDDING_DIMENSIONS,
      description_generated: descriptionGenerated,
      description_embedding_generated: descriptionEmbedding !== null,
      title_generated: titleGenerated,
      title_embedding_generated: titleEmbedding !== null,
    });
  } catch (error) {
    console.error("Embedding API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
