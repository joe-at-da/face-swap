"use client";

import { UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { signupSchema } from "@/schemas/authSchema";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import Link from "next/link";
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

interface SignupEmailFormProps {
  form: UseFormReturn<z.infer<typeof signupSchema>>;
  isLoading: boolean;
  error: string | null;
  success: string | null;
  onSubmit: (values: z.infer<typeof signupSchema>) => Promise<void>;
}

export function SignupEmailForm({
  form,
  isLoading,
  error,
  success,
  onSubmit,
}: SignupEmailFormProps) {
  return (
    <div className="space-y-4">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email Address</FormLabel>
                <FormControl>
                  <div className="relative">
                    <Input
                      {...field}
                      type="email"
                      placeholder={`your.name${getPrimaryMPDomain()}`}
                      className={`focus-visible:ring-2 focus-visible:ring-primary ${isMPEmail(field.value) ? "pr-28" : ""}`}
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
                  We&apos;ll send you a verification code to complete registration
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="acceptedTerms"
            render={({ field }) => (
              <FormItem className="flex items-start gap-3 space-y-0 rounded-md border border-border/60 p-4">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    disabled={isLoading}
                    onCheckedChange={(checked) => field.onChange(checked === true)}
                    className="mt-0.5"
                  />
                </FormControl>
                <div className="space-y-1 leading-relaxed">
                  <FormLabel className="cursor-pointer text-sm font-normal">
                    I agree to the{" "}
                    <Link
                      href="/terms-and-conditions"
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium underline underline-offset-4 hover:text-primary"
                    >
                      Terms & Conditions
                    </Link>
                  </FormLabel>
                  <FormMessage />
                </div>
              </FormItem>
            )}
          />

          {error && (
            <Alert variant="destructive">
              <AlertDescription>
                {error.includes("We are unable to automate your account creation") ? (
                  <div className="space-y-2">
                    <p>{error}</p>
                    <Link 
                      href="/contact" 
                      className="text-sm font-medium underline underline-offset-4 hover:text-primary"
                    >
                      Contact Us
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
                Creating Account...
              </>
            ) : (
              "Create Account"
            )}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/signin" className="text-secondary-foreground hover:underline">
              Sign in instead
            </Link>
          </p>
        </form>
      </Form>
    </div>
  );
}
