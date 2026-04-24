#!/usr/bin/env tsx

// Load environment variables from .env file
import "dotenv/config";

import { createClient } from "@supabase/supabase-js";
import { chromium, Browser, Page } from "playwright";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { Tables, TablesInsert, Database } from "@/supabaseTypes";
import * as crypto from "crypto";
import * as fs from "fs";
import * as path from "path";
import * as faceapi from "@vladmandic/face-api";
import { Canvas, Image, ImageData, loadImage } from "canvas";

// Create Supabase client for scripts (without server-only)
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:55321";
const supabaseKey = process.env.SUPABASE_SERVICE_KEY || "";

if (!supabaseKey) {
  console.warn(
    "Warning: SUPABASE_SERVICE_KEY not set. Using default local Supabase key.",
  );
}

const supabaseAdminClient = createClient<Database>(
  supabaseUrl,
  supabaseKey ||
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  },
);

type ParliamentMember = Tables<"parliament_members">;
type PortraitInsert = TablesInsert<"parliament_member_portraits">;

// Configuration
const MAX_IMAGES_PER_MP = 100;
const BUCKET_NAME = process.env.DO_SPACES_BUCKET!;
const FOLDER_PREFIX = "mp_pictures";
const DRY_RUN_FOLDER = "./mp-images-dry-run";
const DOWNLOAD_FOLDER = "./mp-images-downloaded";
const VALID_FOLDER = "./mp-images-valid";
const INVALID_FOLDER = "./mp-images-invalid";
const _MIN_IMAGE_SIZE = 200; // Minimum dimension in pixels
const _PREFERRED_IMAGE_SIZE = 500; // Preferred dimension in pixels
const DELAY_BETWEEN_REQUESTS = 2000; // 2 seconds between Playwright navigations
const RETRY_ATTEMPTS = 3;
const RETRY_DELAY_BASE = 2000; // Base delay for exponential backoff
const PAGE_NAVIGATION_TIMEOUT = 60000; // 60 seconds timeout for page navigation
const PAGE_NAVIGATION_RETRIES = 2; // Retry page navigation up to 2 times

// Check for dry-run mode
const isDryRun = process.argv.includes("--dry-run");

// Environment variables (only required if not dry-run)
const endpoint = process.env.DO_SPACES_ENDPOINT;
const region = process.env.DO_SPACES_REGION;
const accessKeyId = process.env.DO_SPACES_KEY;
const secretAccessKey = process.env.DO_SPACES_SECRET;

if (!isDryRun) {
  if (!endpoint || !region || !accessKeyId || !secretAccessKey) {
    console.error("Missing required environment variables:");
    console.error("DO_SPACES_ENDPOINT:", endpoint ? "✓" : "✗");
    console.error("DO_SPACES_REGION:", region ? "✓" : "✗");
    console.error("DO_SPACES_KEY:", accessKeyId ? "✓" : "✗");
    console.error("DO_SPACES_SECRET:", secretAccessKey ? "✓" : "✗");
    process.exit(1);
  }
}

// Initialize S3 client (only if not dry-run)
let s3Client: S3Client | null = null;
if (!isDryRun && endpoint && region && accessKeyId && secretAccessKey) {
  s3Client = new S3Client({
    endpoint,
    region,
    credentials: {
      accessKeyId,
      secretAccessKey,
    },
    forcePathStyle: false,
  });
}

// Statistics tracking
interface MPStats {
  member_id: number;
  display_name: string | null;
  imagesFound: number;
  imagesUploaded: number;
  imagesDownloaded: number; // For dry-run mode
  imagesFiltered0Faces: number; // Count of images with no faces
  imagesFilteredMultipleFaces: number; // Count of images with multiple faces
  errors: string[];
}

const stats: MPStats[] = [];
let totalImagesCollected = 0;
let totalImagesUploaded = 0;
let totalImagesDownloaded = 0; // For dry-run mode

// Utility functions
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function retry<T>(
  fn: () => Promise<T>,
  attempts = RETRY_ATTEMPTS,
  operationName = "operation",
): Promise<T | null> {
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error(
        `[${operationName}] Attempt ${i + 1}/${attempts} failed:`,
        errorMsg,
      );
      if (i < attempts - 1) {
        const delay = RETRY_DELAY_BASE * Math.pow(2, i);
        await sleep(delay);
      }
    }
  }
  return null;
}

function _generateImageHash(buffer: Buffer): string {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

// Initialize face detection models (call once at startup)
let faceDetectionModelsLoaded = false;
let faceDetectionAvailable = false;

async function loadFaceDetectionModels() {
  if (faceDetectionModelsLoaded) {
    if (!faceDetectionAvailable) {
      throw new Error(
        "Face detection is required but not available. Cannot proceed without face detection.",
      );
    }
    return;
  }

  // Monkey patch face-api to use node-canvas
  // @ts-expect-error - face-api expects browser types but we're using node-canvas
  faceapi.env.monkeyPatch({ Canvas, Image, ImageData });

  // Get the path to face-api weights
  // The weights are typically in node_modules/@vladmandic/face-api/model
  const modelPath = path.resolve(
    __dirname,
    "../node_modules/@vladmandic/face-api/model",
  );

  // Check if model directory exists
  if (!fs.existsSync(modelPath)) {
    throw new Error(
      `Face detection models not found at ${modelPath}. Please ensure @vladmandic/face-api is properly installed.`,
    );
  }

  // Load tinyFaceDetector model (faster, good for filtering)
  // Alternative: use ssdMobilenetv1 for better accuracy (slower)
  await faceapi.nets.tinyFaceDetector.loadFromDisk(modelPath);

  // Test if TensorFlow.js actually works by trying a simple operation
  // This catches the pnpm module resolution issue early
  // Face detection is REQUIRED - throw error if test fails
  const testCanvas = new Canvas(100, 100);
  // Canvas from 'canvas' package is compatible with faceapi but TypeScript doesn't know this
  await faceapi.detectAllFaces(
    testCanvas as unknown as HTMLCanvasElement,
    new faceapi.TinyFaceDetectorOptions(),
  );

  faceDetectionModelsLoaded = true;
  faceDetectionAvailable = true;
  console.log("Face detection models loaded and tested successfully");
}

// Face detection to check for solo portraits
async function validateSoloPortrait(
  imageUrl: string,
  imageBuffer: Buffer,
): Promise<{ isValid: boolean; faceCount?: number; reason?: string }> {
  try {
    // Check if image is too small
    if (imageBuffer.length < 5000) {
      return { isValid: false, faceCount: 0, reason: "Image too small" };
    }

    // Ensure models are loaded
    if (!faceDetectionModelsLoaded) {
      await loadFaceDetectionModels();
    }

    // Face detection is required - if not available, reject the image
    if (!faceDetectionAvailable) {
      throw new Error(
        "Face detection is required but not available. Cannot validate image.",
      );
    }

    try {
      // Convert buffer to image using canvas
      const img = await loadImage(imageBuffer);
      const canvas = new Canvas(img.width, img.height);
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);

      // Detect faces using tinyFaceDetector (fast, good for filtering)
      // We don't need landmarks, just face count, so we skip .withFaceLandmarks()
      // Wrap in Promise to ensure errors are caught
      // Canvas from 'canvas' package is compatible with faceapi but TypeScript doesn't know this
      const detections = await Promise.resolve(
        faceapi.detectAllFaces(
          canvas as unknown as HTMLCanvasElement,
          new faceapi.TinyFaceDetectorOptions(),
        ),
      ).catch((err) => {
        throw err; // Re-throw to be caught by outer catch
      });

      const faceCount = detections.length;

      // Debug logging
      console.log(
        `  Face detection: found ${faceCount} face(s) in image (${img.width}x${img.height})`,
      );

      // Reject if no faces found
      if (faceCount === 0) {
        return { isValid: false, faceCount: 0, reason: "No faces detected" };
      }

      // Reject if multiple faces found
      if (faceCount > 1) {
        return {
          isValid: false,
          faceCount,
          reason: `Multiple faces detected (${faceCount})`,
        };
      }

      // Check face size (should be at least 0.5% of image area for quality)
      // Lowered from 1% to be more lenient
      const face = detections[0];

      if (!face) {
        return {
          isValid: false,
          faceCount: 1,
          reason: "Face detection returned empty result",
        };
      }

      // face-api returns FaceDetection objects with a .detection property
      // The .detection property contains .box and .score
      // But sometimes the structure might be different, so we check both
      let faceBox: { width: number; height: number } | undefined;
      let confidence: number | undefined;

      // Type for alternative face detection structures
      type AlternativeFaceStructure = {
        box?: { width: number; height: number };
        score?: number;
        width?: number;
        height?: number;
      };

      // Type for face with detection property (face-api structure)
      type FaceWithDetection = {
        detection?: {
          box?: { width: number; height: number };
          score?: number;
        };
      };

      // Try standard structure first: face.detection.box
      const faceWithDetection = face as unknown as FaceWithDetection;
      if (faceWithDetection.detection?.box) {
        faceBox = faceWithDetection.detection.box;
        confidence = faceWithDetection.detection.score;
      }
      // Try alternative: face.box (direct)
      else {
        const altFace = face as unknown as AlternativeFaceStructure;
        if (altFace.box) {
          faceBox = altFace.box;
          confidence = altFace.score;
        }
        // Try another alternative: face is the detection itself
        else if (altFace.width && altFace.height) {
          faceBox = { width: altFace.width, height: altFace.height };
          confidence = altFace.score || 1.0;
        }
      }

      if (
        !faceBox ||
        typeof faceBox.width === "undefined" ||
        typeof faceBox.height === "undefined"
      ) {
        // Debug: log the actual structure
        console.log(
          `  Error: Invalid face box structure. Face object keys:`,
          Object.keys(face),
        );
        console.log(
          `  Face object:`,
          JSON.stringify(face, null, 2).substring(0, 500),
        );
        return {
          isValid: false,
          faceCount: 1,
          reason: "Face detection returned invalid box structure",
        };
      }

      const faceArea = faceBox.width * faceBox.height;
      const imageArea = img.width * img.height;
      const faceRatio = faceArea / imageArea;
      const finalConfidence = confidence ?? 1.0;

      console.log(
        `  Face details: size=${faceBox.width}x${faceBox.height}, ratio=${(
          faceRatio * 100
        ).toFixed(2)}%, confidence=${finalConfidence.toFixed(3)}`,
      );

      // More lenient threshold: 0.5% instead of 1%
      if (faceRatio < 0.005) {
        console.log(
          `  Rejected: Face too small (${(faceRatio * 100).toFixed(2)}% < 0.5%)`,
        );
        return {
          isValid: false,
          faceCount: 1,
          reason: `Face too small in image (${(faceRatio * 100).toFixed(2)}%)`,
        };
      }

      // More lenient threshold: 0.3 instead of 0.5
      if (finalConfidence < 0.3) {
        console.log(
          `  Rejected: Low confidence (${finalConfidence.toFixed(3)} < 0.3)`,
        );
        return {
          isValid: false,
          faceCount: 1,
          reason: `Low face detection confidence (${finalConfidence.toFixed(
            3,
          )})`,
        };
      }

      console.log(`  ✓ Valid: 1 face detected with good quality`);

      // Valid: exactly one face detected with good quality
      return { isValid: true, faceCount: 1 };
    } catch (detectionError) {
      // Face detection is required - if it fails, reject the image
      const errorMsg =
        detectionError instanceof Error
          ? detectionError.message
          : String(detectionError);
      return {
        isValid: false,
        faceCount: undefined,
        reason: `Face detection failed: ${errorMsg}`,
      };
    }
  } catch (error) {
    // Face detection is required - if it fails, reject the image
    const errorMsg = error instanceof Error ? error.message : String(error);
    return {
      isValid: false,
      faceCount: undefined,
      reason: `Face detection error: ${errorMsg}`,
    };
  }
}

