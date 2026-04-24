import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { ErrorLogger } from "@/lib/errorLogger";

const ALLOWED_SUFFIX = ".digitaloceanspaces.com";

export async function GET(request: NextRequest) {
  let userId: string | undefined;

  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    userId = user.id;

    const url = request.nextUrl.searchParams.get("url");

    if (!url) {
      return NextResponse.json(
        { error: "Missing url parameter" },
        { status: 400 }
      );
    }

    let parsedUrl: URL;
    try {
      parsedUrl = new URL(url);
    } catch {
      return NextResponse.json({ error: "Invalid URL" }, { status: 400 });
    }

    if (!parsedUrl.hostname.endsWith(ALLOWED_SUFFIX)) {
      return NextResponse.json(
        { error: "URL domain not allowed" },
        { status: 400 }
      );
    }

    if (parsedUrl.protocol !== "https:") {
      return NextResponse.json(
        { error: "Only HTTPS URLs allowed" },
        { status: 400 }
      );
    }

    const headResponse = await fetch(url, {
      method: "HEAD",
      redirect: "error",
      signal: AbortSignal.timeout(5000),
    });

    if (!headResponse.ok) {
      return NextResponse.json(
        { error: "Failed to fetch video metadata" },
        { status: 502 }
      );
    }

    const contentLength = headResponse.headers.get("content-length");
    const parsed = contentLength ? parseInt(contentLength, 10) : null;
    const sizeBytes = parsed !== null && Number.isNaN(parsed) ? null : parsed;

    return NextResponse.json(
      { size_bytes: sizeBytes },
      { headers: { "Cache-Control": "private, max-age=3600" } }
    );
  } catch (error) {
    ErrorLogger.logApiError(
      error instanceof Error ? error : new Error(String(error)),
      "/api/video-size",
      "GET",
      userId
    );
    return NextResponse.json(
      { error: "Failed to get video size" },
      { status: 500 }
    );
  }
}
