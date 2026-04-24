import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { setupStep3Schema } from "@/schemas/authSchema";
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
    const validatedData = setupStep3Schema.parse(body);

    // Update user_roles with MP following using admin client
    // Regular users don't have permission to modify user_roles table
    const { error: updateError } = await supabaseAdminClient
      .from("user_roles")
      .update({ 
        member_id: validatedData.selectedMpId || null
      })
      .eq("user_id", user.id);

    if (updateError) {
      throw updateError;
    }

    return NextResponse.json({ 
      message: "MP following updated successfully",
      data: validatedData 
    });

  } catch (error) {
    console.error("MP follow update error:", error);
    const { data: { user } } = await (await createSupabaseServerClient()).auth.getUser();
    return NextResponse.json(
      { error: handleError(error, {
        component: 'api/setup/mp-follow',
        action: 'POST',
        userId: user?.id,
        route: '/api/setup/mp-follow',
      }) },
      { status: 500 }
    );
  }
}