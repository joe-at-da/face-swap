import { NextRequest, NextResponse } from "next/server";
import {
  FIBERY_BASE_URL,
  fetchFiberyWithRateLimit,
  getLegalDocumentAssetFetch,
  getLegalDocumentHtml,
  isApprovedLegalDocumentAssetPath,
  isLegalDocumentKey,
} from "@/lib/legal/fibery-documents";
import { ErrorLogger } from "@/lib/errorLogger";

export async function GET(request: NextRequest) {
  const doc = request.nextUrl.searchParams.get("doc");
  const path = request.nextUrl.searchParams.get("path");

  if (!doc || !isLegalDocumentKey(doc)) {
    return NextResponse.json({ error: "Invalid document." }, { status: 400 });
  }

  if (!path) {
    return NextResponse.json({ error: "Invalid file path." }, { status: 400 });
  }

  const auth = await getLegalDocumentAssetFetch(doc);
  if (!auth) {
    return NextResponse.json({ error: "Service unavailable." }, { status: 500 });
  }

  let parsedPath: URL;
  try {
    // Normalize through the URL constructor — the same normalization that
    // `normalizeFiberyFilePath` applies on the write side.  This resolves
    // traversal sequences (../) and decodes safe percent-encoded bytes while
    // preserving reserved characters like %2F, keeping both sides in sync.
    // Intentionally no `decodeURIComponent` step: it would decode %2F → /
    // which the URL constructor leaves encoded, causing allowlist mismatches.
    parsedPath = new URL(path, "https://dummy");
  } catch {
    return NextResponse.json({ error: "Invalid file path." }, { status: 400 });
  }

  const normalized = parsedPath.pathname;
  if (!normalized.startsWith("/api/files/")) {
    return NextResponse.json({ error: "Invalid file path." }, { status: 400 });
  }

  const approvedAssetPath = `${normalized}${parsedPath.search}`;
  if (!isApprovedLegalDocumentAssetPath(doc, approvedAssetPath)) {
    // Allowlist miss — re-fetch the document HTML so the approved-paths set
    // is rebuilt from the latest Fibery content.  `getLegalDocumentHtml` is
    // safe to call on every miss: it returns from cache when fresh (60 s TTL)
    // and deduplicates concurrent in-flight requests, so Fibery is hit at
    // most once per TTL window regardless of traffic volume.
    await getLegalDocumentHtml(doc);
    if (!isApprovedLegalDocumentAssetPath(doc, approvedAssetPath)) {
      return NextResponse.json(
        { error: "File path not approved." },
        { status: 403 },
      );
    }
  }

  const upstreamUrl = new URL(normalized, FIBERY_BASE_URL);
  parsedPath.searchParams.forEach((value, key) => {
    upstreamUrl.searchParams.set(key, value);
  });
  auth.searchParams.forEach((value, key) => {
    upstreamUrl.searchParams.set(key, value);
  });

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetchFiberyWithRateLimit(upstreamUrl, {
      headers: auth.headers,
      next: { revalidate: 3600, tags: [auth.cacheTag] },
      signal: AbortSignal.timeout(10_000),
    });
  } catch (error) {
    ErrorLogger.logApiError(
      error,
      "/api/legal/fibery-file",
      "GET",
      undefined,
      502,
    );
    return NextResponse.json(
      { error: "Upstream file request failed." },
      { status: 502 },
    );
  }

  if (!upstreamResponse.ok) {
    return NextResponse.json(
      { error: "File request failed." },
      { status: 502 },
    );
  }

  // Explicit safe image types — excludes image/svg+xml which can embed
  // JavaScript and execute in the application's origin when navigated directly.
  const ALLOWED_CONTENT_TYPES = [
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/avif",
    "application/pdf",
    "text/plain",
    "application/json",
  ];

  const headers = new Headers();
  const contentType = upstreamResponse.headers.get("content-type");
  const cacheControl = upstreamResponse.headers.get("cache-control");

  // Prevent browsers from MIME-sniffing a different content type.
  headers.set("X-Content-Type-Options", "nosniff");

  const baseType = contentType?.split(";")[0]?.trim().toLowerCase();
  if (baseType && ALLOWED_CONTENT_TYPES.includes(baseType)) {
    headers.set("Content-Type", contentType ?? baseType);
  } else {
    // Force download for unrecognised types so the browser never renders them inline.
    headers.set("Content-Type", "application/octet-stream");
    headers.set("Content-Disposition", "attachment");
  }

  headers.set("Cache-Control", cacheControl || "public, max-age=3600");

  // Stream the response body instead of buffering the entire file into memory
  return new NextResponse(upstreamResponse.body, { headers });
}