// Download image without validation (just download)
async function downloadImage(imageUrl: string): Promise<{
  buffer: Buffer | null;
  success: boolean;
  reason?: string;
}> {
  try {
    const response = await fetch(imageUrl, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      },
    });

    if (!response.ok) {
      return {
        buffer: null,
        success: false,
        reason: `HTTP ${response.status}`,
      };
    }

    const contentType = response.headers.get("content-type") || "";
    if (
      !contentType.startsWith("image/") &&
      !imageUrl.match(/\.(jpg|jpeg|png|webp)$/i)
    ) {
      return {
        buffer: null,
        success: false,
        reason: "Not an image",
      };
    }

    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    return { buffer, success: true };
  } catch (error) {
    return {
      buffer: null,
      success: false,
      reason: `Download error: ${
        error instanceof Error ? error.message : String(error)
      }`,
    };
  }
}

// Validate downloaded image with face detection
async function validateDownloadedImage(
  imageUrl: string,
  buffer: Buffer,
): Promise<{ isValid: boolean; faceCount?: number; reason?: string }> {
  // Validate solo portrait
  return await validateSoloPortrait(imageUrl, buffer);
}

// Save downloaded image to a folder
async function saveDownloadedImage(
  buffer: Buffer,
  folder: string,
  memberId: number,
  index: number,
  imageUrl: string,
): Promise<string | null> {
  try {
    const memberFolder = path.join(folder, memberId.toString());

    // Create directory if it doesn't exist
    if (!fs.existsSync(memberFolder)) {
      fs.mkdirSync(memberFolder, { recursive: true });
    }

    // Determine file extension from URL or default to jpg
    const urlExtension = imageUrl
      .match(/\.(jpg|jpeg|png|webp)$/i)?.[1]
      ?.toLowerCase();
    const fileExtension = urlExtension || "jpg";
    const timestamp = Date.now();
    const fileName = `${timestamp}_${index}.${fileExtension}`;
    const filePath = path.join(memberFolder, fileName);

    // Write file
    fs.writeFileSync(filePath, buffer);

    // Return local file path
    return filePath;
  } catch (error) {
    console.error(`Failed to save image to folder ${folder}:`, error);
    return null;
  }
}

// Save image to local folder (dry-run mode)
async function _saveToLocalFolder(
  buffer: Buffer,
  memberId: number,
  index: number,
  imageUrl: string,
): Promise<string | null> {
  try {
    const memberFolder = path.join(DRY_RUN_FOLDER, memberId.toString());

    // Create directory if it doesn't exist
    if (!fs.existsSync(memberFolder)) {
      fs.mkdirSync(memberFolder, { recursive: true });
    }

    // Determine file extension from URL or default to jpg
    const urlExtension = imageUrl
      .match(/\.(jpg|jpeg|png|webp)$/i)?.[1]
      ?.toLowerCase();
    const fileExtension = urlExtension || "jpg";
    const timestamp = Date.now();
    const fileName = `${timestamp}_${index}.${fileExtension}`;
    const filePath = path.join(memberFolder, fileName);

    // Write file
    fs.writeFileSync(filePath, buffer);

    // Return local file path
    return filePath;
  } catch (error) {
    console.error(`Failed to save image to local folder:`, error);
    return null;
  }
}

// Upload to Digital Ocean Spaces
async function uploadToSpaces(
  buffer: Buffer,
  memberId: number,
  index: number,
): Promise<string | null> {
  if (!s3Client || !region) {
    return null;
  }

  const timestamp = Date.now();
  const fileExtension = "jpg"; // Default to jpg
  const fileName = `${timestamp}_${index}.${fileExtension}`;
  const key = `${FOLDER_PREFIX}/${memberId}/${fileName}`;

  try {
    const command = new PutObjectCommand({
      Bucket: BUCKET_NAME,
      Key: key,
      Body: buffer,
      ContentType: "image/jpeg",
      ACL: "public-read",
    });

    await s3Client.send(command);

    // Generate public URL
    const publicUrl = `https://${BUCKET_NAME}.${region}.cdn.digitaloceanspaces.com/${key}`;
    return publicUrl;
  } catch (error) {
    console.error(`Failed to upload ${key}:`, error);
    return null;
  }
}

// Check if portrait already exists
async function portraitExists(
  memberId: number,
  imageUrl: string,
): Promise<boolean> {
  const { data, error } = await supabaseAdminClient
    .from("parliament_member_portraits")
    .select("id")
    .eq("member_id", memberId)
    .eq("image_url", imageUrl)
    .eq("is_deleted", false)
    .limit(1);

  if (error) {
    console.error(`Error checking existing portrait:`, error);
    return false;
  }

  return (data?.length ?? 0) > 0;
}

