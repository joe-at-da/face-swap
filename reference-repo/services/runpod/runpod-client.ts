/**
 * RunPod API Client
 * Handles communication with RunPod serverless endpoints
 */

import {
  RunPodConfig,
  RunPodApiRequest,
  RunPodApiError,
  VideoProcessorInput,
  ClipCreatorInput,
  FaceEncoderInput,
} from "./runpod-types";

export class RunPodClient {
  private readonly baseUrl = "https://api.runpod.ai/v2";
  private readonly config: RunPodConfig;

  constructor(config: RunPodConfig) {
    this.config = config;
    this.validateConfig();
  }

  /**
   * Validate RunPod configuration
   */
  private validateConfig(): void {
    if (!this.config.apiKey) {
      throw new Error("RunPod API key is required");
    }
  }

  /**
   * Create RunPod configuration from environment variables
   */
  static fromEnv(): RunPodClient {
    const config: RunPodConfig = {
      apiKey: process.env.RUNPOD_API_KEY || "",
      videoProcessorEndpoint: process.env.RUNPOD_VIDEO_PROCESSOR_ENDPOINT || "",
      clipCreatorEndpoint: process.env.RUNPOD_CLIP_CREATOR_ENDPOINT || "",
      faceEncoderEndpoint: process.env.RUNPOD_FACE_ENCODER_ENDPOINT || "",
    };

    return new RunPodClient(config);
  }

  /**
   * Make async HTTP request to RunPod API (fire-and-forget)
   */
  private async makeAsyncRequest<TInput>(
    endpoint: string,
    input: TInput,
    timeout: number = 30000 // 30 seconds timeout for job submission
  ): Promise<{ job_id: string } | RunPodApiError> {
    try {
      const url = `${this.baseUrl}/${endpoint}/run`;

      console.log(`[RunPod] Making async request to: ${url}`);
      console.log(`[RunPod] Input:`, JSON.stringify(input, null, 2));

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.config.apiKey}`,
        },
        body: JSON.stringify({
          input,
        } as RunPodApiRequest<TInput>),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[RunPod] API error ${response.status}:`, errorText);

        return {
          error: `RunPod API error: ${response.status} ${response.statusText}`,
          details: errorText,
          statusCode: response.status,
        };
      }

      const result = await response.json();

      console.log(`[RunPod] Job submitted with ID:`, result.id);

      if (result.id) {
        return { job_id: result.id };
      }

      return {
        error: "No job ID returned from RunPod",
        details: result,
      };
    } catch (error) {
      console.error("[RunPod] Request failed:", error);

      if (error instanceof Error) {
        if (error.name === "AbortError") {
          return {
            error: `RunPod request timed out after ${timeout / 1000} seconds`,
            details: error.message,
          };
        }

        return {
          error: `RunPod request failed: ${error.message}`,
          details: error,
        };
      }

      return {
        error: "Unknown RunPod request error",
        details: error,
      };
    }
  }

  /**
   * Process a parliament video using the video processor endpoint (async)
   */
  async processParliamentVideo(
    input: VideoProcessorInput,
    timeout?: number
  ): Promise<{ job_id: string } | RunPodApiError> {
    if (!this.config.videoProcessorEndpoint) {
      return { error: "Video processor endpoint is not configured" };
    }

    console.log("[RunPod] Starting parliament video processing...");

    return await this.makeAsyncRequest<VideoProcessorInput>(
      this.config.videoProcessorEndpoint,
      input,
      timeout || 30000 // 30 seconds for job submission
    );
  }

  /**
   * Create a user clip using the clip creator queue endpoint (async)
   * Uses POST /run to submit job and returns job_id
   */
  async createUserClip(
    input: ClipCreatorInput,
    timeout?: number
  ): Promise<{ job_id: string } | RunPodApiError> {
    if (!this.config.clipCreatorEndpoint) {
      return { error: "Clip creator endpoint is not configured" };
    }

    console.log("[RunPod] Submitting user clip creation to queue...");

    return await this.makeAsyncRequest<ClipCreatorInput>(
      this.config.clipCreatorEndpoint,
      input,
      timeout || 30000 // 30 seconds for job submission
    );
  }

  /**
   * Process face encodings using the face encoder queue endpoint (async)
   * Uses POST /run to submit job and returns job_id
   */
  async processFaceEncodings(
    input: FaceEncoderInput = {},
    timeout?: number
  ): Promise<{ job_id: string } | RunPodApiError> {
    if (!this.config.faceEncoderEndpoint) {
      return { error: "Face encoder endpoint is not configured" };
    }

    console.log("[RunPod] Submitting face encoding processing to queue...");

    return await this.makeAsyncRequest<FaceEncoderInput>(
      this.config.faceEncoderEndpoint,
      input,
      timeout || 30000 // 30 seconds for job submission
    );
  }

  /**
   * Get configuration (for debugging)
   */
  getConfig(): Partial<RunPodConfig> {
    return {
      videoProcessorEndpoint: this.config.videoProcessorEndpoint,
      clipCreatorEndpoint: this.config.clipCreatorEndpoint,
      faceEncoderEndpoint: this.config.faceEncoderEndpoint,
      // Don't expose API key
    };
  }
}
