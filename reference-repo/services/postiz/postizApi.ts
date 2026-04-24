import "server-only";
import { postizDb } from "./postizDb";
import { SUPPORTED_PLATFORMS } from "@/lib/supportedPlatforms";
import { generateId } from "@/lib/idGenerator";

const POSTIZ_API_URL = process.env.POSTIZ_API_URL!;

export const canRegisterUserToPostiz = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${POSTIZ_API_URL}auth/can-register`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });
    const data = await response.json();
    console.log("canRegisterUserToPostiz data:", data);
    return data && data.register;
  } catch (error) {
    console.error("Error checking if user can register to Postiz:", error);
    return false;
  }
};

export const signupUserToPostiz = async (
  email: string,
  password: string,
  company: string
) => {
  try {
    // const canRegister = await canRegisterUserToPostiz();
    // if (!canRegister) {
    //   return { error: "User cannot register to Postiz", data: null };
    // }

    const body = {
      email,
      password,
      company,
      provider: "LOCAL",
      providerToken: "",
    };

    const response = await fetch(`${POSTIZ_API_URL}auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      // Handle both JSON and plain text error responses
      const responseText = await response.text();
      let errorMessage = "Failed to register user to Postiz";

      try {
        const errorData = JSON.parse(responseText);
        errorMessage = errorData.message || errorMessage;
      } catch {
        // Response is plain text, not JSON
        errorMessage = responseText || errorMessage;
      }

      // If email already exists, try to activate and get existing API key
      if (
        errorMessage.toLowerCase().includes("email already exists") ||
        errorMessage.toLowerCase().includes("already registered")
      ) {
        console.log(
          "Email already exists in Postiz, attempting to retrieve existing account..."
        );

        // Try to activate (in case it wasn't activated before)
        const activateResult = await activateUserToPostiz(email);
        if (activateResult.error) {
          console.warn("Could not activate existing user:", activateResult.error);
          // Continue anyway - user might already be activated
        }

        // Try to get the existing API key
        const apiKeyResult = await getUserApiKey(email);
        if (apiKeyResult.error) {
          return {
            error: `Email already exists but could not retrieve API key: ${apiKeyResult.error}`,
            data: null,
          };
        }

        return { error: null, data: apiKeyResult.data };
      }

      throw new Error(errorMessage);
    }

    const activateResult = await activateUserToPostiz(email);

    if (activateResult.error) {
      return { error: activateResult.error, data: null };
    }

    const apiKeyResult = await getUserApiKey(email);
    if (apiKeyResult.error) {
      return { error: apiKeyResult.error, data: null };
    }

    return { error: null, data: apiKeyResult.data };
  } catch (error) {
    console.error("Error signing up user to Postiz:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

export const activateUserToPostiz = async (email: string) => {
  try {
    const result = await postizDb`
        UPDATE "User" 
        SET activated = true 
        WHERE email = ${email}
        RETURNING *
      `;

    if (result.length === 0) {
      return { error: "User not found", data: null };
    }

    return { error: null, data: result[0] };
  } catch (error) {
    console.error("Error activating user to Postiz:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

export const getUserApiKey = async (email: string) => {
  try {
    const result = await postizDb`
          SELECT o."apiKey" 
FROM "User" u 
INNER JOIN "UserOrganization" uo ON u.id = uo."userId"
INNER JOIN "Organization" o ON uo."organizationId" = o.id
WHERE u.email = ${email}
AND uo.disabled = false 
LIMIT 1
        `;

    if (result.length === 0) {
      return { error: "User or API key not found", data: null };
    }

    return { error: null, data: result[0].apiKey };
  } catch (error) {
    console.error("Error getting user info:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

export const loginUserToPostiz = async (email: string, password: string) => {
  try {
    const body = {
      email,
      password,
      provider: "LOCAL",
      providerToken: "",
    };
    const response = await fetch(`${POSTIZ_API_URL}auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    const authCookie = response.headers.get("set-cookie");
    const data = await response.json();
    console.log("loginUserToPostiz data:", data);
    return { error: null, data: authCookie };
  } catch (error) {
    console.error("Error Logging in user to Postiz:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

export const connectUserPostizToTwitter = async (authCookie: string) => {
  try {
    const response = await fetch(`${POSTIZ_API_URL}integrations/social/x`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Cookie: authCookie,
      },
    });
    const data = await response.json();
    console.log("connectUserPostizToTwitter data:", data);
    return { error: null, data: data.url || null };
  } catch (error) {
    console.error("Error Logging in user to Postiz:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

export const getConnectSocialMediaAccounts = async (email: string) => {
  try {
    // Query database to get user's connected integrations
    // Include inBetweenSteps to know if Facebook page selection is needed
    const connectedIntegrations = await postizDb`
      SELECT
        i.id,
        i.name,
        i."providerIdentifier",
        i.picture,
        i.profile,
        i.disabled,
        i."inBetweenSteps"
      FROM "Integration" i
      INNER JOIN "UserOrganization" uo ON i."organizationId" = uo."organizationId"
      INNER JOIN "User" u ON uo."userId" = u.id
      WHERE u.email = ${email}
        AND i.disabled = false
        AND uo.disabled = false
        AND i."deletedAt" IS NULL
    `;

    // Create a map of connected platforms for quick lookup
    const connectedMap = new Map(
      connectedIntegrations.map((integration) => [
        integration.providerIdentifier,
        {
          integrationId: integration.id,
          name: integration.name,
          picture: integration.picture,
          profile: integration.profile,
          inBetweenSteps: integration.inBetweenSteps,
        },
      ])
    );

    // Map all supported platforms with their connection status
    const platforms = SUPPORTED_PLATFORMS.map((platform) => {
      const connectedData = connectedMap.get(platform.identifier);

      // For Facebook and YouTube: if inBetweenSteps is true, page/channel selection is needed
      // Don't show as fully connected until page/channel is selected
      const isFullyConnected = connectedData
        ? platform.identifier === "facebook" || platform.identifier === "youtube"
          ? !connectedData.inBetweenSteps
          : true
        : false;

      return {
        name: platform.name,
        identifier: platform.identifier,
        ...("toolTip" in platform ? { toolTip: platform.toolTip } : {}),
        isConnected: isFullyConnected,
        // Include inBetweenSteps for Facebook/YouTube to show "page/channel not selected" state
        ...(connectedData && {
          integrationId: connectedData.integrationId,
          profile: connectedData.profile,
          profileName: connectedData.name,
          picture: connectedData.picture,
          inBetweenSteps: connectedData.inBetweenSteps || false,
        }),
      };
    });

    return {
      error: null,
      data: platforms,
    };
  } catch (error) {
    console.error("Error getting connected social media accounts:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

/**
 * Disconnect a social media integration
 * @param email - User's Postiz email
 * @param password - User's Postiz password
 * @param integrationId - Integration ID to disconnect
 * @returns Success or error
 */
export const disconnectSocialMediaIntegration = async (
  email: string,
  password: string,
  integrationId: string
) => {
  try {
    // Step 1: Login to get authentication cookie
    const loginResult = await loginUserToPostiz(email, password);

    if (loginResult.error || !loginResult.data) {
      return {
        error: loginResult.error || "Failed to login to Postiz",
        data: null,
      };
    }

    const authCookie = loginResult.data;

    // Step 2: Delete integration via Postiz API
    const response = await fetch(
      `${POSTIZ_API_URL}integrations`,
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Cookie: authCookie,
        },
        body: JSON.stringify({ id: integrationId }),
      }
    );

    if (!response.ok) {
      const responseText = await response.text();
      console.error(
        `Failed to disconnect integration:`,
        response.status,
        responseText
      );
      return {
        error: `Failed to disconnect (HTTP ${response.status})`,
        data: null,
      };
    }

    return {
      error: null,
      data: true,
    };
  } catch (error) {
    console.error("Error disconnecting social media integration:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

/**
 * Get OAuth URL for connecting a social media platform
 * @param email - User's Postiz email
 * @param password - User's Postiz password
 * @param platform - Platform identifier (e.g., 'x', 'linkedin', 'facebook')
 * @returns OAuth URL for the platform or error
 */
export const getPostizOAuthUrl = async (
  email: string,
  password: string,
  platform: string
) => {
  try {
    // Step 1: Login to get authentication cookie
    const loginResult = await loginUserToPostiz(email, password);

    if (loginResult.error || !loginResult.data) {
      return {
        error: loginResult.error || "Failed to login to Postiz",
        data: null,
      };
    }

    const authCookie = loginResult.data;

    // Step 2: Use cookie to get OAuth URL
    const response = await fetch(
      `${POSTIZ_API_URL}integrations/social/${platform}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Cookie: authCookie,
        },
      }
    );

    // Get response text first to handle both JSON and non-JSON responses
    const responseText = await response.text();

    console.log("responseText:", responseText);

    if (!response.ok) {
      // Try to parse as JSON, fallback to text
      let errorMessage = `Failed to get OAuth URL (HTTP ${response.status})`;
      try {
        const errorData = JSON.parse(responseText);
        errorMessage = errorData.message || errorMessage;
      } catch {
        // Not JSON, use text or status text
        errorMessage = responseText || response.statusText || errorMessage;
      }

      console.error(
        `Postiz OAuth URL error for ${platform}:`,
        response.status,
        responseText
      );

      return {
        error: errorMessage,
        data: null,
      };
    }

    // Parse successful response
    let data;
    try {
      data = JSON.parse(responseText);
    } catch {
      return {
        error: "Invalid response from Postiz API",
        data: null,
      };
    }

    return {
      error: null,
      data: data.url || null,
    };
  } catch (error) {
    console.error("Error getting Postiz OAuth URL:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

/**
 * Upload a video file to Postiz using cookie authentication
 * @param email - User's Postiz email
 * @param password - User's Postiz password
 * @param videoBuffer - Video file as Buffer
 * @param extension - File extension (e.g., 'mp4', 'mov')
 * @returns Uploaded file URL/path or error
 */
export const uploadVideoToPostiz = async (
  email: string,
  password: string,
  videoBuffer: Buffer,
  extension: string
) => {
  try {
    // Step 1: Login to get authentication cookie
    const loginResult = await loginUserToPostiz(email, password);

    if (loginResult.error || !loginResult.data) {
      return {
        error: loginResult.error || "Failed to login to Postiz",
        data: null,
      };
    }

    const authCookie = loginResult.data;

    // Step 2: Create form data for file upload
    const formData = new FormData();

    // Convert Buffer to Blob
    const blob = new Blob([new Uint8Array(videoBuffer)], {
      type: `video/${extension}`
    });

    // Append file to form data
    formData.append('file', blob, `video.${extension}`);

    // Step 3: Upload with auth cookie (try /media/upload-simple first)
    const response = await fetch(`${POSTIZ_API_URL}media/upload-simple`, {
      method: "POST",
      headers: {
        Cookie: authCookie, // Use cookie instead of API key
      },
      body: formData,
    });

    const responseText = await response.text();

    if (!response.ok) {
      let errorMessage = `Failed to upload video (HTTP ${response.status})`;
      try {
        const errorData = JSON.parse(responseText);
        errorMessage = errorData.message || errorData.msg || errorMessage;
      } catch {
        errorMessage = responseText || response.statusText || errorMessage;
      }

      console.error(
        "Postiz upload error:",
        response.status,
        responseText
      );

      return {
        error: errorMessage,
        data: null,
      };
    }

    // Parse successful response
    let data;
    try {
      data = JSON.parse(responseText);
    } catch {
      return {
        error: "Invalid response from Postiz upload API",
        data: null,
      };
    }

    // Return the uploaded file URL/path
    return {
      error: null,
      data: data.url || data.path || data,
    };
  } catch (error) {
    console.error("Error uploading video to Postiz:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

/**
 * Get next available time slot for scheduling a post on a platform
 * @param email - User's Postiz email
 * @param password - User's Postiz password
 * @param integrationId - Integration ID to get next slot for
 * @returns Next available slot datetime (ISO 8601) or error
 */
export const getNextAvailableSlot = async (
  email: string,
  password: string,
  integrationId: string
) => {
  try {
    // Step 1: Login to get authentication cookie
    const loginResult = await loginUserToPostiz(email, password);

    if (loginResult.error || !loginResult.data) {
      return {
        error: loginResult.error || "Failed to login to Postiz",
        data: null,
      };
    }

    const authCookie = loginResult.data;

    // Step 2: Get next available slot
    const response = await fetch(
      `${POSTIZ_API_URL}posts/find-slot/${integrationId}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Cookie: authCookie,
        },
      }
    );

    const responseText = await response.text();

    if (!response.ok) {
      let errorMessage = `Failed to get next slot (HTTP ${response.status})`;
      try {
        const errorData = JSON.parse(responseText);
        errorMessage = errorData.message || errorMessage;
      } catch {
        errorMessage = responseText || response.statusText || errorMessage;
      }

      console.error(
        "Postiz get next slot error:",
        response.status,
        responseText
      );

      return {
        error: errorMessage,
        data: null,
      };
    }

    // Parse successful response
    let data: { date: string };
    try {
      data = JSON.parse(responseText);
    } catch {
      return {
        error: "Invalid response from Postiz API",
        data: null,
      };
    }

    return {
      error: null,
      data: data.date, // ISO 8601 datetime string
    };
  } catch (error) {
    console.error("Error getting next available slot:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

/**
 * Create a social media post via Postiz API using cookie authentication
 * @param email - User's Postiz email
 * @param password - User's Postiz password
 * @param integrationIds - Array of integration IDs to post to
 * @param platformIdentifiers - Array of platform identifiers (e.g., ['x', 'youtube']) matching integrationIds order
 * @param message - Post content/message
 * @param mediaUrls - Array of media URLs (video/image) - can be external URLs or Postiz-uploaded file paths
 * @param scheduleTime - Optional ISO 8601 datetime for scheduling (null for immediate post)
 * @param videoTitle - Optional video title for YouTube (defaults to message truncated to 100 chars)
 * @returns Array of {postId, integration} objects on success or error
 */
export const createPostizPost = async (
  email: string,
  password: string,
  integrationIds: string[],
  platformIdentifiers: string[],
  message: string,
  mediaUrls: string[],
  scheduleTime?: string | null,
  videoTitle?: string
) => {
  try {
    // Step 1: Login to get authentication cookie
    const loginResult = await loginUserToPostiz(email, password);

    if (loginResult.error || !loginResult.data) {
      return {
        error: loginResult.error || "Failed to login to Postiz",
        data: null,
      };
    }

    const authCookie = loginResult.data;

    // Step 2: Download videos from URLs and upload to Postiz storage (server-side)
    const uploadedMedia: Array<{ id: string; path: string }> = [];

    if (mediaUrls && mediaUrls.length > 0) {
      for (const videoUrl of mediaUrls) {
        try {
          console.log("Downloading video from URL:", videoUrl);

          // Step 2a: Download video to server memory
          const videoResponse = await fetch(videoUrl);

          if (!videoResponse.ok) {
            console.error(
              "Failed to download video:",
              videoResponse.status,
              videoResponse.statusText
            );
            continue; // Skip this video but continue with others
          }

          // Convert to Buffer for upload
          const videoArrayBuffer = await videoResponse.arrayBuffer();
          const videoBuffer = Buffer.from(videoArrayBuffer);

          console.log(`Video downloaded successfully (${videoBuffer.length} bytes), uploading to Postiz...`);

          // Step 2b: Create FormData for upload
          const formData = new FormData();

          // Convert Buffer to Blob
          const blob = new Blob([videoBuffer], { type: 'video/mp4' });

          // Append file to form data
          formData.append('file', blob, 'video.mp4');

          // Step 2c: Upload to Postiz via /media/upload-simple
          const uploadResponse = await fetch(
            `${POSTIZ_API_URL}media/upload-simple`,
            {
              method: "POST",
              headers: {
                Cookie: authCookie,
              },
              body: formData,
            }
          );

          const uploadText = await uploadResponse.text();

          if (!uploadResponse.ok) {
            console.error(
              "Failed to upload video to Postiz:",
              uploadResponse.status,
              uploadText
            );
            continue; // Skip this video but continue with others
          }

          const uploadData = JSON.parse(uploadText);
          console.log("Video uploaded to Postiz successfully:", uploadData);

          // Postiz returns uploaded media with id and path
          if (uploadData.id && uploadData.path) {
            uploadedMedia.push({
              id: uploadData.id,
              path: uploadData.path,
            });
          }
        } catch (uploadError) {
          console.error("Error processing video:", uploadError);
          // Continue with other videos even if one fails
        }
      }
    }

    // Validate that at least one video was uploaded when videos were provided
    if (mediaUrls && mediaUrls.length > 0 && uploadedMedia.length === 0) {
      return {
        error: "Failed to upload video(s) to Postiz. Please try again.",
        data: null,
      };
    }

    // Step 3: Prepare request body in Postiz API format
    const groupId = generateId();
    const valueId = generateId();

    // Generate YouTube title from message if not provided
    const youtubeTitle = videoTitle || message.replace(/<[^>]*>/g, '').substring(0, 100) || "Video";

    const body = {
      type: scheduleTime ? "schedule" : "now",
      tags: [],
      shortLink: false,
      date: scheduleTime || new Date().toISOString(), // Always include date (current time for immediate posts)
      posts: integrationIds.map((integrationId, index) => {
        const platformIdentifier = platformIdentifiers[index];

        // YouTube requires specific settings (title, type, selfDeclaredMadeForKids)
        // Other platforms (X/Twitter, LinkedIn, etc.) use generic settings
        const settings = platformIdentifier === "youtube"
          ? {
              title: youtubeTitle,
              type: "public" as const,
              selfDeclaredMadeForKids: "no" as const,
              tags: []
            }
          : {
              who_can_reply_post: "everyone",
              community: "",
              active_thread_finisher: false,
              thread_finisher: "That's a wrap!\n\nIf you enjoyed this thread:\n\n1. Follow me @TaoufiqVeedoo for more of these\n2. RT the tweet below to share this thread with your audience\n",
              "plug--x-repost-post-users--integrations": []
            };

        return {
          integration: { id: integrationId },
          group: groupId,
          settings,
          value: [
            {
              id: valueId,
              content: `<p>${message.replace(/\n/g, "<br>")}</p>`, // Convert newlines to HTML
              image: uploadedMedia, // Use uploaded media objects with id and path
            },
          ],
        };
      }),
    };

    // Log the request body for debugging
    console.log("Postiz create post request body:", JSON.stringify(body, null, 2));

    // Step 4: Create post with cookie authentication
    const response = await fetch(`${POSTIZ_API_URL}posts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: authCookie, // Use cookie instead of API key
      },
      body: JSON.stringify(body),
    });

    const responseText = await response.text();

    if (!response.ok) {
      // Try to parse as JSON for error message
      let errorMessage = `Failed to create post (HTTP ${response.status})`;
      try {
        const errorData = JSON.parse(responseText);
        errorMessage = errorData.message || errorMessage;
      } catch {
        errorMessage = responseText || response.statusText || errorMessage;
      }

      console.error(
        "Postiz create post error:",
        response.status,
        responseText
      );

      return {
        error: errorMessage,
        data: null,
      };
    }

    // Parse successful response - returns array of {postId, integration} objects
    let data: Array<{ postId: string; integration: string }>;
    try {
      data = JSON.parse(responseText);
      // Log the response for debugging
      console.log("Postiz create post response (raw):", responseText);
      console.log("Postiz create post response (parsed):", JSON.stringify(data, null, 2));
    } catch {
      console.error("Postiz create post response (unparseable):", responseText);
      return {
        error: "Invalid response from Postiz API",
        data: null,
      };
    }

    // Validate response contains actual posts
    if (!Array.isArray(data) || data.length === 0) {
      return {
        error: "Postiz API returned no posts. The post may not have been created.",
        data: null,
      };
    }

    // Validate each post has required fields
    for (const post of data) {
      if (!post.postId || !post.integration) {
        return {
          error: "Invalid response from Postiz API: missing post data",
          data: null,
        };
      }
    }

    return {
      error: null,
      data: data,
    };
  } catch (error) {
    console.error("Error creating Postiz post:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
};

// Note: Bluesky posting is now handled directly via @atproto/api
// See services/bluesky/blueskyApi.ts for the implementation