// Insert portrait into database (check for conflicts first to avoid constraint violations)
async function insertPortrait(
  memberId: number,
  imageUrl: string,
  cropType: number,
): Promise<boolean> {
  // Check if a portrait with the same (member_id, crop_type, web_version) already exists
  // The unique constraint is on these three columns where is_deleted = false
  const { data: existing, error: checkError } = await supabaseAdminClient
    .from("parliament_member_portraits")
    .select("id")
    .eq("member_id", memberId)
    .eq("crop_type", cropType)
    .eq("web_version", false)
    .eq("is_deleted", false)
    .limit(1)
    .maybeSingle();

  if (checkError) {
    console.error(
      `Error checking existing portrait for member ${memberId}, crop_type ${cropType}:`,
      checkError,
    );
    return false;
  }

  // If a portrait with this crop_type already exists, skip insertion
  if (existing) {
    console.log(
      `Portrait already exists for member ${memberId}, crop_type ${cropType}. Skipping.`,
    );
    return false; // Return false to indicate we didn't insert (but it's not an error)
  }

  // Insert new portrait
  const portrait: PortraitInsert = {
    member_id: memberId,
    image_url: imageUrl,
    crop_type: cropType,
    web_version: false,
    is_primary: false,
    is_deleted: false,
    last_synced_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const { error } = await supabaseAdminClient
    .from("parliament_member_portraits")
    .insert(portrait);

  if (error) {
    console.error(
      `Failed to insert portrait for member ${memberId}, crop_type ${cropType}:`,
      error,
    );
    return false;
  }

  return true;
}

// Helper function to navigate with retry
async function navigateWithRetry(
  page: Page,
  url: string,
  retries = PAGE_NAVIGATION_RETRIES,
  sourceName = "",
): Promise<boolean> {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await page.goto(url, {
        waitUntil: "domcontentloaded", // More lenient than networkidle
        timeout: PAGE_NAVIGATION_TIMEOUT,
      });

      // Check if page loaded successfully
      if (response && response.status() >= 400) {
        if (i < retries - 1) {
          console.log(
            `  [${sourceName}] HTTP ${response.status()}, retrying...`,
          );
          await sleep(DELAY_BETWEEN_REQUESTS);
          continue;
        }
        return false;
      }

      // Wait a bit for dynamic content
      await sleep(2000); // Increased wait time
      return true;
    } catch {
      if (i < retries - 1) {
        console.log(
          `  [${sourceName}] Retrying navigation (attempt ${i + 2}/${
            retries + 1
          })...`,
        );
        await sleep(DELAY_BETWEEN_REQUESTS);
      } else {
        // Silently fail - will be handled by caller
        return false;
      }
    }
  }
  return false;
}

// Image source scrapers

// 1. Wikimedia Commons API (WORKING - verified by test)
async function scrapeWikimediaCommons(
  page: Page,
  mpName: string,
): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    // Try multiple search variations
    const searchVariations = [
      mpName + " UK Parliament",
      mpName + " MP",
      mpName + " Member of Parliament",
      mpName + " politician",
      mpName,
    ];

    for (const searchTerm of searchVariations) {
      const searchQuery = encodeURIComponent(searchTerm);
      const apiUrl = `https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srsearch=${searchQuery}&srnamespace=6&srlimit=50&origin=*`;

      try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
          continue;
        }

        const data = await response.json();

        if (data.query && data.query.search) {
          for (const item of data.query.search) {
            const title = item.title;
            if (title && title.startsWith("File:")) {
              // Get direct image URL from file title
              const fileName = title.replace("File:", "");
              // Use Special:FilePath to get direct image URL
              const imageUrl = `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(
                fileName,
              )}`;
              imageUrls.push(imageUrl);
            }
          }
        }

        await sleep(500); // Rate limiting between requests
      } catch {
        // Continue with next variation
        continue;
      }
    }

    return Array.from(new Set(imageUrls)).slice(0, 50);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 2. Openverse (CC Search) - WORKING (verified by test)
async function scrapeOpenverse(page: Page, mpName: string): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    // Try Openverse API first (more reliable)
    try {
      // Try multiple search variations
      const searchVariations = [
        mpName,
        mpName + " MP",
        mpName + " UK Parliament",
      ];

      for (const searchTerm of searchVariations) {
        const apiUrl = `https://api.openverse.org/v1/images/?q=${encodeURIComponent(
          searchTerm,
        )}&page_size=50&license_type=commercial,modification`;
        const response = await fetch(apiUrl);
        if (response.ok) {
          const data = await response.json();
          if (data.results) {
            for (const result of data.results) {
              // Get the actual image URL, not thumbnail
              if (result.url) {
                imageUrls.push(result.url);
              } else if (result.foreign_landing_url) {
                // Try to extract from landing URL
                imageUrls.push(result.foreign_landing_url);
              }
            }
          }
        }
        await sleep(500); // Rate limiting
      }
    } catch {
      // API failed, try scraping
    }

    // Also try web scraping as fallback
    const searchUrl = `https://openverse.org/search/?q=${encodeURIComponent(
      mpName,
    )}&type=image`;
    const navigated = await navigateWithRetry(
      page,
      searchUrl,
      PAGE_NAVIGATION_RETRIES,
      "Openverse",
    );
    if (navigated) {
      await sleep(3000); // Wait longer for dynamic content

      // Try multiple strategies
      try {
        // Strategy 1: Look for all img tags and extract URLs
        const allImages = await page.$$eval("img", (imgs) => {
          return imgs
            .map((img) => {
              let src =
                img.getAttribute("src") ||
                img.getAttribute("data-src") ||
                img.getAttribute("data-lazy-src") ||
                img.getAttribute("data-original");
              if (src && !src.includes("logo") && !src.includes("icon")) {
                if (src.startsWith("//")) {
                  src = "https:" + src;
                } else if (src.startsWith("/")) {
                  src = "https://openverse.org" + src;
                }
                return src;
              }
              return null;
            })
            .filter(
              (url): url is string => url !== null && url.startsWith("http"),
            );
        });
        imageUrls.push(...allImages);
      } catch {
        // Continue
      }

      // Strategy 2: Look for background images
      try {
        const bgImages = await page.$$eval(
          "[style*='background-image']",
          (elements) => {
            return elements
              .map((el) => {
                const style = el.getAttribute("style") || "";
                const match = style.match(/url\(['"]?([^'")]+)['"]?\)/);
                if (match && match[1]) {
                  return match[1];
                }
                return null;
              })
              .filter(
                (url): url is string => url !== null && url.startsWith("http"),
              );
          },
        );
        imageUrls.push(...bgImages);
      } catch {
        // Continue
      }
    }

    return Array.from(new Set(imageUrls)).slice(0, 50);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 3. UK Parliament Official Portraits (web scraping, NOT API)
