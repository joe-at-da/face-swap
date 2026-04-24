"use client";

import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Loader2, ArrowLeft, Mail } from "lucide-react";

interface InvitationVerifyProps {
  email: string;
  otpValue: string;
  onOtpChange: (value: string) => void;
  onVerify: () => void;
  onBack: () => void;
  isSubmitting: boolean;
  isSignIn: boolean;
  error: string | null;
}

export function InvitationVerify({
  email,
  otpValue,
  onOtpChange,
  onVerify,
  onBack,
  isSubmitting,
  isSignIn,
  error,
}: InvitationVerifyProps) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center pb-6">
          <div className="flex justify-center mb-6">
            <div className="rounded-full bg-primary/10 p-4">
              <Mail className="h-8 w-8 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl font-semibold">Verify Your Email</CardTitle>
          <CardDescription className="text-base mt-2">
            We&apos;ve sent a 6-digit verification code to
          </CardDescription>
          <p className="font-medium text-foreground mt-1">{email}</p>
        </CardHeader>
        <CardContent className="space-y-6 px-8 pb-8">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            <Label htmlFor="otp" className="text-center block text-sm font-medium">
              Enter verification code
            </Label>
            <div className="flex justify-center">
              <InputOTP
                id="otp"
                value={otpValue}
                onChange={onOtpChange}
                maxLength={6}
                autoFocus
                className="gap-2"
              >
                <InputOTPGroup className="gap-2">
                  <InputOTPSlot index={0} className="w-12 h-12 text-lg" />
                  <InputOTPSlot index={1} className="w-12 h-12 text-lg" />
                  <InputOTPSlot index={2} className="w-12 h-12 text-lg" />
                  <InputOTPSlot index={3} className="w-12 h-12 text-lg" />
                  <InputOTPSlot index={4} className="w-12 h-12 text-lg" />
                  <InputOTPSlot index={5} className="w-12 h-12 text-lg" />
                </InputOTPGroup>
              </InputOTP>
            </div>
          </div>

          <div className="space-y-4 pt-2">
            <Button
              onClick={onVerify}
              disabled={otpValue.length !== 6 || isSubmitting}
              className="w-full h-12"
              size="lg"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 motion-safe:animate-spin" />
                  Verifying...
                </>
              ) : (
                isSignIn ? "Verify & Accept Invitation" : "Verify & Join Team"
              )}
            </Button>
            <Button variant="ghost" onClick={onBack} className="w-full h-12">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to invitation
            </Button>
          </div>

          <p className="text-xs text-center text-muted-foreground pt-4">
            Didn&apos;t receive the code? Check your spam folder or try again in a few moments.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
