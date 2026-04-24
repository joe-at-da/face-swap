import { generateText } from "ai";
import { openaiProvider } from "./providers/openai";
import { getErrorMessage } from "@/lib/getErrorMessage";

const SEARCH_MODEL = "gpt-5-mini";

export interface SearchQueryExpansion {
  hypotheticalTranscript: string;
  searchTerms: string[];
  originalQuery: string;
}

export interface MultiSearchQueryExpansion {
  hypotheticalTranscripts: string[];
  searchTerms: string[];
  originalQuery: string;
}

type SearchQueryExpansionResponse = {
  data: SearchQueryExpansion | null;
  error: string | null;
};

/**
 * Expand a search query using HyDE (Hypothetical Document Embeddings) + term expansion.
 *
 * Generates a hypothetical parliamentary transcript excerpt (for vector embedding)
 * and a list of related search terms (for full-text search).
 */
export async function expandSearchQuery(
  query: string
): Promise<SearchQueryExpansionResponse> {
  try {
    const trimmed = query.trim();

    if (!trimmed || trimmed.length < 3) {
      return {
        data: {
          hypotheticalTranscript: trimmed,
          searchTerms: [trimmed],
          originalQuery: trimmed,
        },
        error: null,
      };
    }

    if (!process.env.OPENAI_API_KEY) {
      return { data: null, error: "OpenAI API key not configured" };
    }

    const truncated = trimmed.length > 500 ? trimmed.slice(0, 500) : trimmed;

    const prompt = `You are a UK parliamentary transcript generator used for search query expansion.

Given a user's search query about UK parliament speeches, generate two things:

1. "transcript": A hypothetical excerpt (100-200 words) from a UK parliamentary transcript that would be highly relevant to this search query. Write it as if an MP is speaking in the House of Commons about this topic. Use British English, parliamentary language, and cover the key aspects and subtopics. Include specific policy terms, department names, and related issues that would appear in real debates.

2. "terms": A list of 5-10 related search terms and phrases that would appear in parliamentary transcripts about this topic. Include synonyms, related policy areas, and parliamentary terminology.

IMPORTANT: Output ONLY valid JSON with no other text. Format: { "transcript": "...", "terms": ["...", ...] }

Query: "${truncated}"`;

    const { text } = await generateText({
      model: openaiProvider(SEARCH_MODEL),
      prompt,
      temperature: 0.4,
    });

    const parsed = JSON.parse(text.trim());

    if (!parsed.transcript || !Array.isArray(parsed.terms)) {
      return {
        data: {
          hypotheticalTranscript: truncated,
          searchTerms: [truncated],
          originalQuery: truncated,
        },
        error: null,
      };
    }

    return {
      data: {
        hypotheticalTranscript: parsed.transcript,
        searchTerms: parsed.terms,
        originalQuery: truncated,
      },
      error: null,
    };
  } catch (error) {
    const message = getErrorMessage(error);
    console.error("[Search Query Expansion] Failed:", message);
    const fallbackQuery = query.trim().slice(0, 500);
    return {
      data: {
        hypotheticalTranscript: fallbackQuery,
        searchTerms: [fallbackQuery],
        originalQuery: fallbackQuery,
      },
      error: null,
    };
  }
}

type MultiSearchQueryExpansionResponse = {
  data: MultiSearchQueryExpansion | null;
  error: string | null;
};

/**
 * Multi-HyDE: Generate multiple hypothetical transcripts in parallel for more
 * robust vector matching. Each transcript captures different aspects of the topic.
 * Embeddings of these transcripts are averaged downstream for a more central
 * representation in vector space.
 */
export async function expandSearchQueryMulti(
  query: string,
  count: number = 3
): Promise<MultiSearchQueryExpansionResponse> {
  const trimmed = query.trim();

  if (!trimmed || trimmed.length < 3) {
    return {
      data: {
        hypotheticalTranscripts: [trimmed],
        searchTerms: [trimmed],
        originalQuery: trimmed,
      },
      error: null,
    };
  }

  // Run `count` HyDE expansions in parallel with higher temperature for diversity
  const promises = Array.from({ length: count }, () =>
    expandSearchQuerySingle(trimmed, 0.5)
  );

  const results = await Promise.allSettled(promises);

  const transcripts: string[] = [];
  const allTerms: string[] = [];

  for (const result of results) {
    if (result.status === "fulfilled" && result.value.data) {
      transcripts.push(result.value.data.hypotheticalTranscript);
      allTerms.push(...result.value.data.searchTerms);
    }
  }

  // Need at least 1 successful result
  if (transcripts.length === 0) {
    const truncated = trimmed.length > 500 ? trimmed.slice(0, 500) : trimmed;
    return {
      data: {
        hypotheticalTranscripts: [truncated],
        searchTerms: [truncated],
        originalQuery: truncated,
      },
      error: null,
    };
  }

  // Deduplicate search terms
  const uniqueTerms = [...new Set(allTerms.map((t) => t.trim()).filter(Boolean))];
  const truncated = trimmed.length > 500 ? trimmed.slice(0, 500) : trimmed;

  return {
    data: {
      hypotheticalTranscripts: transcripts,
      searchTerms: uniqueTerms,
      originalQuery: truncated,
    },
    error: null,
  };
}

/**
 * Internal single HyDE expansion with configurable temperature.
 */
async function expandSearchQuerySingle(
  query: string,
  temperature: number
): Promise<SearchQueryExpansionResponse> {
  try {
    if (!process.env.OPENAI_API_KEY) {
      return { data: null, error: "OpenAI API key not configured" };
    }

    const truncated = query.length > 500 ? query.slice(0, 500) : query;

    const prompt = `You are a UK parliamentary transcript generator used for search query expansion.

Given a user's search query about UK parliament speeches, generate two things:

1. "transcript": A hypothetical excerpt (100-200 words) from a UK parliamentary transcript that would be highly relevant to this search query. Write it as if an MP is speaking in the House of Commons about this topic. Use British English, parliamentary language, and cover the key aspects and subtopics. Include specific policy terms, department names, and related issues that would appear in real debates.

2. "terms": A list of 5-10 related search terms and phrases that would appear in parliamentary transcripts about this topic. Include synonyms, related policy areas, and parliamentary terminology.

IMPORTANT: Output ONLY valid JSON with no other text. Format: { "transcript": "...", "terms": ["...", ...] }

Query: "${truncated}"`;

    const { text } = await generateText({
      model: openaiProvider(SEARCH_MODEL),
      prompt,
      temperature,
    });

    const parsed = JSON.parse(text.trim());

    if (!parsed.transcript || !Array.isArray(parsed.terms)) {
      return {
        data: {
          hypotheticalTranscript: truncated,
          searchTerms: [truncated],
          originalQuery: truncated,
        },
        error: null,
      };
    }

    return {
      data: {
        hypotheticalTranscript: parsed.transcript,
        searchTerms: parsed.terms,
        originalQuery: truncated,
      },
      error: null,
    };
  } catch (error) {
    const message = getErrorMessage(error);
    console.error("[Multi-HyDE] Single expansion failed:", message);
    return { data: null, error: message };
  }
}

/**
 * Build a fulltext query string for websearch_to_tsquery from expanded terms.
 * Uses OR logic for broad recall — RRF handles precision.
 */
export function buildFulltextQuery(
  originalQuery: string,
  searchTerms: string[]
): string {
  const allTerms = [originalQuery, ...searchTerms];
  const unique = [...new Set(allTerms.map((t) => t.trim()).filter(Boolean))];
  return unique.join(" OR ");
}