async function _scrapeParliamentPortraits(
  page: Page,
  memberId: number,
): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    const portraitUrl = `https://members.parliament.uk/member/${memberId}/portrait`;
    const navigated = await navigateWithRetry(
      page,
      portraitUrl,
      PAGE_NAVIGATION_RETRIES,
      "Parliament",
    );
    if (!navigated) {
      return imageUrls;
    }
    await sleep(DELAY_BETWEEN_REQUESTS);

    // Try multiple strategies to find portrait images
    const strategies = [
      // Strategy 1: Look for img tags with portrait-related attributes
      async () => {
        return await page.$$eval("img", (imgs) => {
          return imgs
            .map((img) => {
              const src =
                img.getAttribute("src") ||
                img.getAttribute("data-src") ||
                img.getAttribute("data-lazy-src");
              if (
                src &&
                (src.includes("portrait") ||
                  src.includes("member") ||
                  src.includes("photo"))
              ) {
                return src.startsWith("http")
                  ? src
                  : `https://members.parliament.uk${src}`;
              }
              return null;
            })
            .filter(
              (url): url is string =>
                url !== null &&
                (url.includes(".jpg") ||
                  url.includes(".png") ||
                  url.includes(".jpeg")),
            );
        });
      },
      // Strategy 2: Look for background images in style attributes
      async () => {
        return await page.$$eval(
          "[style*='background-image'], [style*='background:']",
          (elements) => {
            return elements
              .map((el) => {
                const style = el.getAttribute("style") || "";
                const match = style.match(/url\(['"]?([^'")]+)['"]?\)/);
                if (match && match[1]) {
                  const src = match[1];
                  if (
                    src.includes("portrait") ||
                    src.includes("member") ||
                    src.includes("photo")
                  ) {
                    return src.startsWith("http")
                      ? src
                      : `https://members.parliament.uk${src}`;
                  }
                }
                return null;
              })
              .filter(
                (url): url is string =>
                  url !== null &&
                  (url.includes(".jpg") ||
                    url.includes(".png") ||
                    url.includes(".jpeg")),
              );
          },
        );
      },
      // Strategy 3: Look for picture/source elements
      async () => {
        return await page.$$eval("picture source, picture img", (elements) => {
          return elements
            .map((el) => {
              const src =
                el.getAttribute("src") ||
                el.getAttribute("srcset")?.split(" ")[0];
              if (src && (src.includes("portrait") || src.includes("member"))) {
                return src.startsWith("http")
                  ? src
                  : `https://members.parliament.uk${src}`;
              }
              return null;
            })
            .filter(
              (url): url is string =>
                url !== null &&
                (url.includes(".jpg") ||
                  url.includes(".png") ||
                  url.includes(".jpeg")),
            );
        });
      },
    ];

    for (const strategy of strategies) {
      try {
        const images = await strategy();
        if (images.length > 0) {
          imageUrls.push(...images);
          break;
        }
      } catch {
        continue;
      }
    }

    return Array.from(new Set(imageUrls));
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 4. TheyWorkForYou
async function _scrapeTheyWorkForYou(
  page: Page,
  memberId: number,
): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    const profileUrl = `https://www.theyworkforyou.com/mp/${memberId}`;
    const navigated = await navigateWithRetry(
      page,
      profileUrl,
      PAGE_NAVIGATION_RETRIES,
      "TheyWorkForYou",
    );
    if (!navigated) {
      return imageUrls;
    }
    await sleep(DELAY_BETWEEN_REQUESTS);

    // Try multiple selectors
    const selectors = [
      "img[src*='theyworkforyou']",
      ".mp-photo img",
      ".portrait img",
      ".profile-image img",
      "img",
    ];

    for (const selector of selectors) {
      try {
        const images = await page.$$eval(selector, (imgs) => {
          return imgs
            .map((img) => {
              const src =
                img.getAttribute("src") || img.getAttribute("data-src");
              if (
                src &&
                (src.includes("theyworkforyou") ||
                  src.includes("portrait") ||
                  src.includes("photo"))
              ) {
                return src.startsWith("http")
                  ? src
                  : `https://www.theyworkforyou.com${src}`;
              }
              return null;
            })
            .filter(
              (url): url is string =>
                url !== null &&
                (url.includes(".jpg") ||
                  url.includes(".png") ||
                  url.includes(".jpeg")),
            );
        });

        if (images.length > 0) {
          imageUrls.push(...images);
          break;
        }
      } catch {
        continue;
      }
    }

    return Array.from(new Set(imageUrls));
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 5. House of Commons Flickr
async function scrapeCommonsFlickr(
  page: Page,
  mpName: string,
): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    const searchUrl = `https://www.flickr.com/search/?text=${encodeURIComponent(
      mpName,
    )}&sort=relevance`;
    const navigated = await navigateWithRetry(
      page,
      searchUrl,
      PAGE_NAVIGATION_RETRIES,
      "Flickr",
    );
    if (!navigated) {
      return imageUrls;
    }
    await sleep(DELAY_BETWEEN_REQUESTS);

    // Try multiple selectors for Flickr
    const selectors = [
      ".photo-list-photo-view img",
      ".photo-list-photo img",
      ".overlay img",
      ".photo-list img",
      "img[src*='staticflickr.com']",
      "img[src*='live.staticflickr.com']",
    ];

    for (const selector of selectors) {
      try {
        const images = await page.$$eval(selector, (imgs) => {
          return imgs
            .map((img) => {
              let src =
                img.getAttribute("src") ||
                img.getAttribute("data-src") ||
                img.getAttribute("data-lazy-src");
              if (src) {
                // Convert Flickr thumbnail sizes to larger
                // _s = 75px, _q = 150px, _t = 100px, _m = 240px, _n = 320px, _z = 640px, _c = 800px, _b = 1024px
                src = src.replace(/_[stqmnz]\.(jpg|png|jpeg)$/i, "_b.$1");
                // Ensure full URL
                if (src.startsWith("//")) {
                  src = "https:" + src;
                }
                return src;
              }
              return null;
            })
            .filter(
              (url): url is string =>
                url !== null &&
                url.startsWith("http") &&
                url.includes("flickr"),
            );
        });

        if (images.length > 0) {
          imageUrls.push(...images);
          break;
        }
      } catch {
        continue;
      }
    }

    return Array.from(new Set(imageUrls)).slice(0, 20);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 6. House of Lords Flickr
async function _scrapeLordsFlickr(
  page: Page,
  mpName: string,
): Promise<string[]> {
  // Reuse Commons Flickr logic with different search term
  return scrapeCommonsFlickr(page, mpName + " House of Lords");
}

// 7. National Portrait Gallery
async function _scrapeNationalPortraitGallery(
  page: Page,
  mpName: string,
): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    const searchUrl = `https://www.npg.org.uk/collections/search/person.php?searchTerm=${encodeURIComponent(
      mpName,
    )}`;
    const navigated = await navigateWithRetry(
      page,
      searchUrl,
      PAGE_NAVIGATION_RETRIES,
      "NPG",
    );
    if (!navigated) {
      return imageUrls;
    }
    await sleep(DELAY_BETWEEN_REQUESTS);

    // Try multiple selectors
    const selectors = [
      "img[src*='npg.org.uk']",
      ".portrait img",
      ".image img",
      ".thumbnail img",
      "img",
    ];

    for (const selector of selectors) {
      try {
        const images = await page.$$eval(selector, (imgs) => {
          return imgs
            .map((img) => {
              const src =
                img.getAttribute("src") ||
                img.getAttribute("data-src") ||
                img.getAttribute("data-lazy-src");
              if (src && src.includes("npg.org.uk")) {
                let fullUrl = src.startsWith("http")
                  ? src
                  : `https://www.npg.org.uk${src}`;
                // Remove query parameters that might limit image size
                fullUrl = fullUrl.split("?")[0];
                return fullUrl;
              }
              return null;
            })
            .filter(
              (url): url is string =>
                url !== null &&
                (url.includes(".jpg") ||
                  url.includes(".png") ||
                  url.includes(".jpeg")),
            );
        });

        if (images.length > 0) {
          imageUrls.push(...images);
          break;
        }
      } catch {
        continue;
      }
    }

    return Array.from(new Set(imageUrls)).slice(0, 20);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 8. Parliamentary Heritage Collections
async function _scrapeHeritageCollections(
  page: Page,
  mpName: string,
): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    const searchUrl = `https://heritagecollections.parliament.uk/?s=${encodeURIComponent(
      mpName,
    )}`;
    const navigated = await navigateWithRetry(
      page,
      searchUrl,
      PAGE_NAVIGATION_RETRIES,
      "Heritage",
    );
    if (!navigated) {
      return imageUrls;
    }
    await sleep(DELAY_BETWEEN_REQUESTS);

    // Try multiple selectors
    const selectors = [
      "img[src*='heritagecollections']",
      ".wp-post-image",
      ".attachment-thumbnail",
      ".gallery-item img",
      "img",
    ];

    for (const selector of selectors) {
      try {
        const images = await page.$$eval(selector, (imgs) => {
          return imgs
            .map((img) => {
              const src =
                img.getAttribute("src") ||
                img.getAttribute("data-src") ||
                img.getAttribute("data-lazy-src");
              if (src && src.includes("heritagecollections")) {
                return src.startsWith("http")
                  ? src
                  : `https://heritagecollections.parliament.uk${src}`;
              }
              return null;
            })
            .filter(
              (url): url is string =>
                url !== null &&
                (url.includes(".jpg") ||
                  url.includes(".png") ||
                  url.includes(".jpeg")),
            );
        });

        if (images.length > 0) {
          imageUrls.push(...images);
          break;
        }
      } catch {
        continue;
      }
    }

    return Array.from(new Set(imageUrls)).slice(0, 20);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 10. Getty Images (WORKING - verified by test)
