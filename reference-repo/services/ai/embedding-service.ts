import { embed, embedMany } from "ai";
import {
  openaiProvider,
  EMBEDDING_MODEL,
  EMBEDDING_DIMENSIONS,
} from "./providers/openai";

export interface EmbeddingResult {
  embedding: number[];
  dimensions: number;
  model: string;
}

type EmbeddingResponse = {
  data: EmbeddingResult | null;
  error: string | null;
};

type FormattedEmbeddingResponse = {
  data: string | null;
  error: string | null;
};

/**
 * Generate embedding for a given text using OpenAI
 * Returns { data, error } like generation-service
 */
export async function generateEmbedding(
  text: string
): Promise<EmbeddingResponse> {
  try {
    if (!text || text.trim().length === 0) {
      return { data: null, error: "Transcript cannot be empty" };
    }

    if (!process.env.OPENAI_API_KEY) {
      console.error("[Embedding] OPENAI_API_KEY is not set");
      return { data: null, error: "OpenAI API key not configured" };
    }

    const { embedding } = await embed({
      model: openaiProvider.embedding(EMBEDDING_MODEL),
      value: text,
    });

    if (embedding.length !== EMBEDDING_DIMENSIONS) {
      return {
        data: null,
        error: `Unexpected embedding dimensions. Expected ${EMBEDDING_DIMENSIONS}, got ${embedding.length}`,
      };
    }

    return {
      data: {
        embedding,
        dimensions: embedding.length,
        model: EMBEDDING_MODEL,
      },
      error: null,
    };
  } catch (error) {
    console.error("Failed to generate embedding:", error instanceof Error ? error.message : error);
    return { data: null, error: `Failed to generate embedding: ${error instanceof Error ? error.message : "Unknown error"}` };
  }
}

/**
 * Format embedding array for pgvector storage
 */
export function formatForPgVector(embedding: number[]): string {
  return `[${embedding.join(",")}]`;
}

/**
 * Generate and format embedding for database storage
 * Returns { data, error } with formatted pgvector string on success
 */
export async function generateAndFormatEmbedding(
  text: string
): Promise<FormattedEmbeddingResponse> {
  const result = await generateEmbedding(text);
  if (result.error) {
    return { data: null, error: result.error };
  }
  return { data: formatForPgVector(result.data!.embedding), error: null };
}

/**
 * Generate embeddings for multiple texts in batch using a single API call.
 * Much faster than calling generateEmbedding() in a loop.
 * Uses embedMany which auto-chunks and supports parallel requests.
 */
export async function generateBatchEmbeddings(
  texts: string[],
  maxParallelCalls = 5
): Promise<{ data: string[] | null; error: string | null }> {
  try {
    if (texts.length === 0) {
      return { data: [], error: null };
    }

    if (!process.env.OPENAI_API_KEY) {
      return { data: null, error: "OpenAI API key not configured" };
    }

    const { embeddings } = await embedMany({
      model: openaiProvider.embedding(EMBEDDING_MODEL),
      values: texts,
      maxParallelCalls,
    });

    const formatted = embeddings.map(formatForPgVector);
    return { data: formatted, error: null };
  } catch (error) {
    console.error("Failed to generate batch embeddings:", error);
    return {
      data: null,
      error: error instanceof Error ? error.message : "Batch embedding failed",
    };
  }
}

/**
 * Generate embeddings for multiple texts in parallel and average them.
 * Used by Multi-HyDE to combine multiple hypothetical document embeddings
 * into a single, more robust query embedding.
 */
export async function generateAveragedEmbedding(
  texts: string[]
): Promise<FormattedEmbeddingResponse> {
  if (texts.length === 0) {
    return { data: null, error: "No texts provided for embedding" };
  }

  if (texts.length === 1) {
    return generateAndFormatEmbedding(texts[0]);
  }

  const results = await Promise.allSettled(
    texts.map((text) => generateEmbedding(text))
  );

  const embeddings: number[][] = [];
  for (const result of results) {
    if (
      result.status === "fulfilled" &&
      !result.value.error &&
      result.value.data
    ) {
      embeddings.push(result.value.data.embedding);
    }
  }

  if (embeddings.length === 0) {
    return { data: null, error: "All embedding generations failed" };
  }

  // Average element-wise
  const dims = embeddings[0].length;
  const averaged = new Array<number>(dims);
  for (let i = 0; i < dims; i++) {
    let sum = 0;
    for (const emb of embeddings) {
      sum += emb[i];
    }
    averaged[i] = sum / embeddings.length;
  }

  return { data: formatForPgVector(averaged), error: null };
}
