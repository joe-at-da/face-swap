"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { EmailForm } from "@/app/(publicPages)/signin/components/form-parts/email-form";
import { OTPVerification } from "@/app/(publicPages)/signin/components/form-parts/otp-verification";
import { PasswordForm } from "@/app/(publicPages)/signin/components/form-parts/password-form";
import { useSignInForm } from "@/app/(publicPages)/signin/hooks/use-signin-form";
import { useUser } from "@/stores/hooks/useUser";

export function SignInForm() {
  const router = useRouter();
  const { isAuthenticated, isInitialized } = useUser();

  // All hooks must be called before any early returns
  const {
    isLoading,
    error,
    success,
    showOtpInput,
    showPasswordInput,
    userEmail,
    otpValue,
    emailForm,
    otpForm,
    passwordForm,
    onEmailSubmit,
    onOtpSubmit,
    onPasswordSubmit,
    isAppReviewEmail,
    goBackToEmailForm,
    handleOtpChange,
  } = useSignInForm();

  // Redirect to dashboard if user becomes authenticated (e.g., from another tab)
  useEffect(() => {
    if (isInitialized && isAuthenticated) {
      // Use replace to prevent going back to signin page
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

  if (showPasswordInput) {
    return (
      <PasswordForm
        form={passwordForm}
        userEmail={userEmail}
        isLoading={isLoading}
        error={error}
        onSubmit={onPasswordSubmit}
        onGoBack={goBackToEmailForm}
      />
    );
  }

  if (showOtpInput) {
    return (
      <OTPVerification
        form={otpForm}
        userEmail={userEmail}
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
    <EmailForm
      form={emailForm}
      isLoading={isLoading}
      error={error}
      success={success}
      isAppReviewEmail={isAppReviewEmail}
      onSubmit={onEmailSubmit}
    />
  );
}
