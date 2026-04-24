import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { setupStep1Schema } from "@/schemas/authSchema";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";

export async function POST(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();
    
    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Parse and validate request body
    const body = await request.json();
    const validatedData = setupStep1Schema.parse(body);

    // Update user metadata with profile information
    const { error: updateError } = await supabase.auth.updateUser({
      data: {
        first_name: validatedData.firstName,
        last_name: validatedData.lastName,
        profile_image: validatedData.profileImage || null,
        profile_completed: true,
      }
    });

    if (updateError) {
      throw updateError;
    }

    return NextResponse.json({ 
      message: "Profile updated successfully",
      data: validatedData 
    });

  } catch (error) {
    console.error("Profile update error:", error);
    const { data: { user } } = await (await createSupabaseServerClient()).auth.getUser();
    return NextResponse.json(
      { error: handleError(error, {
        component: 'api/setup/profile',
        action: 'POST',
        userId: user?.id,
        route: '/api/setup/profile',
      }) },
      { status: 500 }
    );
  }
}