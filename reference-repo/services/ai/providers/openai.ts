import { openai } from "@ai-sdk/openai";

/**
 * OpenAI provider instance for AI SDK
 * Uses environment variable OPENAI_API_KEY
 */
export const openaiProvider = openai;

/**
 * OpenAI embedding model configuration
 * text-embedding-3-large at native 3072 dims for best quality.
 */
export const EMBEDDING_MODEL = "text-embedding-3-large";

/**
 * Expected embedding dimensions for text-embedding-3-large (native)
 */
export const EMBEDDING_DIMENSIONS = 3072;

//**

/**
 * OpenAI generation model configuration
 */
export const GENERATION_MODEL = "gpt-4o-mini";