async function _scrapeGettyImages(
  page: Page,
  mpName: string,
): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    const searchUrl = `https://www.gettyimages.com/photos/${encodeURIComponent(
      mpName,
    ).replace(/%20/g, "-")}`;
    const navigated = await navigateWithRetry(
      page,
      searchUrl,
      PAGE_NAVIGATION_RETRIES,
      "Getty",
    );
    if (!navigated) {
      return imageUrls;
    }
    await sleep(3000); // Wait longer for dynamic content

    // Try to extract all images, not just specific selectors
    try {
      const allImages = await page.$$eval("img", (imgs) => {
        return imgs
          .map((img) => {
            let src =
              img.getAttribute("src") ||
              img.getAttribute("data-src") ||
              img.getAttribute("data-lazy-src") ||
              img.getAttribute("data-original");
            if (
              src &&
              src.includes("gettyimages") &&
              !src.includes("logo") &&
              !src.includes("icon")
            ) {
              // Try to get full size image
              if (src.includes("_thumb") || src.includes("_small")) {
                src = src.replace("_thumb", "").replace("_small", "");
              }
              if (src.startsWith("//")) {
                src = "https:" + src;
              } else if (src.startsWith("/")) {
                src = `https://www.gettyimages.com${src}`;
              }
              return src;
            }
            return null;
          })
          .filter(
            (url): url is string => url !== null && url.startsWith("http"),
          );
      });
      imageUrls.push(...allImages);
    } catch {
      // Continue with other strategies
    }

    // Also try looking for data attributes
    try {
      const dataImages = await page.$$eval(
        "[data-src*='gettyimages'], [data-image*='gettyimages']",
        (elements) => {
          return elements
            .map((el) => {
              const src =
                el.getAttribute("data-src") ||
                el.getAttribute("data-image") ||
                el.getAttribute("data-url");
              if (src && src.includes("gettyimages")) {
                return src.startsWith("http")
                  ? src
                  : `https://www.gettyimages.com${src}`;
              }
              return null;
            })
            .filter(
              (url): url is string => url !== null && url.startsWith("http"),
            );
        },
      );
      imageUrls.push(...dataImages);
    } catch {
      // Continue
    }

    return Array.from(new Set(imageUrls)).slice(0, 50);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 11. Alamy (WORKING - verified by test)
async function _scrapeAlamy(page: Page, mpName: string): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    // Try multiple search variations
    const searchVariations = [
      mpName,
      mpName + " MP",
      mpName + " UK Parliament",
      mpName + " politician",
    ];

    for (const searchTerm of searchVariations) {
      try {
        const searchUrl = `https://www.alamy.com/stock-photo/${encodeURIComponent(
          searchTerm,
        ).replace(/%20/g, "-")}.html`;
        const navigated = await navigateWithRetry(
          page,
          searchUrl,
          PAGE_NAVIGATION_RETRIES,
          "Alamy",
        );
        if (!navigated) {
          continue;
        }
        await sleep(3000); // Wait longer for dynamic content

        // Extract all images from Alamy
        try {
          const allImages = await page.$$eval("img", (imgs) => {
            return imgs
              .map((img) => {
                let src =
                  img.getAttribute("src") ||
                  img.getAttribute("data-src") ||
                  img.getAttribute("data-lazy-src") ||
                  img.getAttribute("data-original");
                if (
                  src &&
                  src.includes("alamy") &&
                  !src.includes("logo") &&
                  !src.includes("icon")
                ) {
                  // Try to get full size image - Alamy uses different size suffixes
                  if (
                    src.includes("_thumb") ||
                    src.includes("_small") ||
                    src.includes("_medium")
                  ) {
                    // Remove size suffixes to get larger version
                    src = src.replace(/_thumb|_small|_medium/g, "");
                  }
                  if (src.startsWith("//")) {
                    src = "https:" + src;
                  } else if (src.startsWith("/")) {
                    src = `https://www.alamy.com${src}`;
                  }
                  return src;
                }
                return null;
              })
              .filter(
                (url): url is string => url !== null && url.startsWith("http"),
              );
          });
          imageUrls.push(...allImages);

          // If we found images, break early
          if (allImages.length > 0) {
            break;
          }
        } catch {
          // Continue
        }
      } catch {
        continue;
      }
    }

    return Array.from(new Set(imageUrls)).slice(0, 50);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 12. Pixabay (WORKING - verified by test, found 98 images)
async function _scrapePixabay(page: Page, mpName: string): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    // Try multiple search variations
    const searchVariations = [
      mpName,
      mpName + " MP",
      mpName + " UK Parliament",
      mpName + " politician",
    ];

    for (const searchTerm of searchVariations) {
      try {
        const searchUrl = `https://pixabay.com/images/search/${encodeURIComponent(
          searchTerm,
        ).replace(/%20/g, "%20")}/`;
        const navigated = await navigateWithRetry(
          page,
          searchUrl,
          PAGE_NAVIGATION_RETRIES,
          "Pixabay",
        );
        if (!navigated) {
          continue;
        }
        await sleep(3000); // Wait longer for dynamic content

        // Extract all images from Pixabay
        try {
          const allImages = await page.$$eval("img", (imgs) => {
            return imgs
              .map((img) => {
                let src =
                  img.getAttribute("src") ||
                  img.getAttribute("data-src") ||
                  img.getAttribute("data-lazy-src") ||
                  img.getAttribute("data-original");
                if (
                  src &&
                  src.includes("pixabay") &&
                  !src.includes("logo") &&
                  !src.includes("icon")
                ) {
                  // Try to get full size image - remove size suffixes
                  if (
                    src.includes("_150") ||
                    src.includes("_340") ||
                    src.includes("_640") ||
                    src.includes("_960")
                  ) {
                    // Remove size suffix: image_150.jpg -> image.jpg
                    src = src.replace(/_\d+\.(jpg|png|jpeg)$/i, ".$1");
                  }
                  if (src.startsWith("//")) {
                    src = "https:" + src;
                  } else if (src.startsWith("/")) {
                    src = `https://pixabay.com${src}`;
                  }
                  return src;
                }
                return null;
              })
              .filter(
                (url): url is string => url !== null && url.startsWith("http"),
              );
          });
          imageUrls.push(...allImages);

          // If we found images, break early
          if (allImages.length > 0) {
            break;
          }
        } catch {
          // Continue
        }

        // Also try looking for link hrefs that might contain image URLs
        try {
          const linkImages = await page.$$eval(
            "a[href*='pixabay']",
            (links) => {
              return links
                .map((link) => {
                  const href = link.getAttribute("href");
                  if (
                    href &&
                    href.includes("pixabay") &&
                    (href.includes(".jpg") || href.includes(".png"))
                  ) {
                    return href.startsWith("http")
                      ? href
                      : `https://pixabay.com${href}`;
                  }
                  return null;
                })
                .filter((url): url is string => url !== null);
            },
          );
          imageUrls.push(...linkImages);
        } catch {
          // Continue
        }
      } catch {
        continue;
      }
    }

    return Array.from(new Set(imageUrls)).slice(0, 50);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 13. Pexels (WORKING - verified by test)
async function _scrapePexels(page: Page, mpName: string): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    // Try multiple search variations
    const searchVariations = [
      mpName,
      mpName + " MP",
      mpName + " UK Parliament",
      mpName + " politician",
    ];

    for (const searchTerm of searchVariations) {
      try {
        const searchUrl = `https://www.pexels.com/search/${encodeURIComponent(
          searchTerm,
        ).replace(/%20/g, "%20")}/`;
        const navigated = await navigateWithRetry(
          page,
          searchUrl,
          PAGE_NAVIGATION_RETRIES,
          "Pexels",
        );
        if (!navigated) {
          continue;
        }
        await sleep(3000); // Wait longer for dynamic content

        // Extract all images from Pexels
        try {
          const allImages = await page.$$eval("img", (imgs) => {
            return imgs
              .map((img) => {
                let src =
                  img.getAttribute("src") ||
                  img.getAttribute("data-src") ||
                  img.getAttribute("data-lazy-src") ||
                  img.getAttribute("data-original");
                if (
                  src &&
                  (src.includes("pexels") || src.includes("images.pexels")) &&
                  !src.includes("logo") &&
                  !src.includes("icon")
                ) {
                  // Try to get full size image - remove query parameters
                  if (src.includes("?auto=compress") || src.includes("?cs=")) {
                    src = src.split("?")[0];
                  }
                  if (src.startsWith("//")) {
                    src = "https:" + src;
                  } else if (src.startsWith("/")) {
                    src = `https://www.pexels.com${src}`;
                  }
                  return src;
                }
                return null;
              })
              .filter(
                (url): url is string => url !== null && url.startsWith("http"),
              );
          });
          imageUrls.push(...allImages);

          // If we found images, break early
          if (allImages.length > 0) {
            break;
          }
        } catch {
          // Continue
        }
      } catch {
        continue;
      }
    }

    return Array.from(new Set(imageUrls)).slice(0, 50);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// 14. Chris McAndrew's Parliamentary Portraits (via Parliament website) - REMOVED (not working)
