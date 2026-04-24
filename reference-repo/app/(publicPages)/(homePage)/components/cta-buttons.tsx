import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";

export async function CTAButtons() {
  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();

  return (
    <div className="mt-8 flex justify-center">
      <Button
        size="lg"
        className="w-full sm:w-auto min-h-[44px] px-8 text-lg bg-foreground text-primary-foreground"
        asChild
      >
        <Link href={user ? "/dashboard" : "/signup"}>
          {user ? "Go to Dashboard" : "See it in Action"}
          <ArrowRight className="ml-2 h-5 w-5" aria-hidden="true" />
        </Link>
      </Button>
    </div>
  );
}