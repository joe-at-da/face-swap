import { NextRequest, NextResponse } from "next/server";

// Rate limiting state for parliament API requests
let lastRequestTime = 0;
const MIN_REQUEST_INTERVAL = 500; // 500ms between requests
const MAX_RETRIES = 2;
const RETRY_DELAY = 1000; // 1 second between retries

async function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForRateLimit(): Promise<void> {
  const now = Date.now();
  const timeSinceLastRequest = now - lastRequestTime;

  if (timeSinceLastRequest < MIN_REQUEST_INTERVAL) {
    const waitTime = MIN_REQUEST_INTERVAL - timeSinceLastRequest;
    await delay(waitTime);
  }

  lastRequestTime = Date.now();
}

// Generate a simple placeholder SVG image
function generatePlaceholderSVG(): string {
  return `<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
    <rect width="400" height="400" fill="#E5E7EB"/>
    <text x="50%" y="50%" font-family="Arial, sans-serif" font-size="16" fill="#6B7280" text-anchor="middle" dominant-baseline="middle">
      Portrait unavailable
    </text>
  </svg>`;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const imageUrl = searchParams.get("url");

    if (!imageUrl) {
      // Return placeholder for missing URL instead of error
      const placeholder = generatePlaceholderSVG();
      return new NextResponse(placeholder, {
        status: 200,
        headers: {
          "Content-Type": "image/svg+xml",
          "Cache-Control": "public, max-age=3600", // Cache placeholder for 1 hour
        },
      });
    }

    // Only allow proxying images from parliament.uk domains for security
    try {
      const url = new URL(imageUrl);
      if (!url.hostname.endsWith("parliament.uk")) {
        const placeholder = generatePlaceholderSVG();
        return new NextResponse(placeholder, {
          status: 200,
          headers: {
            "Content-Type": "image/svg+xml",
            "Cache-Control": "public, max-age=3600",
          },
        });
      }
    } catch {
      // Invalid URL, return placeholder
      const placeholder = generatePlaceholderSVG();
      return new NextResponse(placeholder, {
        status: 200,
        headers: {
          "Content-Type": "image/svg+xml",
          "Cache-Control": "public, max-age=3600",
        },
      });
    }

    // Try to fetch with retries
    let lastError: Error | null = null;
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      try {
        // Apply rate limiting before making the request
        await waitForRateLimit();

        // Fetch the image from the Parliament API
        const response = await fetch(imageUrl, {
          headers: {
            "User-Agent": "Parliament-Image-Proxy/1.0",
            Accept: "image/*",
          },
          // Longer timeout for first attempt
          signal: AbortSignal.timeout(attempt === 0 ? 10000 : 15000),
        });

        if (!response.ok) {
          // If rate limited, wait longer and retry
          if (response.status === 429 && attempt < MAX_RETRIES - 1) {
            console.warn(
              `Rate limited on attempt ${attempt + 1}, waiting ${RETRY_DELAY * (attempt + 1)}ms...`
            );
            await delay(RETRY_DELAY * (attempt + 1));
            continue;
          }

          // For other errors, log but don't retry
          console.error(
            `Failed to fetch image (attempt ${attempt + 1}): ${response.status} ${response.statusText}`
          );
          lastError = new Error(`HTTP ${response.status}`);
          continue;
        }

        // Get the image buffer
        const imageBuffer = await response.arrayBuffer();
        const contentType = response.headers.get("content-type") || "image/jpeg";

        // Return the image with aggressive caching headers
        return new NextResponse(imageBuffer, {
          status: 200,
          headers: {
            "Content-Type": contentType,
            "Cache-Control": "public, max-age=31536000, immutable", // Cache for 1 year
            "CDN-Cache-Control": "public, max-age=31536000, immutable",
            "Vercel-CDN-Cache-Control": "public, max-age=31536000, immutable",
          },
        });
      } catch (error) {
        lastError = error instanceof Error ? error : new Error("Unknown error");
        console.error(`Attempt ${attempt + 1} failed:`, lastError.message);

        // Wait before retry
        if (attempt < MAX_RETRIES - 1) {
          await delay(RETRY_DELAY);
        }
      }
    }

    // All retries failed, return placeholder
    console.error(
      `All ${MAX_RETRIES} attempts failed for ${imageUrl}:`,
      lastError?.message
    );
    const placeholder = generatePlaceholderSVG();
    return new NextResponse(placeholder, {
      status: 200,
      headers: {
        "Content-Type": "image/svg+xml",
        "Cache-Control": "public, max-age=300", // Cache failed image for 5 minutes
      },
    });
  } catch (error) {
    console.error("Image proxy error:", error);
    // Return placeholder on any unexpected error
    const placeholder = generatePlaceholderSVG();
    return new NextResponse(placeholder, {
      status: 200,
      headers: {
        "Content-Type": "image/svg+xml",
        "Cache-Control": "public, max-age=300",
      },
    });
  }
}