async function _scrapeMcAndrewPortraits(
  page: Page,
  mpName: string,
): Promise<string[]> {
  const imageUrls: string[] = [];
  try {
    // Search Parliament media galleries
    const searchUrl = `https://www.parliament.uk/search/?q=${encodeURIComponent(
      mpName + " portrait",
    )}`;
    const navigated = await navigateWithRetry(
      page,
      searchUrl,
      PAGE_NAVIGATION_RETRIES,
      "McAndrew",
    );
    if (!navigated) {
      return imageUrls;
    }
    await sleep(DELAY_BETWEEN_REQUESTS);

    // Try multiple selectors
    const selectors = [
      "img[src*='parliament.uk']",
      ".search-result img",
      ".media-item img",
      ".gallery img",
      "img",
    ];

    for (const selector of selectors) {
      try {
        const images = await page.$$eval(selector, (imgs) => {
          return imgs
            .map((img) => {
              const src =
                img.getAttribute("src") ||
                img.getAttribute("data-src") ||
                img.getAttribute("data-lazy-src");
              if (
                src &&
                (src.includes("parliament.uk") ||
                  src.includes("portrait") ||
                  src.includes("photo"))
              ) {
                return src.startsWith("http")
                  ? src
                  : `https://www.parliament.uk${src}`;
              }
              return null;
            })
            .filter(
              (url): url is string =>
                url !== null &&
                (url.includes(".jpg") ||
                  url.includes(".png") ||
                  url.includes(".jpeg")),
            );
        });

        if (images.length > 0) {
          imageUrls.push(...images);
          break;
        }
      } catch {
        continue;
      }
    }

    return Array.from(new Set(imageUrls)).slice(0, 20);
  } catch {
    // Silently fail
  }
  return imageUrls;
}

// Collect images for a single MP
async function collectImagesForMP(
  browser: Browser,
  mp: ParliamentMember,
): Promise<void> {
  const mpStats: MPStats = {
    member_id: mp.member_id,
    display_name: mp.display_name,
    imagesFound: 0,
    imagesUploaded: 0,
    imagesDownloaded: 0,
    imagesFiltered0Faces: 0,
    imagesFilteredMultipleFaces: 0,
    errors: [],
  };

  console.log(
    `\n[${mp.member_id}] Processing ${mp.display_name || "Unknown MP"}...`,
  );

  // Create context with user agent and viewport settings
  const context = await browser.newContext({
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    viewport: { width: 1920, height: 1080 },
  });

  const page = await context.newPage();

  const allImageUrls = new Set<string>();
  const uploadedUrls = new Set<string>();

  try {
    // Build search queries
    const searchQueries = [
      mp.display_name,
      mp.given_name && mp.family_name
        ? `${mp.given_name} ${mp.family_name}`
        : null,
      mp.constituency_name ? `${mp.constituency_name} MP` : null,
    ].filter((q): q is string => q !== null);

    const primaryQuery = searchQueries[0] || "Unknown";

    // Search all sources
    const sourcePromises: Promise<string[]>[] = [];

    // Source 1: Wikimedia Commons API (WORKING - verified by test)
    sourcePromises.push(scrapeWikimediaCommons(page, primaryQuery));

    // Source 2: Openverse (CC Search) (WORKING - verified by test)
    sourcePromises.push(scrapeOpenverse(page, primaryQuery));

    const sourceResults = await Promise.all(sourcePromises);

    // Log results from each source
    const sourceNames = ["Wikimedia Commons", "Openverse"];

    console.log(`[${mp.member_id}] Source results:`);
    sourceResults.forEach((urls, index) => {
      const name = sourceNames[index] || `Source ${index + 1}`;
      console.log(`  ${name}: ${urls.length} images`);
      if (urls.length > 0 && urls.length <= 5) {
        console.log(`    Sample URLs: ${urls.slice(0, 3).join(", ")}`);
      }
      urls.forEach((url) => allImageUrls.add(url));
    });

    mpStats.imagesFound = allImageUrls.size;
    console.log(
      `[${mp.member_id}] Found ${
        allImageUrls.size
      } unique potential images from ${
        sourceResults.filter((r) => r.length > 0).length
      } sources`,
    );

    // Step 1: Check for existing images or download new ones
    const memberDownloadFolder = path.join(
      DOWNLOAD_FOLDER,
      mp.member_id.toString(),
    );
    const existingImages = fs.existsSync(memberDownloadFolder)
      ? fs
          .readdirSync(memberDownloadFolder)
          .filter((file) => /\.(jpg|jpeg|png|webp)$/i.test(file))
          .sort()
      : [];

    const downloadedImages: Array<{
      url: string;
      buffer: Buffer;
      index: number;
    }> = [];

    if (existingImages.length > 0) {
      // Load existing images from download folder
      console.log(
        `[${mp.member_id}] Step 1: Found ${existingImages.length} existing images in download folder. Loading them...`,
      );
      for (let i = 0; i < existingImages.length; i++) {
        const imageFile = existingImages[i];
        const imagePath = path.join(memberDownloadFolder, imageFile);
        try {
          const buffer = fs.readFileSync(imagePath);
          downloadedImages.push({
            url: `file://${imagePath}`, // Use file:// URL for tracking
            buffer: buffer,
            index: i,
          });
          console.log(
            `[${mp.member_id}] Loaded ${i + 1}/${
              existingImages.length
            }: ${imageFile}`,
          );
        } catch (error) {
          console.error(
            `[${mp.member_id}] Failed to load ${imageFile}:`,
            error instanceof Error ? error.message : String(error),
          );
          mpStats.errors.push(`Failed to load ${imageFile}`);
        }
      }
    } else {
      // Download images if none exist
      console.log(
        `[${mp.member_id}] Step 1: Downloading ${allImageUrls.size} images...`,
      );
      let downloadIndex = 0;

      for (const imageUrl of allImageUrls) {
        // Check if already exists (only in non-dry-run mode)
        if (!isDryRun) {
          const exists = await portraitExists(mp.member_id, imageUrl);
          if (exists) {
            continue;
          }
        }

        // Download image
        const downloadResult = await retry(
          () => downloadImage(imageUrl),
          RETRY_ATTEMPTS,
          `download-${mp.member_id}`,
        );

        if (
          !downloadResult ||
          !downloadResult.success ||
          !downloadResult.buffer
        ) {
          if (downloadResult?.reason) {
            mpStats.errors.push(
              `Download failed ${imageUrl}: ${downloadResult.reason}`,
            );
          }
          continue;
        }

        // Save to download folder
        const downloadPath = await saveDownloadedImage(
          downloadResult.buffer,
          DOWNLOAD_FOLDER,
          mp.member_id,
          downloadIndex,
          imageUrl,
        );

        if (downloadPath) {
          downloadedImages.push({
            url: imageUrl,
            buffer: downloadResult.buffer,
            index: downloadIndex,
          });
          downloadIndex++;
          console.log(
            `[${mp.member_id}] Downloaded ${downloadIndex}/${
              allImageUrls.size
            }: ${path.basename(downloadPath)}`,
          );
        }
      }
    }

    console.log(
      `[${mp.member_id}] Step 2: Validating ${downloadedImages.length} downloaded images with face detection...`,
    );

    // Step 2: Filter downloaded images with face detection
    const validImages: Array<{ url: string; buffer: Buffer; index: number }> =
      [];
    const invalidImages: Array<{
      url: string;
      buffer: Buffer;
      index: number;
      reason: string;
      faceCount?: number;
    }> = [];

    for (const downloaded of downloadedImages) {
      console.log(
        `[${mp.member_id}] Validating image ${downloaded.index + 1}/${
          downloadedImages.length
        }...`,
      );
      const validation = await validateDownloadedImage(
        downloaded.url,
        downloaded.buffer,
      );

      // Debug logging
      console.log(
        `[${mp.member_id}] Validation result: isValid=${
          validation.isValid
        }, faceCount=${validation.faceCount ?? "undefined"}, reason=${
          validation.reason || "none"
        }`,
      );

      if (validation.isValid && validation.faceCount === 1) {
        // Valid: exactly one face
        validImages.push(downloaded);
        await saveDownloadedImage(
          downloaded.buffer,
          VALID_FOLDER,
          mp.member_id,
          downloaded.index,
          downloaded.url,
        );
      } else {
        // Invalid: 0 faces or multiple faces
        invalidImages.push({
          ...downloaded,
          reason: validation.reason || "Unknown",
          faceCount: validation.faceCount,
        });
        await saveDownloadedImage(
          downloaded.buffer,
          INVALID_FOLDER,
          mp.member_id,
          downloaded.index,
          downloaded.url,
        );

        // Track filtered images
        if (validation.faceCount === 0) {
          mpStats.imagesFiltered0Faces++;
          console.log(
            `[${mp.member_id}] Invalid (0 faces): ${downloaded.url.substring(
              0,
              80,
            )}...`,
          );
        } else if (validation.faceCount && validation.faceCount > 1) {
          mpStats.imagesFilteredMultipleFaces++;
          console.log(
            `[${mp.member_id}] Invalid (${
              validation.faceCount
            } faces): ${downloaded.url.substring(0, 80)}...`,
          );
        } else {
          mpStats.errors.push(`Image ${downloaded.url}: ${validation.reason}`);
        }
      }
    }

    console.log(
      `[${mp.member_id}] Filtered: ${validImages.length} valid (1 face), ${invalidImages.length} invalid (0 or multiple faces)`,
    );

    // Step 3: Process valid images (upload or save)
    let processedCount = 0;
    let cropType = 10; // Start from 10 to distinguish from API portraits

    for (const validImage of validImages) {
      if (processedCount >= MAX_IMAGES_PER_MP) {
        break;
      }

      if (isDryRun) {
        // In dry-run, images are already saved to VALID_FOLDER
        processedCount++;
        mpStats.imagesDownloaded++;
        totalImagesDownloaded++;
        console.log(
          `[${mp.member_id}] Valid image ${processedCount}/${Math.min(
            validImages.length,
            MAX_IMAGES_PER_MP,
          )}: ${path.basename(
            path.join(
              VALID_FOLDER,
              mp.member_id.toString(),
              `${Date.now()}_${validImage.index}.jpg`,
            ),
          )}`,
        );
      } else {
        // Upload to Spaces in normal mode
        const publicUrl = await retry(
          () => uploadToSpaces(validImage.buffer, mp.member_id, processedCount),
          RETRY_ATTEMPTS,
          `upload-${mp.member_id}`,
        );

        if (!publicUrl) {
          mpStats.errors.push(`Failed to upload ${validImage.url}`);
          continue;
        }

        // Insert into database
        const inserted = await insertPortrait(
          mp.member_id,
          publicUrl,
          cropType,
        );
        if (inserted) {
          uploadedUrls.add(publicUrl);
          processedCount++;
          cropType++;
          mpStats.imagesUploaded++;
          totalImagesUploaded++;
          console.log(
            `[${
              mp.member_id
            }] Uploaded valid image ${processedCount}/${Math.min(
              validImages.length,
              MAX_IMAGES_PER_MP,
            )}: ${publicUrl}`,
          );
        } else {
          mpStats.errors.push(`Failed to insert ${publicUrl} into database`);
        }
      }
    }

    if (isDryRun) {
      mpStats.imagesDownloaded = processedCount;
      totalImagesCollected += processedCount;
    } else {
      mpStats.imagesUploaded = processedCount;
      totalImagesCollected += processedCount;
    }
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    mpStats.errors.push(`Fatal error: ${errorMsg}`);
    console.error(`[${mp.member_id}] Error:`, error);
  } finally {
    await page.close();
    await context.close();
  }

  stats.push(mpStats);
  if (isDryRun) {
    console.log(
      `[${mp.member_id}] Completed: ${mpStats.imagesDownloaded} images downloaded, ${mpStats.errors.length} errors`,
    );
  } else {
    console.log(
      `[${mp.member_id}] Completed: ${mpStats.imagesUploaded} images uploaded, ${mpStats.errors.length} errors`,
    );
  }
}

