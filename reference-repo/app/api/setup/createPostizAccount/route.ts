import { handleError } from "@/lib/getErrorMessage";
import { signupUserToPostiz } from "@/services/postiz/postizApi";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { NextResponse } from "next/server";

// Force this route to use Node.js runtime for postgres compatibility
export const runtime = "nodejs";

export async function GET() {
  try {
    const supabase = await createSupabaseServerClient();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    const email = user.id + "@mpai.com";
    const password = user.id;
    const company = user.email || user.id;
    const response = await signupUserToPostiz(email, password, company);
    if (response.error) {
      throw new Error(response.error);
    }
    const apiKey = response.data;
    if (!apiKey) {
      throw new Error("Failed to create Postiz account");
    }

    await supabaseAdminClient
      .from("user_roles")
      .update({
        postiz_api_key: apiKey,
        postiz_email: email,
        postiz_password: password,
      })
      .eq("user_id", user.id);

    return NextResponse.json({ data: "Postiz account created successfully" });
  } catch (error) {
    console.error("MPs fetch error:", error);
    return NextResponse.json(
      {
        error: handleError(error, {
          component: "api/setup/createPostizAccount",
          action: "GET",
          route: "/api/setup/createPostizAccount",
        }),
      },
      { status: 500 }
    );
  }
}
