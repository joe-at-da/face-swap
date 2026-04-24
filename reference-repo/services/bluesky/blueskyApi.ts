"use server";

import { AtpAgent, BlobRef, AppBskyVideoDefs } from "@atproto/api";

/**
 * Create a post on Bluesky with video upload
 * @param service - Bluesky service URL (e.g., https://bsky.social)
 * @param identifier - Bluesky account identifier/handle
 * @param password - Bluesky app password
 * @param message - Post text content
 * @param videoUrl - URL of the video to upload
 * @returns Post URI on success or error
 */
export const createBlueskyPostWithVideo = async (
  service: string,
  identifier: string,
  password: string,
  message: string,
  videoUrl: string
): Promise<{ error: string | null; data: string | null }> => {
  try {
    console.log("[Bluesky] Starting post creation with video", {
      service,
      identifier,
      videoUrl,
    });

    // Step 1: Create agent and login
    const agent = new AtpAgent({ service });
    await agent.login({ identifier, password });

    if (!agent.session) {
      return { error: "Failed to authenticate with Bluesky", data: null };
    }

    console.log("[Bluesky] Successfully logged in");

    // Step 2: Download video from URL
    console.log("[Bluesky] Downloading video from URL...");
    const videoResponse = await fetch(videoUrl);

    if (!videoResponse.ok) {
      return {
        error: `Failed to download video: ${videoResponse.status} ${videoResponse.statusText}`,
        data: null,
      };
    }

    const videoBuffer = await videoResponse.arrayBuffer();
    const videoData = new Uint8Array(videoBuffer);

    console.log(
      `[Bluesky] Video downloaded successfully (${videoData.length} bytes)`
    );

    // Step 3: Get service auth token for video upload
    // The audience should be the user's PDS DID
    // After login, the agent should know the user's PDS endpoint

    // Get PDS endpoint from the agent's internal state
    let pdsEndpoint: string | undefined;

    // Try to get from agent's pdsUrl or dispatchUrl
    if (!pdsEndpoint) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const dispatchUrl = (agent as any).dispatchUrl as URL | undefined;
      pdsEndpoint = dispatchUrl?.href || agent.pdsUrl?.href || undefined;
    }

    // Extract host from PDS endpoint
    let pdsHost: string;
    if (pdsEndpoint) {
      pdsHost = new URL(pdsEndpoint).host;
    } else {
      // Last resort: use the service URL (this will likely fail for users on different PDS)
      pdsHost = new URL(service).host;
      console.warn(
        "[Bluesky] Could not determine user's PDS, falling back to service URL"
      );
    }

    const pdsDid = `did:web:${pdsHost}`;

    console.log("[Bluesky] User's PDS endpoint:", pdsEndpoint);
    console.log("[Bluesky] Getting service auth token for PDS DID:", pdsDid);

    const { data: serviceAuth } = await agent.com.atproto.server.getServiceAuth(
      {
        aud: pdsDid,
        lxm: "com.atproto.repo.uploadBlob",
        exp: Math.floor(Date.now() / 1000) + 60 * 30, // 30 minutes
      }
    );

    const token = serviceAuth.token;
    console.log("[Bluesky] Got service auth token for video upload");

    // Step 4: Upload video to video service
    const videoFileName = videoUrl.split("/").pop() || "video.mp4";
    const uploadUrl = new URL(
      "https://video.bsky.app/xrpc/app.bsky.video.uploadVideo"
    );
    uploadUrl.searchParams.append("did", agent.session.did);
    uploadUrl.searchParams.append("name", videoFileName);

    console.log("[Bluesky] Uploading video to Bluesky video service...");

    const uploadResponse = await fetch(uploadUrl.toString(), {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "video/mp4",
        "Content-Length": String(videoData.length),
      },
      body: videoData,
    });

    const uploadResponseText = await uploadResponse.text();

    // Parse response
    let uploadData: AppBskyVideoDefs.JobStatus;
    try {
      uploadData = JSON.parse(uploadResponseText);
    } catch {
      console.error("[Bluesky] Invalid JSON response:", uploadResponseText);
      return {
        error: "Invalid response from Bluesky video service",
        data: null,
      };
    }

    // Check for errors in response (even if status is ok, there might be an error in body)
    const errorCode =
      uploadData.error ||
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (uploadData as any).jobStatus?.error;

    // Variable to hold the final blob
    let blob: BlobRef | undefined;

    if (!uploadResponse.ok || errorCode) {
      console.error("[Bluesky] Video upload failed:", uploadResponseText);

      // Check for error message in the response body as well
      const errorText =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (uploadData as any).error || errorCode || "";

      // Handle specific errors
      if (errorCode === "unconfirmed_email") {
        return {
          error:
            "Your Bluesky account email is not verified. Please verify your email in Bluesky settings before uploading videos.",
          data: null,
        };
      } else if (errorCode === "rate_limit") {
        return {
          error: "Bluesky video upload rate limit reached. Please try again later.",
          data: null,
        };
      } else if (errorCode === "already_exists") {
        // Video already exists - use the existing job to get the blob
        // The response contains jobId and state when video was already processed
        const existingJobId = uploadData.jobId;

        if (existingJobId) {
          console.log(
            "[Bluesky] Video already exists, retrieving from job:",
            existingJobId
          );

          try {
            const videoAgent = new AtpAgent({ service: "https://video.bsky.app" });
            const { data: status } = await videoAgent.app.bsky.video.getJobStatus({
              jobId: existingJobId,
            });

            if (status.jobStatus.blob) {
              blob = status.jobStatus.blob;
              console.log("[Bluesky] Retrieved existing video blob successfully");
            } else if (status.jobStatus.state === "JOB_STATE_COMPLETED") {
              // Job completed but no blob - this shouldn't happen, but handle it
              console.warn("[Bluesky] Job completed but no blob found");
              return {
                error: "Video processing completed but blob not available. Please try again.",
                data: null,
              };
            } else {
              // Job still processing or failed
              console.log("[Bluesky] Existing job state:", status.jobStatus.state);
              return {
                error: `Video processing state: ${status.jobStatus.state}. Please try again.`,
                data: null,
              };
            }
          } catch (jobError) {
            console.error("[Bluesky] Failed to retrieve existing job:", jobError);
            return {
              error: "Failed to retrieve existing video. Please try again.",
              data: null,
            };
          }
        } else {
          // No jobId in response - shouldn't happen but handle it
          return {
            error: "Video already exists but no job ID provided. Please try a different clip.",
            data: null,
          };
        }
      } else if (
        errorText.toLowerCase().includes("capacity") ||
        errorText.toLowerCase().includes("try again")
      ) {
        // Server capacity issues - user should retry later
        return {
          error: "Bluesky servers are currently busy. Please try again in a few minutes.",
          data: null,
        };
      } else {
        return {
          error: `Bluesky video upload error: ${errorText || "unknown"}`,
          data: null,
        };
      }
    }

    // If we got here via video service (no blob yet), poll for the blob
    if (!blob && uploadData.jobId) {
      const jobStatus = uploadData;
      console.log("[Bluesky] Video upload job started:", jobStatus.jobId);

      // Step 5: Poll for processing status
      blob = jobStatus.blob;
      const videoAgent = new AtpAgent({ service: "https://video.bsky.app" });

      let pollAttempts = 0;
      const maxPollAttempts = 120; // Max 2 minutes polling (1 second intervals)

      while (!blob && pollAttempts < maxPollAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        pollAttempts++;

        try {
          const { data: status } = await videoAgent.app.bsky.video.getJobStatus({
            jobId: jobStatus.jobId,
          });

          console.log(
            `[Bluesky] Video processing status (attempt ${pollAttempts}):`,
            status.jobStatus.state
          );

          if (status.jobStatus.state === "JOB_STATE_FAILED") {
            return {
              error: `Video processing failed: ${
                status.jobStatus.error || "Unknown error"
              }`,
              data: null,
            };
          }

          if (status.jobStatus.blob) {
            blob = status.jobStatus.blob;
          }
        } catch (pollError) {
          console.warn("[Bluesky] Error polling job status:", pollError);
          // Continue polling
        }
      }

      if (!blob) {
        return {
          error: "Video processing timed out after 2 minutes",
          data: null,
        };
      }

      console.log("[Bluesky] Video processing complete, blob ready");
    }

    // Final check - we should have a blob by now
    if (!blob) {
      return {
        error: "Failed to get video blob for posting",
        data: null,
      };
    }

    // Step 6: Get video aspect ratio (default to 9:16 for vertical video)
    // Since we're dealing with vertical clips, we'll use 9:16 ratio
    const aspectRatio = { width: 9, height: 16 };

    // Step 7: Create post with video embed
    console.log("[Bluesky] Creating post with video embed...");

    const postResult = await agent.post({
      text: message,
      langs: ["en"],
      embed: {
        $type: "app.bsky.embed.video",
        video: blob,
        aspectRatio,
      },
    });

    console.log("[Bluesky] Post created successfully:", postResult.uri);

    return { error: null, data: postResult.uri };
  } catch (error) {
    console.error("[Bluesky] Error creating post with video:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

/**
 * Create a text-only post on Bluesky (for when no video is provided)
 * @param service - Bluesky service URL
 * @param identifier - Bluesky account identifier/handle
 * @param password - Bluesky app password
 * @param message - Post text content
 * @returns Post URI on success or error
 */
export const createBlueskyTextPost = async (
  service: string,
  identifier: string,
  password: string,
  message: string
): Promise<{ error: string | null; data: string | null }> => {
  try {
    console.log("[Bluesky] Creating text-only post", {
      service,
      identifier,
    });

    const agent = new AtpAgent({ service });
    await agent.login({ identifier, password });

    if (!agent.session) {
      return { error: "Failed to authenticate with Bluesky", data: null };
    }

    const postResult = await agent.post({
      text: message,
      langs: ["en"],
    });

    console.log("[Bluesky] Text post created successfully:", postResult.uri);

    return { error: null, data: postResult.uri };
  } catch (error) {
    console.error("[Bluesky] Error creating text post:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

/**
 * Check if Bluesky credentials are valid
 * @param service - Bluesky service URL
 * @param identifier - Bluesky account identifier/handle
 * @param password - Bluesky app password
 * @returns true if credentials are valid, error otherwise
 */
export const validateBlueskyCredentials = async (
  service: string,
  identifier: string,
  password: string
): Promise<{ error: string | null; data: boolean }> => {
  try {
    const agent = new AtpAgent({ service });
    await agent.login({ identifier, password });

    if (!agent.session) {
      return { error: "Invalid credentials", data: false };
    }

    return { error: null, data: true };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : String(error),
      data: false,
    };
  }
};

/**
 * Get Bluesky profile data including avatar
 * @param service - Bluesky service URL (e.g., https://bsky.social)
 * @param identifier - Bluesky account identifier/handle
 * @param password - Bluesky app password
 * @returns Profile data including avatar URL
 */
export const getBlueskyProfile = async (
  service: string,
  identifier: string,
  password: string
): Promise<{
  error: string | null;
  data: { avatar?: string; displayName?: string } | null;
}> => {
  try {
    const agent = new AtpAgent({ service });
    await agent.login({ identifier, password });

    if (!agent.session) {
      return { error: "Invalid credentials", data: null };
    }

    // Use the handle from session, not the identifier (which could be email)
    const { data: profile } = await agent.app.bsky.actor.getProfile({
      actor: agent.session.handle,
    });

    return {
      error: null,
      data: {
        avatar: profile.avatar,
        displayName: profile.displayName,
      },
    };
  } catch (error) {
    console.error("[Bluesky] Error fetching profile:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};
