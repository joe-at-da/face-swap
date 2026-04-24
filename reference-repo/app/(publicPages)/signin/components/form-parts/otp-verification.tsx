"use client";

import { UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { otpVerificationSchema } from "@/schemas/authSchema";
import { Button } from "@/components/ui/button";
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
import { OTPInput } from "input-otp";
import { isMPEmail } from "@/lib/domains";

interface OTPVerificationProps {
  form: UseFormReturn<z.infer<typeof otpVerificationSchema>>;
  userEmail: string;
  otpValue: string;
  isLoading: boolean;
  error: string | null;
  success: string | null;
  onOtpChange: (value: string) => void;
  onSubmit: (values: z.infer<typeof otpVerificationSchema>) => Promise<void>;
  onGoBack: () => void;
}

export function OTPVerification({ 
  form, 
  userEmail, 
  otpValue,
  isLoading, 
  error, 
  success, 
  onOtpChange,
  onSubmit,
  onGoBack
}: OTPVerificationProps) {
  return (
    <div className="space-y-6">
      {/* Email Display */}
      <div className="text-center space-y-2">
        <p className="text-sm text-muted-foreground">
          Enter the 6-digit code sent to
        </p>
        <p className="font-medium text-foreground">{userEmail}</p>
        {isMPEmail(userEmail) && (
          <Badge variant="secondary" className="mx-auto">
            <Shield className="mr-1 h-3 w-3" />
            Parliament Member Account
          </Badge>
        )}
      </div>

      {/* OTP Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="token"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Verification Code</FormLabel>
                <FormControl>
                  <div data-input-otp-container>
                    <OTPInput
                      maxLength={6}
                      value={otpValue}
                      onChange={(value) => {
                        onOtpChange(value);
                        field.onChange(value);
                      }}
                      disabled={isLoading}
                      containerClassName="flex items-center gap-2"
                      render={({ slots }) => (
                        <>
                          {slots.map((slot, idx) => (
                            <div
                              key={idx}
                              className="relative flex h-9 w-9 items-center justify-center border border-input bg-background text-sm transition-all first:rounded-l-md last:rounded-r-md"
                              data-active={slot.isActive}
                            >
                              {slot.char}
                              {slot.hasFakeCaret && (
                                <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                                  <div className="h-4 w-px animate-pulse bg-foreground duration-1000" />
                                </div>
                              )}
                            </div>
                          ))}
                        </>
                      )}
                    />
                  </div>
                </FormControl>
                <FormDescription>
                  Enter the 6-digit code from your email
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="border-primary/50 bg-primary/5">
              <Sparkles className="h-4 w-4 text-primary" />
              <AlertDescription>{success}</AlertDescription>
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
                  Verifying...
                </>
              ) : (
                "Verify & Sign In"
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