// Main function
async function main() {
  // Handle unhandled promise rejections from TensorFlow.js
  // Face detection is required, so we exit if it fails
  const originalUnhandledRejection = process.listeners("unhandledRejection");
  process.removeAllListeners("unhandledRejection");
  process.on("unhandledRejection", (reason, promise) => {
    if (
      reason &&
      typeof reason === "object" &&
      "message" in reason &&
      typeof reason.message === "string" &&
      (reason.message.includes("isNullOrUndefined") ||
        reason.message.includes("tensorflow"))
    ) {
      console.error(
        "FATAL: TensorFlow.js error detected. Face detection is required but failed.",
      );
      console.error(
        "Error details:",
        reason instanceof Error ? reason.message : String(reason),
      );
      console.error("\nPossible solutions:");
      console.error("  1. Switch to Node.js 20 (currently using Node.js 24)");
      console.error("  2. Use npm instead of pnpm for this project");
      console.error(
        "  3. Check TensorFlow.js installation and rebuild native modules",
      );
      process.exit(1);
    }
    // Re-throw other unhandled rejections
    if (originalUnhandledRejection.length > 0) {
      originalUnhandledRejection.forEach((listener) => {
        listener(reason, promise);
      });
    } else {
      console.error("Unhandled promise rejection:", reason);
    }
  });

  const args = process.argv.slice(2);

  // Parse arguments - handle both --arg=value and --arg value formats
  const limitArg = args.find((arg) => arg.startsWith("--limit="));
  const limitArgIndex = args.findIndex((arg) => arg === "--limit");
  const memberIdArg = args.find((arg) => arg.startsWith("--member-id="));
  const memberIdArgIndex = args.findIndex((arg) => arg === "--member-id");
  const skipExisting = args.includes("--skip-existing");
  const dryRun = args.includes("--dry-run");

  const limit = limitArg
    ? parseInt(limitArg.split("=")[1], 10)
    : limitArgIndex !== -1 && args[limitArgIndex + 1]
      ? parseInt(args[limitArgIndex + 1], 10)
      : undefined;

  const memberId = memberIdArg
    ? parseInt(memberIdArg.split("=")[1], 10)
    : memberIdArgIndex !== -1 && args[memberIdArgIndex + 1]
      ? parseInt(args[memberIdArgIndex + 1], 10)
      : undefined;

  console.log("Starting MP image collection script...");
  console.log("Configuration:");
  console.log(
    `  Mode: ${
      dryRun ? "DRY RUN (local folder)" : "PRODUCTION (Digital Ocean Spaces)"
    }`,
  );
  console.log(`  Max images per MP: ${MAX_IMAGES_PER_MP}`);
  console.log(`  Limit: ${limit || "none"}`);
  console.log(`  Member ID filter: ${memberId || "none"}`);
  console.log(`  Skip existing: ${skipExisting}`);
  // Create folders for downloaded, valid, and invalid images
  if (!fs.existsSync(DOWNLOAD_FOLDER)) {
    fs.mkdirSync(DOWNLOAD_FOLDER, { recursive: true });
    console.log(`  Created download folder: ${DOWNLOAD_FOLDER}`);
  }
  if (!fs.existsSync(VALID_FOLDER)) {
    fs.mkdirSync(VALID_FOLDER, { recursive: true });
    console.log(`  Created valid images folder: ${VALID_FOLDER}`);
  }
  if (!fs.existsSync(INVALID_FOLDER)) {
    fs.mkdirSync(INVALID_FOLDER, { recursive: true });
    console.log(`  Created invalid images folder: ${INVALID_FOLDER}`);
  }

  if (dryRun) {
    console.log(`  Dry-run mode: Images will be organized in folders`);
    console.log(`    - Downloaded: ${DOWNLOAD_FOLDER}`);
    console.log(`    - Valid (1 face): ${VALID_FOLDER}`);
    console.log(`    - Invalid (0 or multiple faces): ${INVALID_FOLDER}`);
  }

  // Fetch MPs from database with pagination
  const PAGE_SIZE = 1000; // Supabase default limit
  const allMps: ParliamentMember[] = [];
  let page = 0;
  let hasMore = true;

  console.log("Fetching MPs from database...");

  while (hasMore) {
    const startRange = page * PAGE_SIZE;
    const endRange = startRange + PAGE_SIZE - 1;

    let query = supabaseAdminClient
      .from("parliament_members")
      .select(
        "member_id, display_name, given_name, family_name, constituency_name, house_name",
      )
      .eq("is_current_member", true)
      .eq("is_deleted", false)
      .order("member_id", { ascending: true })
      .range(startRange, endRange);

    if (memberId) {
      query = query.eq("member_id", memberId);
    }

    const { data: mps, error } = await query;

    if (error) {
      console.error("Error fetching MPs:", error);
      process.exit(1);
    }

    if (!mps || mps.length === 0) {
      hasMore = false;
      break;
    }

    allMps.push(...(mps as ParliamentMember[]));
    console.log(
      `  Fetched page ${page + 1}: ${
        mps.length
      } MPs (range ${startRange}-${endRange}, total: ${allMps.length})`,
    );

    // If memberId is specified, we only need one result, so stop after first page
    if (memberId && allMps.length > 0) {
      hasMore = false;
      break;
    }

    // If limit is specified and we've reached it, stop
    if (limit && allMps.length >= limit) {
      hasMore = false;
      break;
    }

    // Continue to next page if we got exactly PAGE_SIZE results (might be more)
    // Only stop if we got fewer than PAGE_SIZE
    if (mps.length < PAGE_SIZE) {
      hasMore = false;
    } else {
      page++;
      // Add a small delay between pages to avoid overwhelming the database
      await sleep(100);
    }
  }

  // Apply limit if specified
  const mps = limit ? allMps.slice(0, limit) : allMps;

  if (mps.length === 0) {
    console.log("No MPs found matching criteria");
    process.exit(0);
  }

  console.log(
    `Found ${mps.length} MPs to process (fetched ${allMps.length} total from database)`,
  );

  // Verify we got all MPs - check if we stopped at exactly a page boundary
  if (allMps.length > 0 && allMps.length % PAGE_SIZE === 0) {
    console.log(
      `⚠️  Warning: Fetched exactly ${allMps.length} MPs (multiple of ${PAGE_SIZE}). There might be more MPs. Consider checking the database count.`,
    );
  }

  // Check existing portraits if skip-existing is enabled
  const mpsToProcess: ParliamentMember[] = [];
  if (skipExisting) {
    for (const mp of mps) {
      const { count } = await supabaseAdminClient
        .from("parliament_member_portraits")
        .select("*", { count: "exact", head: true })
        .eq("member_id", mp.member_id)
        .eq("is_deleted", false);

      if ((count ?? 0) < MAX_IMAGES_PER_MP) {
        mpsToProcess.push(mp);
      } else {
        console.log(
          `[${mp.member_id}] Skipping ${mp.display_name} (already has ${count} images)`,
        );
      }
    }
  } else {
    mpsToProcess.push(...mps);
  }

  console.log(`Processing ${mpsToProcess.length} MPs`);

  // Load face detection models once at startup
  // Face detection is REQUIRED - exit if it fails
  console.log("Loading face detection models...");
  try {
    await loadFaceDetectionModels();
  } catch (error) {
    console.error(
      "FATAL: Could not load face detection models. Face detection is required.",
    );
    console.error(
      "Error:",
      error instanceof Error ? error.message : String(error),
    );
    console.error("\nPossible solutions:");
    console.error("  1. Switch to Node.js 20 (currently using Node.js 24)");
    console.error("  2. Use npm instead of pnpm for this project");
    console.error(
      "  3. Check TensorFlow.js installation and rebuild native modules",
    );
    console.error(
      "  4. Ensure all system dependencies are installed (libcairo2-dev, etc.)",
    );
    process.exit(1);
  }

  // Launch browser with better settings
  const browser = await chromium.launch({
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-accelerated-2d-canvas",
      "--disable-gpu",
    ],
  });

  try {
    // Process MPs sequentially to avoid overwhelming sources
    for (const mp of mpsToProcess) {
      await collectImagesForMP(browser, mp);
      await sleep(DELAY_BETWEEN_REQUESTS); // Delay between MPs
    }
  } finally {
    await browser.close();
  }

  // Print statistics
  console.log("\n" + "=".repeat(80));
  console.log("FINAL STATISTICS");
  console.log("=".repeat(80));
  console.log(`Mode: ${isDryRun ? "DRY RUN" : "PRODUCTION"}`);
  console.log(`Total MPs processed: ${stats.length}`);
  console.log(`Total images collected: ${totalImagesCollected}`);

  // Calculate filtered image totals
  const totalFiltered0Faces = stats.reduce(
    (sum, s) => sum + s.imagesFiltered0Faces,
    0,
  );
  const totalFilteredMultipleFaces = stats.reduce(
    (sum, s) => sum + s.imagesFilteredMultipleFaces,
    0,
  );
  const totalFiltered = totalFiltered0Faces + totalFilteredMultipleFaces;

  if (totalFiltered > 0) {
    console.log(`\nFace Detection Filtering:`);
    console.log(`  Total images filtered (0 faces): ${totalFiltered0Faces}`);
    console.log(
      `  Total images filtered (multiple faces): ${totalFilteredMultipleFaces}`,
    );
    console.log(`  Total filtered: ${totalFiltered}`);
  }

  if (isDryRun) {
    console.log(`Total images downloaded: ${totalImagesDownloaded}`);
    console.log(`\nImage folders:`);
    console.log(`  Downloaded: ${DOWNLOAD_FOLDER}`);
    console.log(`  Valid (1 face): ${VALID_FOLDER}`);
    console.log(`  Invalid (0 or multiple faces): ${INVALID_FOLDER}`);

    const mpsWith100 = stats.filter((s) => s.imagesDownloaded >= 100).length;
    const mpsWithLess = stats.filter((s) => s.imagesDownloaded < 100);

    console.log(`\nMPs with 100+ images: ${mpsWith100}`);
    console.log(`MPs with < 100 images: ${mpsWithLess.length}`);

    if (mpsWithLess.length > 0) {
      console.log("\nMPs with < 100 images:");
      mpsWithLess.forEach((s) => {
        console.log(
          `  [${s.member_id}] ${s.display_name || "Unknown"}: ${
            s.imagesDownloaded
          } images`,
        );
        if (s.imagesFiltered0Faces > 0 || s.imagesFilteredMultipleFaces > 0) {
          console.log(
            `    Filtered: ${s.imagesFiltered0Faces} (0 faces), ${s.imagesFilteredMultipleFaces} (multiple faces)`,
          );
        }
        if (s.errors.length > 0) {
          console.log(`    Errors: ${s.errors.length}`);
        }
      });
    }
  } else {
    console.log(`Total images uploaded: ${totalImagesUploaded}`);
    console.log(`\nImage folders (for manual review):`);
    console.log(`  Downloaded: ${DOWNLOAD_FOLDER}`);
    console.log(`  Valid (1 face): ${VALID_FOLDER}`);
    console.log(`  Invalid (0 or multiple faces): ${INVALID_FOLDER}`);

    const mpsWith100 = stats.filter((s) => s.imagesUploaded >= 100).length;
    const mpsWithLess = stats.filter((s) => s.imagesUploaded < 100);

    console.log(`\nMPs with 100+ images: ${mpsWith100}`);
    console.log(`MPs with < 100 images: ${mpsWithLess.length}`);

    if (mpsWithLess.length > 0) {
      console.log("\nMPs with < 100 images:");
      mpsWithLess.forEach((s) => {
        console.log(
          `  [${s.member_id}] ${s.display_name || "Unknown"}: ${
            s.imagesUploaded
          } images`,
        );
        if (s.imagesFiltered0Faces > 0 || s.imagesFilteredMultipleFaces > 0) {
          console.log(
            `    Filtered: ${s.imagesFiltered0Faces} (0 faces), ${s.imagesFilteredMultipleFaces} (multiple faces)`,
          );
        }
        if (s.errors.length > 0) {
          console.log(`    Errors: ${s.errors.length}`);
        }
      });
    }
  }

  const totalErrors = stats.reduce((sum, s) => sum + s.errors.length, 0);
  if (totalErrors > 0) {
    console.log(`\nTotal errors encountered: ${totalErrors}`);
  }

  console.log("\nScript completed!");
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
}
