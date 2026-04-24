"use client";

import { UseFormReturn } from "react-hook-form";
import { AppReviewPasswordData } from "@/schemas/authSchema";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";

interface PasswordFormProps {
  form: UseFormReturn<AppReviewPasswordData>;
  userEmail: string;
  isLoading: boolean;
  error: string | null;
  onSubmit: (values: AppReviewPasswordData) => Promise<void>;
  onGoBack: () => void;
}

export function PasswordForm({
  form,
  userEmail,
  isLoading,
  error,
  onSubmit,
  onGoBack,
}: PasswordFormProps) {
  return (
    <div className="space-y-6">
      {/* Email Display */}
      <div className="text-center space-y-2">
        <p className="text-sm text-muted-foreground">
          Enter your password to sign in
        </p>
        <p className="font-medium text-foreground">{userEmail}</p>
      </div>

      {/* Password Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Password</FormLabel>
                <FormControl>
                  <Input
                    type="password"
                    placeholder="Enter your password"
                    autoComplete="current-password"
                    disabled={isLoading}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Button
              type="submit"
              className="w-full transition-all duration-200 hover:scale-[1.02] hover:shadow-lg"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign In"
              )}
            </Button>

            <Button
              type="button"
              variant="ghost"
              className="w-full transition-all duration-200 hover:bg-muted/80"
              onClick={onGoBack}
              disabled={isLoading}
            >
              Use a different email
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
