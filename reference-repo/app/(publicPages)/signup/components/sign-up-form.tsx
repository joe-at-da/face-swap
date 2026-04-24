"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { SignupEmailForm } from "@/app/(publicPages)/signup/components/signup-email-form";
import { SignupOTPVerification } from "@/app/(publicPages)/signup/components/signup-otp-verification";
import { useSignUpForm } from "@/app/(publicPages)/signup/hooks/use-signup-form";
import { useUser } from "@/stores/hooks/useUser";

interface SignUpFormProps {
  initialErrorCode?: string | null;
}

export function SignUpForm({ initialErrorCode }: SignUpFormProps) {
  const router = useRouter();
  const { isAuthenticated, isInitialized } = useUser();

  // All hooks must be called before any early returns
  const {
    isLoading,
    error,
    success,
    showOtpInput,
    userEmail,
    isParliamentMember,
    otpValue,
    emailForm,
    otpForm,
    onEmailSubmit,
    onOtpSubmit,
    goBackToEmailForm,
    handleOtpChange,
  } = useSignUpForm(initialErrorCode);

  // Redirect to dashboard if user becomes authenticated (e.g., from another tab)
  useEffect(() => {
    if (isInitialized && isAuthenticated) {
      // Use replace to prevent going back to signup page
      router.replace('/dashboard');
    }
  }, [isInitialized, isAuthenticated, router]);

  // If already authenticated, don't render the form (prevents flash)
  if (isInitialized && isAuthenticated) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">Redirecting to dashboard...</div>
      </div>
    );
  }

  if (showOtpInput) {
    return (
      <SignupOTPVerification
        form={otpForm}
        userEmail={userEmail}
        isParliamentMember={isParliamentMember}
        otpValue={otpValue}
        isLoading={isLoading}
        error={error}
        success={success}
        onOtpChange={handleOtpChange}
        onSubmit={onOtpSubmit}
        onGoBack={goBackToEmailForm}
      />
    );
  }

  return (
    <SignupEmailForm
      form={emailForm}
      isLoading={isLoading}
      error={error}
      success={success}
      onSubmit={onEmailSubmit}
    />
  );
}
