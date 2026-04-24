import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";
import { google, GoogleGenerativeAIProviderOptions } from "@ai-sdk/google";
import { generateText } from "ai";
import { z } from "zod";

// Schema for AI response
const MPIdentificationSchema = z.object({
  detected: z.boolean().describe("Whether an MP was detected in the image"),
  mpName: z
    .string()
    .nullable()
    .describe("Full name of the UK MP if detected, null otherwise"),
  memberId: z
    .number()
    .nullable()
    .describe("Parliament member ID if known, null otherwise"),
  confidence: z
    .enum(["high", "medium", "low"])
    .nullable()
    .describe("Confidence level of the identification"),
});

export async function POST(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { imageUrl } = body;

    if (!imageUrl) {
      return NextResponse.json(
        { error: "Image URL is required" },
        { status: 400 }
      );
    }

    // Fetch the image and convert to base64
    let imageData: string;
    try {
      const imageResponse = await fetch(imageUrl);
      if (!imageResponse.ok) {
        throw new Error("Failed to fetch image");
      }
      const imageBuffer = await imageResponse.arrayBuffer();
      const base64Image = Buffer.from(imageBuffer).toString("base64");
      imageData = `data:image/jpeg;base64,${base64Image}`;
    } catch (error) {
      console.error("Error fetching image:", error);
      return NextResponse.json(
        { error: "Failed to fetch image from URL" },
        { status: 400 }
      );
    }

    // Call Gemini with high thinking level for better MP identification
    const { text, reasoning, providerMetadata } = await generateText({
      model: google("gemini-3-pro-preview"),
      messages: [
        {
          role: "user",
          content: [
            {
              type: "text",
              text: `You are an expert at identifying UK Members of Parliament (MPs). Analyze this image and identify the UK MP shown.

You must respond with valid JSON in this exact format:
{
  "detected": boolean,
  "mpName": string | null,
  "memberId": number | null,
  "confidence": "high" | "medium" | "low" | null
}

Fields:
- detected: true if you identified an MP, false otherwise
- mpName: Full name of the UK MP if detected, null otherwise
- memberId: Parliament member ID if known, null otherwise
- confidence: "high" if very certain, "medium" if fairly sure, "low" if uncertain, null if not detected

Think carefully before responding.`,
            },
            {
              type: "image",
              image: imageData,
            },
          ],
        },
      ],
      providerOptions: {
        google: {
          thinkingConfig: {
            thinkingLevel: "high",
            includeThoughts: true,
          },
        } satisfies GoogleGenerativeAIProviderOptions,
      },
    });

    console.log("AI Reasoning:", reasoning);
    console.log("Provider Metadata:", providerMetadata);

    // Parse JSON response
    let object;
    try {
      // Extract JSON from the response (it might be wrapped in markdown code blocks)
      const jsonMatch = text.match(/```json\n?([\s\S]*?)\n?```/) || text.match(/\{[\s\S]*\}/);
      const jsonString = jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : text;
      object = JSON.parse(jsonString);

      // Validate against schema
      MPIdentificationSchema.parse(object);
    } catch (parseError) {
      console.error("Failed to parse AI response:", text);
      console.error("Parse error:", parseError);
      throw new Error("Failed to parse AI response as valid JSON");
    }

    // If MP was detected and we have a name, try to find them in the database
    let matchedMember = null;
    if (object.detected && object.mpName) {
      // Search for the MP in the database by name
      const { data: members } = await supabase
        .from("parliament_members")
        .select(
          "member_id, display_name, party_abbreviation, constituency_name"
        )
        .ilike("display_name", `%${object.mpName}%`)
        .eq("is_current_member", true)
        .eq("is_deleted", false)
        .limit(1);

      if (members && members.length > 0) {
        matchedMember = members[0];
      }
    }

    return NextResponse.json({
      detected: object.detected,
      mpName: object.mpName,
      memberId: matchedMember?.member_id || object.memberId,
      confidence: object.confidence,
      matchedMember,
    });
  } catch (error) {
    console.error("AI identification error:", error);
    return NextResponse.json(
      {
        error: handleError(error, {
          component: "api/portrait-collection/identify-with-ai",
          action: "POST",
          route: "/api/portrait-collection/identify-with-ai",
        }),
      },
      { status: 500 }
    );
  }
}
