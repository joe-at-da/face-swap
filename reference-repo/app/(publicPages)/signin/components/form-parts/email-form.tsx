"use client";

import { UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { signInSchema } from "@/schemas/authSchema";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Loader2, Shield, Sparkles } from "lucide-react";
import { isMPEmail, getPrimaryMPDomain } from "@/lib/domains";
import Link from "next/link";

interface EmailFormProps {
  form: UseFormReturn<z.infer<typeof signInSchema>>;
  isLoading: boolean;
  error: string | null;
  success: string | null;
  isAppReviewEmail?: (email: string) => boolean;
  onSubmit: (values: z.infer<typeof signInSchema>) => Promise<void>;
}

// Removed local function, using isMPEmail from lib/domains instead

export function EmailForm({
  form,
  isLoading,
  error,
  success,
  isAppReviewEmail,
  onSubmit,
}: EmailFormProps) {
  const currentEmail = form.watch("email");
  const isReviewEmail = isAppReviewEmail?.(currentEmail) ?? false;
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <div className="relative">
                  <Input
                    {...field}
                    type="email"
                    placeholder={`your.name${getPrimaryMPDomain()}`}
                    className={`focus-visible:ring-2 focus-visible:ring-primary ${
                      isMPEmail(field.value) ? "pr-28" : ""
                    }`}
                    disabled={isLoading}
                    autoComplete="email"
                  />
                  {field.value && isMPEmail(field.value) && (
                    <div className="absolute right-2 top-1/2 -translate-y-1/2">
                      <Badge variant="secondary" className="text-xs">
                        <Shield className="mr-1 h-3 w-3" />
                        MP
                      </Badge>
                    </div>
                  )}
                </div>
              </FormControl>
              <FormDescription>
                {isReviewEmail
                  ? "You'll sign in with your password"
                  : "We'll send you a 6-digit verification code"}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {error && (
          <Alert variant="destructive">
            <AlertDescription>
              {error === "ACCOUNT_NOT_FOUND" ? (
                <div className="space-y-2">
                  <p>
                    You don&apos;t have an account. Please sign up to create one.
                  </p>
                  <Link
                    href="/signup"
                    className="text-sm font-medium underline underline-offset-4 hover:text-primary"
                  >
                    Go to Sign Up
                  </Link>
                </div>
              ) : (
                error
              )}
            </AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert className="border-primary/50 bg-primary/5">
            <Sparkles className="h-4 w-4 text-primary" />
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        <Button
          type="submit"
          className="w-full transition-all duration-200 hover:scale-[1.02] hover:shadow-lg"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Sending...
            </>
          ) : (
            <>
              {isReviewEmail
                ? "Continue"
                : "Send Verification Code"}
            </>
          )}
        </Button>
      </form>
    </Form>
  );
}
