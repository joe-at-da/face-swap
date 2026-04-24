import { generateText } from "ai";
import { openaiProvider, GENERATION_MODEL } from "./providers/openai";
import { getErrorMessage } from "@/lib/getErrorMessage";

export interface MemberInfo {
  display_name: string | null;
  party_abbreviation: string | null;
  constituency_name: string | null;
}

/**
 * Service for generating AI descriptions of parliament clips
 */
/**
 * Generate a concise, engaging description for a parliament clip
 * @param transcript - The transcript text from the clip
 * @param memberInfo - Information about the parliament member
 * @returns Promise with description result or error
 */
export async function generateClipDescription(
  transcript: string,
  memberInfo: MemberInfo
) {
  try {
    if (!transcript || transcript.trim().length === 0) {
      return {
        error: "Transcript cannot be empty",
        data: null,
      };
    }

    if (!process.env.OPENAI_API_KEY) {
      return {
        error: "OpenAI API key not configured",
        data: null,
      };
    }

    const mpName = memberInfo.display_name || "MP";
    const constituency = memberInfo.constituency_name || "";
    const party = memberInfo.party_abbreviation || "";

    const prompt = `You are writing a short description for a parliament video clip.

MP: ${mpName}${party ? ` (${party})` : ""}${
      constituency ? ` for ${constituency}` : ""
    }

Transcript:
${transcript}

Instructions:
- Write one concise, factual description summarizing what ${mpName} actually said or did in this clip.
- Maximum 150 characters.
- Use active voice and direct statements. Focus on specific actions, statements, or concrete points made.
- Always use ${mpName}'s name instead of "The MP" or "the MP" for clarity.
- Avoid passive voice, abstract language, and vague phrasing like "the need to...", "is emphasized", "concerns are raised", or "support for X is discussed".
- Describe what was said or done, not abstract concepts or general themes.
- Be specific about the topic or issue addressed.
- No quotes, emojis, hashtags, or leading labels.
- Use British English spelling and terminology (e.g., "equalising" not "equalizing").

Examples of what to avoid:
- "The MP emphasizes the need to support doctors returning to the NHS post-pandemic"
- "Concerns about healthcare funding are raised"
- "Support for policy changes is discussed"

Examples of good descriptions:
- "${mpName} calls for supporting doctors returning to the NHS post-pandemic without detriment to their service"
- "${mpName} questions the government's handling of healthcare funding cuts"
- "${mpName} proposes new policy to address housing shortages in rural areas"

Return only the description text with no extra commentary.`;

    const { text } = await generateText({
      model: openaiProvider(GENERATION_MODEL),
      prompt,
      temperature: 0.5,
    });

    const description = text.trim();

    if (description.length > 200) {
      const truncated = truncateAtSentence(description, 150);
      return {
        data: truncated,
        error: null,
      };
    }

    return {
      data: description,
      error: null,
    };
  } catch (error) {
    const message = getErrorMessage(error);
    console.error("Failed to generate clip description:", error);
    return {
      error: message,
      data: null,
    };
  }
}

/**
 *
 * @param transcript
 * @param mp
 * @returns Promise with title result or error
 */

export async function generateClipTitle(
  transcript: string,
  mp: MemberInfo
) {
  try {
    if (!transcript || transcript == "") {
      return {
        error:
          "Error Failed to generate Clip title for clips without a transcript",
        data: null,
      };
    }

    if (!process.env.OPENAI_API_KEY) {
      return {
        error: "OpenAI API key not configured",
        data: null,
      };
    }

    const mpName = mp.display_name || "MP";
    const constituency = mp.constituency_name || "";
    const party = mp.party_abbreviation || "";

    const prompt = `You are titling a short parliament video clip.

MP: ${mpName}${party ? ` (${party})` : ""}${
      constituency ? ` for ${constituency}` : ""
    }

Transcript:
${transcript}

Instructions:
- Write a single, compelling title summarizing the main topic.
- Keep it under 80 characters.
- Use Title Case, no quotes, no emojis, no hashtags.
- Avoid clickbait; be factual and specific.
- Always use ${mpName}'s name in the title instead of "The MP" or "MP" for clarity.
- Do not include the words Transcript, MP, or metadata.
- Use British English spelling and terminology.

Return only the title text with no extra commentary.`;

    const { text } = await generateText({
      model: openaiProvider(GENERATION_MODEL),
      prompt,
      temperature: 0.7,
    });

    const title = text.trim();

    if (title.length > 200) {
      const truncated = truncateAtSentence(title, 150);
      return {
        data: truncated,
        error: null,
      };
    }

    return {
      data: title,
      error: null,
    };
  } catch (error) {
    const message = getErrorMessage(error);
    console.error("Error Failed to generate Clip title: ", error);
    return {
      error: message,
      data: null,
    };
  }
}

/**
 * Truncate text at the last complete sentence within maxLength
 */
function truncateAtSentence(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;

  const truncated = text.slice(0, maxLength);

  const lastSentenceEnd = Math.max(
    truncated.lastIndexOf("."),
    truncated.lastIndexOf("!"),
    truncated.lastIndexOf("?")
  );

  if (lastSentenceEnd > 0) {
    return truncated.slice(0, lastSentenceEnd + 1);
  }

  const lastSpace = truncated.lastIndexOf(" ");
  if (lastSpace > 0) {
    return truncated.slice(0, lastSpace) + "...";
  }

  return truncated + "...";
}

/**
 * Generate a fallback description from transcript
 * Used when AI generation fails
 */
export function generateFallbackDescription(
  transcript: string,
  memberInfo: MemberInfo
): string {
  const mpName = memberInfo.display_name || "MP";
  const truncated = transcript.slice(0, 100).trim();
  return `${mpName} speaks: ${truncated}${
    transcript.length > 100 ? "..." : ""
  }`;
}
