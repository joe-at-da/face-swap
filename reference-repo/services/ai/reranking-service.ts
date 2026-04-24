import { CohereClient } from "cohere-ai";
import { getErrorMessage } from "@/lib/getErrorMessage";

const RERANK_MODEL = "rerank-v4.0-pro";
// Cohere scores are inflated for same-author parliamentary speeches (floor ~0.25).
// 0.35 filters the noise floor while keeping genuinely relevant results.
const RELEVANCE_THRESHOLD = 0.35;
// Minimum score drop between consecutive results to be considered a gap.
// 0.08 catches medium gaps (e.g. pollution → 5 results, mental health → 5)
// without affecting specific queries (sewage, ADHD still get 3-4 results).
const MIN_GAP_SIZE = 0.08;
// Always return at least this many results (if available above threshold).
const MIN_RESULTS = 3;
// Hard cap when no gap is found. Generic queries (e.g. "education") produce
// smooth score distributions where all clips score above threshold with tiny
// gaps. Without a cap, 10K+ clips would all be returned. 25 is enough to
// show meaningful results while the top ones are already in Cohere rank order.
const MAX_RESULTS = 25;

interface RerankableClip {
  transcript?: string | null;
  description?: string | null;
  [key: string]: unknown;
}

type RerankResponse<T extends RerankableClip> = {
  data: T[] | null;
  error: string | null;
};

/**
 * Find the optimal cutoff point in sorted relevance scores.
 * Looks for the largest score gap (cliff) between consecutive results.
 * If no significant gap exists, caps at MAX_RESULTS to prevent flooding.
 */
function findScoreCutoff(scores: number[]): number {
  if (scores.length <= MIN_RESULTS) return scores.length;

  // Search ALL scores above threshold for the largest gap (not just top 30).
  // With 100K clips, the relevant→irrelevant boundary could be at any position.
  let bestGapIndex = -1;
  let bestGap = 0;

  for (let i = 1; i < scores.length; i++) {
    const gap = scores[i - 1] - scores[i];
    if (gap > bestGap && gap >= MIN_GAP_SIZE) {
      bestGap = gap;
      bestGapIndex = i;
    }
  }

  if (bestGapIndex > 0) {
    return Math.max(bestGapIndex, MIN_RESULTS);
  }

  // No clear gap — cap at MAX_RESULTS. Generic queries on small corpora
  // produce smooth distributions where every clip scores above threshold.
  // The cap prevents flooding; results are already in Cohere rank order.
  return Math.min(scores.length, MAX_RESULTS);
}

/**
 * Rerank clips using Cohere Rerank v2 API.
 * Combines each clip's description + transcript into a single document,
 * then reranks by semantic relevance to the original query.
 *
 * Uses two-layer filtering:
 * 1. Minimum relevance score threshold (filters noise floor)
 * 2. Score-gap detection (finds natural cutoff for specific queries)
 *
 * Falls back gracefully: returns original order on failure.
 */
export async function rerankClips<T extends RerankableClip>(
  query: string,
  clips: T[],
  topN?: number
): Promise<RerankResponse<T>> {
  try {
    if (!process.env.COHERE_API_KEY) {
      return { data: null, error: "Cohere API key not configured" };
    }

    if (clips.length === 0) {
      return { data: [], error: null };
    }

    // Build document strings: description (if any) + transcript
    const documents = clips.map((clip) => {
      const parts: string[] = [];
      if (clip.description) parts.push(clip.description);
      if (clip.transcript) parts.push(clip.transcript);
      return parts.join("\n\n") || "";
    });

    const cohere = new CohereClient({ token: process.env.COHERE_API_KEY });

    const response = await cohere.v2.rerank({
      model: RERANK_MODEL,
      query,
      documents,
      topN: topN ?? clips.length,
    });

    // Layer 1: Filter by minimum relevance score
    const aboveThreshold = response.results.filter(
      (result) => result.relevanceScore >= RELEVANCE_THRESHOLD
    );

    // Layer 2: Score-gap detection
    const scores = aboveThreshold.map((r) => r.relevanceScore);
    const cutoff = findScoreCutoff(scores);
    const finalResults = aboveThreshold.slice(0, cutoff);

    const reranked = finalResults.map((result) => clips[result.index]);

    console.log(
      `[Reranking] ${response.results.length} candidates → ${aboveThreshold.length} above ${RELEVANCE_THRESHOLD} → ${reranked.length} after gap detection`
    );

    return { data: reranked, error: null };
  } catch (error) {
    const message = getErrorMessage(error);
    console.error("[Reranking] Failed:", message);
    return { data: null, error: message };
  }
}
