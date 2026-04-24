"use server";

import { readFile } from "node:fs/promises";
import OpenAI from "openai";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { extractAudioSegment } from "@/lib/extractAudioSegment";
import { ErrorLogger } from "@/lib/errorLogger";
import type { Caption } from "@/types/remotionEditor";

// ─── In-memory rate limiter (per-user, 10 requests/hour) ────────────────────

const RATE_LIMIT_MAX = 10;
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour

const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

function checkRateLimit(userId: string): boolean {
  const now = Date.now();
  const entry = rateLimitMap.get(userId);

  if (!entry || now >= entry.resetAt) {
    rateLimitMap.set(userId, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }

  if (entry.count >= RATE_LIMIT_MAX) {
    return false;
  }

  entry.count++;
  return true;
}

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

/** Max duration per chunk sent to Whisper (10 minutes). */
const CHUNK_DURATION_MS = 600_000;

/** Max total duration allowed (60 minutes = 6 chunks). */
const MAX_TOTAL_DURATION_MS = 3_600_000;

/**
 * Generate subtitles for a video clip using OpenAI Whisper API.
 *
 * Extracts audio-only from the source video using ffmpeg (no full video
 * download needed — uses HTTP range seeking). For clips longer than 10
 * minutes, automatically chunks into segments and merges results.
 *
 * SECURITY: Accepts clipId (not videoUrl) to prevent SSRF attacks.
 * The video URL is resolved from the database server-side.
 *
 * @param clipId - The parliament_member_clips ID
 * @param startMs - Start time in the source video (ms)
 * @param endMs - End time in the source video (ms)
 */
export async function generateSubtitles(
  clipId: string,
  startMs: number,
  endMs: number
): Promise<{ captions: Caption[]; error?: string }> {
  // Validate inputs
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!clipId || typeof clipId !== "string" || !uuidRegex.test(clipId)) {
    return { captions: [], error: "Invalid clip ID format" };
  }
  if (startMs < 0 || endMs <= startMs) {
    return { captions: [], error: "Invalid time range" };
  }
  if (endMs - startMs > MAX_TOTAL_DURATION_MS) {
    return { captions: [], error: "Clip too long (max 60 minutes)" };
  }

  // Resolve video URL from database (SSRF prevention)
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return { captions: [], error: "Unauthorized" };
  }

  // Rate limit: 10 requests per hour per user
  if (!checkRateLimit(user.id)) {
    return { captions: [], error: "Rate limit exceeded. Please try again later." };
  }

  const { data: clip, error: clipError } = await supabase
    .from("parliament_member_clips")
    .select("full_video_path")
    .eq("id", clipId)
    .eq("is_deleted", false)
    .single();

  if (clipError || !clip?.full_video_path) {
    return { captions: [], error: "Clip not found or no video available" };
  }

  const videoUrl = clip.full_video_path;
  const totalDurationMs = endMs - startMs;

  try {
    // Calculate chunks (10-min segments)
    const chunkCount = Math.ceil(totalDurationMs / CHUNK_DURATION_MS);
    const allCaptions: Caption[] = [];

    for (let i = 0; i < chunkCount; i++) {
      const chunkStartMs = startMs + i * CHUNK_DURATION_MS;
      const chunkEndMs = Math.min(startMs + (i + 1) * CHUNK_DURATION_MS, endMs);
      const chunkOffsetMs = i * CHUNK_DURATION_MS; // Offset within the full clip

      const chunkCaptions = await transcribeChunk(
        videoUrl,
        chunkStartMs,
        chunkEndMs,
        chunkOffsetMs
      );

      allCaptions.push(...chunkCaptions);
    }

    return { captions: allCaptions };
  } catch (err) {
    ErrorLogger.logError(err, {
      component: "generateSubtitles",
      action: "transcribe",
      feature: "remotion-editor",
      additionalContext: { clipId },
    });
    return {
      captions: [],
      error: "Failed to generate subtitles. Please try again.",
    };
  }
}

/**
 * Transcribe a single chunk of the video using ffmpeg extraction + Whisper.
 *
 * @param videoUrl - Source video URL
 * @param chunkStartMs - Absolute start position in the source video
 * @param chunkEndMs - Absolute end position in the source video
 * @param chunkOffsetMs - Offset of this chunk within the full clip (for timestamp merging)
 * @returns Captions with timestamps relative to the full clip start (0ms = clip start)
 */
async function transcribeChunk(
  videoUrl: string,
  chunkStartMs: number,
  chunkEndMs: number,
  chunkOffsetMs: number
): Promise<Caption[]> {
  // Extract audio-only from the specific time range
  const { filePath, cleanup } = await extractAudioSegment(
    videoUrl,
    chunkStartMs,
    chunkEndMs
  );

  try {
    // Read the extracted audio file and send to Whisper
    const audioBuffer = new Uint8Array(await readFile(filePath));
    const audioFile = new File([audioBuffer], "segment.mp3", {
      type: "audio/mpeg",
    });

    const transcription = await openai.audio.transcriptions.create({
      file: audioFile,
      model: "whisper-1",
      response_format: "verbose_json",
      timestamp_granularities: ["word"],
      language: "en",
    });

    // Map Whisper response to our Caption format
    const captions: Caption[] = [];

    const words = (transcription as unknown as Record<string, unknown>)
      .words as
      | Array<{ word: string; start: number; end: number }>
      | undefined;

    if (words && Array.isArray(words)) {
      for (let i = 0; i < words.length; i++) {
        const word = words[i];
        // Whisper timestamps are in seconds relative to extracted chunk (0 = chunk start)
        // Convert to ms and offset by chunkOffsetMs to make relative to full clip start
        const wordStartMs = word.start * 1000 + chunkOffsetMs;
        const wordEndMs = word.end * 1000 + chunkOffsetMs;

        // Prepend space to all words except the first.
        // @remotion/captions createTikTokStyleCaptions needs leading spaces for:
        // 1. Page breaks via text.startsWith(' ')
        // 2. Word spacing via currentText += text
        const text =
          i === 0 ? word.word.trimStart() : " " + word.word.trim();

        captions.push({
          text,
          startMs: wordStartMs,
          endMs: wordEndMs,
          timestampMs: wordStartMs,
          confidence: null,
        });
      }
    } else if (transcription.text) {
      // Fallback: no word-level timestamps, create a single caption for this chunk
      const chunkDurationMs = chunkEndMs - chunkStartMs;
      captions.push({
        text: transcription.text,
        startMs: chunkOffsetMs,
        endMs: chunkOffsetMs + chunkDurationMs,
        timestampMs: chunkOffsetMs,
        confidence: null,
      });
    }

    return captions;
  } finally {
    await cleanup();
  }
}
