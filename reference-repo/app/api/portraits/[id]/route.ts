import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { S3Client, DeleteObjectCommand } from "@aws-sdk/client-s3";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createSupabaseServerClient();
    const { id } = await params;

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Check if user has @veedoo.io or @veedoo.com email
    const email = user.email;
    if (
      !email ||
      (!email.endsWith("@veedoo.io") && !email.endsWith("@veedoo.com"))
    ) {
      return NextResponse.json(
        { error: "Forbidden: Access restricted to Veedoo team members" },
        { status: 403 }
      );
    }

    // Validate portrait ID
    if (!id || typeof id !== "string") {
      return NextResponse.json(
        { error: "Invalid portrait ID" },
        { status: 400 }
      );
    }

    // Get the portrait record to extract image URL before deleting
    // Verify portrait exists and isn't already deleted
    const { data: portrait, error: fetchError } = await supabaseAdminClient
      .from("parliament_member_portraits")
      .select("image_url, is_deleted")
      .eq("id", id)
      .single();

    if (fetchError || !portrait) {
      console.error("Failed to fetch portrait:", fetchError);
      return NextResponse.json(
        { error: "Portrait not found or does not exist" },
        { status: 404 }
      );
    }

    // Check if portrait is already deleted
    if (portrait.is_deleted) {
      return NextResponse.json(
        { error: "Portrait has already been deleted" },
        { status: 409 }
      );
    }

    // Delete image from DigitalOcean Spaces if it's stored there
    const imageUrl = portrait.image_url;
    if (imageUrl && imageUrl.includes("digitaloceanspaces.com")) {
      try {
        const endpoint = process.env.DO_SPACES_ENDPOINT;
        const region = process.env.DO_SPACES_REGION;
        const accessKeyId = process.env.DO_SPACES_KEY;
        const secretAccessKey = process.env.DO_SPACES_SECRET;
        const bucketName = process.env.DO_SPACES_BUCKET;

        if (endpoint && region && accessKeyId && secretAccessKey) {
          // Extract the key from the URL
          // URL format: https://thempai.{region}.cdn.digitaloceanspaces.com/mp_pictures/{memberId}/{filename}
          const urlParts = imageUrl.split(".cdn.digitaloceanspaces.com/");
          if (urlParts.length === 2) {
            const key = urlParts[1];

            const s3Client = new S3Client({
              endpoint,
              region,
              credentials: {
                accessKeyId,
                secretAccessKey,
              },
              forcePathStyle: false,
            });

            const deleteCommand = new DeleteObjectCommand({
              Bucket: bucketName,
              Key: key,
            });

            await s3Client.send(deleteCommand);
            console.log(`Deleted image from DO Spaces: ${key}`);
          }
        }
      } catch (s3Error) {
        // Log error but don't fail the request - we still want to delete the DB record
        // The image may have already been deleted or the URL might be invalid
        console.error(
          "Failed to delete image from DO Spaces (continuing with DB deletion):",
          s3Error
        );
      }
    }

    // Soft delete the portrait
    // Use select to verify the update affected a row
    const { data: updatedPortrait, error: deleteError } =
      await supabaseAdminClient
        .from("parliament_member_portraits")
        .update({
          is_deleted: true,
          deleted_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        .eq("id", id)
        .eq("is_deleted", false) // Only update if not already deleted
        .select("id")
        .single();

    if (deleteError) {
      console.error("Failed to delete portrait:", deleteError);
      return NextResponse.json(
        { error: "Failed to delete portrait from database" },
        { status: 500 }
      );
    }

    // Verify the update actually affected a row
    if (!updatedPortrait) {
      console.error("Portrait update did not affect any rows");
      return NextResponse.json(
        {
          error:
            "Portrait was not deleted. It may have been deleted by another process.",
        },
        { status: 409 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "Portrait deleted successfully",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Delete portrait error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to delete portrait: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createSupabaseServerClient();
    const { id } = await params;

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Check if user has @veedoo.io or @veedoo.com email
    const email = user.email;
    if (
      !email ||
      (!email.endsWith("@veedoo.io") && !email.endsWith("@veedoo.com"))
    ) {
      return NextResponse.json(
        { error: "Forbidden: Access restricted to Veedoo team members" },
        { status: 403 }
      );
    }

    // Validate portrait ID
    if (!id || typeof id !== "string") {
      return NextResponse.json(
        { error: "Invalid portrait ID" },
        { status: 400 }
      );
    }

    // Parse request body
    let body: { is_valid_mp_image?: boolean };
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { is_valid_mp_image } = body;

    // Validate that is_valid_mp_image is provided and is a boolean
    if (typeof is_valid_mp_image !== "boolean") {
      return NextResponse.json(
        { error: "is_valid_mp_image must be a boolean" },
        { status: 400 }
      );
    }

    // Verify portrait exists and isn't deleted before updating
    const { data: existingPortrait, error: fetchError } =
      await supabaseAdminClient
        .from("parliament_member_portraits")
        .select("id, is_deleted")
        .eq("id", id)
        .single();

    if (fetchError || !existingPortrait) {
      console.error("Failed to fetch portrait:", fetchError);
      return NextResponse.json(
        { error: "Portrait not found or does not exist" },
        { status: 404 }
      );
    }

    // Check if portrait is deleted
    if (existingPortrait.is_deleted) {
      return NextResponse.json(
        { error: "Cannot update a deleted portrait" },
        { status: 409 }
      );
    }

    // Update the portrait
    // Use select to verify the update affected a row
    const { data: updatedPortrait, error: updateError } =
      await supabaseAdminClient
        .from("parliament_member_portraits")
        .update({
          is_valid_mp_image: is_valid_mp_image,
          updated_at: new Date().toISOString(),
        })
        .eq("id", id)
        .eq("is_deleted", false) // Only update if not deleted
        .select("id")
        .single();

    if (updateError) {
      console.error("Failed to update portrait:", updateError);
      return NextResponse.json(
        { error: "Failed to update portrait in database" },
        { status: 500 }
      );
    }

    // Verify the update actually affected a row
    if (!updatedPortrait) {
      console.error("Portrait update did not affect any rows");
      return NextResponse.json(
        {
          error:
            "Portrait was not updated. It may have been deleted by another process.",
        },
        { status: 409 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "Portrait updated successfully",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Update portrait error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to update portrait: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
