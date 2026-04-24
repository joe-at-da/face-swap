import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";

export async function POST(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Parse form data
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: "No file provided" },
        { status: 400 }
      );
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      return NextResponse.json(
        { error: "File must be an image" },
        { status: 400 }
      );
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      return NextResponse.json(
        { error: "File size must be less than 10MB" },
        { status: 400 }
      );
    }

    // Generate unique filename
    const timestamp = Date.now();
    const fileExtension = file.name.split('.').pop() || 'png';
    const fileName = `watermark_${timestamp}.${fileExtension}`;
    const filePath = `${user.id}/${fileName}`;

    // Convert file to array buffer
    const arrayBuffer = await file.arrayBuffer();
    const fileBuffer = new Uint8Array(arrayBuffer);

    // Upload to Supabase storage
    const { error: uploadError } = await supabase.storage
      .from('watermarks')
      .upload(filePath, fileBuffer, {
        contentType: file.type,
        cacheControl: '3600',
        upsert: false
      });

    if (uploadError) {
      console.error('Upload error:', uploadError);
      return NextResponse.json(
        { error: "Failed to upload watermark" },
        { status: 500 }
      );
    }

    // Get public URL
    const { data: { publicUrl } } = supabase.storage
      .from('watermarks')
      .getPublicUrl(filePath);

    console.log(
      `[Watermarks API] Uploaded watermark for user ${user.id}: ${filePath}`
    );

    return NextResponse.json({
      success: true,
      publicUrl,
      fileName,
      filePath,
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Watermark upload error:', error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Watermark upload failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

// DELETE endpoint to remove watermarks
export async function DELETE(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Get file path from query params
    const { searchParams } = new URL(request.url);
    const filePath = searchParams.get('filePath');

    if (!filePath) {
      return NextResponse.json(
        { error: "File path is required" },
        { status: 400 }
      );
    }

    // Verify the file belongs to the user
    if (!filePath.startsWith(`${user.id}/`)) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      );
    }

    // Delete from Supabase storage
    const { error: deleteError } = await supabase.storage
      .from('watermarks')
      .remove([filePath]);

    if (deleteError) {
      console.error('Delete error:', deleteError);
      return NextResponse.json(
        { error: "Failed to delete watermark" },
        { status: 500 }
      );
    }

    console.log(
      `[Watermarks API] Deleted watermark for user ${user.id}: ${filePath}`
    );

    return NextResponse.json({
      success: true,
      message: "Watermark deleted successfully",
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Watermark delete error:', error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Watermark delete failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

// GET endpoint for health check
export async function GET() {
  return NextResponse.json({
    success: true,
    message: "Watermarks Upload API is running",
    endpoint: "/api/watermarks/upload",
    methods: ["POST", "DELETE"],
    auth: "Required (authenticated user)",
    timestamp: new Date().toISOString(),
  });
}