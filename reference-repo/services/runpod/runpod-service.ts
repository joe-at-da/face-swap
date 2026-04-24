/**
 * RunPod Service Layer
 * Handles RunPod API operations - database updates are handled by RunPod functions themselves
 *
 * All endpoints use queue-based async endpoint (POST /run)
 * - Video Processor: Process parliament videos
 * - Clip Creator: Create user clips
 * - Face Encoder: Process face encodings
 */

import { RunPodClient } from "./runpod-client";
import {
  VideoProcessorInput,
  ClipCreatorInput,
  FaceEncoderInput,
  RunPodApiError,
  RunPodConfig,
} from "./runpod-types";

export class RunPodService {
  private runPodClient: RunPodClient;

  constructor() {
    this.runPodClient = RunPodClient.fromEnv();
  }

  /**
   * Check if result is an error
   */
  private isError<T>(result: T | RunPodApiError): result is RunPodApiError {
    return result && typeof result === "object" && "error" in result;
  }

  /**
   * Process a parliament video by parliament_event_id
   * RunPod function handles all database updates internally
   * Returns job_id for async processing
   */
  async processParliamentVideo(parliamentEventId: string): Promise<{
    success: boolean;
    job_id?: string;
    error?: string;
  }> {
    console.log(
      `[RunPodService] Submitting parliament video processing: ${parliamentEventId}`
    );

    try {
      // Call RunPod API - it handles all database updates
      const input: VideoProcessorInput = {
        parliament_event_id: parliamentEventId,
      };
      const result = await this.runPodClient.processParliamentVideo(input);

      if (this.isError(result)) {
        console.error(
          "[RunPodService] RunPod video processing submission failed:",
          result.error
        );
        return {
          success: false,
          error: result.error,
        };
      }

      console.log(
        `[RunPodService] Parliament video processing job submitted: ${result.job_id}`
      );

      return {
        success: true,
        job_id: result.job_id,
      };
    } catch (error) {
      console.error(
        "[RunPodService] Parliament video processing submission error:",
        error
      );

      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  /**
   * Create a user clip by user_clip_id
   * Uses queue-based async endpoint (POST /run)
   * RunPod function handles all database updates internally
   * Returns job_id for async processing
   */
  async createUserClip(userClipId: string): Promise<{
    success: boolean;
    job_id?: string;
    error?: string;
  }> {
    console.log(`[RunPodService] Submitting user clip creation: ${userClipId}`);

    try {
      // Call RunPod API - it handles all database updates
      const input: ClipCreatorInput = { user_clip_id: userClipId };
      const result = await this.runPodClient.createUserClip(input);

      if (this.isError(result)) {
        console.error(
          "[RunPodService] RunPod clip creation submission failed:",
          result.error
        );
        return {
          success: false,
          error: result.error,
        };
      }

      console.log(
        `[RunPodService] User clip creation job submitted: ${result.job_id}`
      );

      return {
        success: true,
        job_id: result.job_id,
      };
    } catch (error) {
      console.error(
        "[RunPodService] User clip creation submission error:",
        error
      );

      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  /**
   * Process face encodings
   * Uses queue-based async endpoint (POST /run)
   * RunPod function handles all database updates internally
   * Returns job_id for async processing
   */
  async processFaceEncodings(detectionThreshold: number = 0.65): Promise<{
    success: boolean;
    job_id?: string;
    error?: string;
  }> {
    console.log(
      `[RunPodService] Submitting face encodings processing with threshold: ${detectionThreshold}`
    );

    try {
      const input: FaceEncoderInput = { detection_threshold: detectionThreshold };
      const result = await this.runPodClient.processFaceEncodings(input);

      if (this.isError(result)) {
        console.error(
          "[RunPodService] RunPod face encoding submission failed:",
          result.error
        );
        return {
          success: false,
          error: result.error,
        };
      }

      console.log(
        `[RunPodService] Face encoding processing job submitted: ${result.job_id}`
      );

      return {
        success: true,
        job_id: result.job_id,
      };
    } catch (error) {
      console.error(
        "[RunPodService] Face encoding processing submission error:",
        error
      );

      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  /**
   * Get RunPod client configuration (for debugging)
   */
  getConfig(): Partial<RunPodConfig> {
    return this.runPodClient.getConfig();
  }
}
