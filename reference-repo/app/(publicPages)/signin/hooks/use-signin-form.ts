"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { usePostHog } from "posthog-js/react";
import { signInSchema, otpVerificationSchema, appReviewPasswordSchema } from "@/schemas/authSchema";
import { signInWithOtp, verifyOtp, signInWithAppReviewPassword } from "@/app/actions/auth";

export function useSignInForm() {
  const posthog = usePostHog();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showOtpInput, setShowOtpInput] = useState(false);
  const [showPasswordInput, setShowPasswordInput] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [otpValue, setOtpValue] = useState("");

  // Email form
  const emailForm = useForm<z.infer<typeof signInSchema>>({
    resolver: zodResolver(signInSchema),
    defaultValues: {
      email: "",
    },
  });

  // OTP verification form
  const otpForm = useForm<z.infer<typeof otpVerificationSchema>>({
    resolver: zodResolver(otpVerificationSchema),
    defaultValues: {
      email: "",
      token: "",
    },
  });

  // Password form for app review
  const passwordForm = useForm<z.infer<typeof appReviewPasswordSchema>>({
    resolver: zodResolver(appReviewPasswordSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  function isAppReviewEmail(email: string): boolean {
    return (
      process.env.NEXT_PUBLIC_APP_REVIEW_AUTH_ENABLED === "true" &&
      email.toLowerCase() === process.env.NEXT_PUBLIC_APP_REVIEW_EMAIL
    );
  }

  async function onEmailSubmit(values: z.infer<typeof signInSchema>) {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Check if this is the app review email — show password form instead
      if (isAppReviewEmail(values.email)) {
        setUserEmail(values.email);
        passwordForm.reset({ email: values.email, password: "" });
        setShowPasswordInput(true);
        setIsLoading(false);
        return;
      }

      const result = await signInWithOtp(values);
      if (result.success && result.requiresOtp) {
        posthog.capture("signin_email_submitted", {
          email_domain: values.email.split("@")[1],
          auth_method: "otp",
        });
        setUserEmail(values.email);
        setOtpValue("");
        otpForm.reset({
          email: values.email,
          token: "",
        });
        setShowOtpInput(true);
        setSuccess("Verification code sent! Check your email.");
      }

      if (result.error) {
        posthog.capture("signin_failed", {
          email_domain: values.email.split("@")[1],
          auth_method: "otp",
          error_type: "server_error",
          error_message: result.error,
        });
        setError(result.error);
      }
    } catch (err) {
      // Track exception
      posthog.capture("signin_failed", {
        email_domain: values.email.split("@")[1],
        auth_method: "otp",
        error_type: "exception",
        error_message: err instanceof Error ? err.message : "Unknown error",
      });
      setError("An unexpected error occurred. Please try again.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }

  async function onOtpSubmit(values: z.infer<typeof otpVerificationSchema>) {
    setIsLoading(true);
    setError(null);
    let redirecting = false;

    try {
      const result = await verifyOtp(values);
      if (result?.error) {
        if (result.redirectPath) {
          redirecting = true;
          window.location.href = result.redirectPath;
          return;
        }
        // Track OTP verification failure
        posthog.capture("signin_failed", {
          email_domain: values.email.split("@")[1],
          auth_method: "otp",
          error_type: "otp_verification_failed",
          error_message: result.error,
        });
        setError(result.error);
      } else if (result?.success && result?.redirectTo) {
        // Track successful signin completion
        posthog.capture("signin_completed", {
          email_domain: values.email.split("@")[1],
          auth_method: "otp",
          redirect_to: result.redirectTo,
        });
        // Don't set isLoading to false, let the navigation happen
        redirecting = true;
        window.location.href = result.redirectTo;
        return;
      }
    } catch (err) {
      // Track exception during OTP verification
      posthog.capture("signin_failed", {
        email_domain: values.email.split("@")[1],
        auth_method: "otp",
        error_type: "otp_exception",
        error_message: err instanceof Error ? err.message : "Unknown error",
      });
      setError("Verification failed. Please try again.");
      console.error(err);
    } finally {
      if (!redirecting) setIsLoading(false);
    }
  }

  async function onPasswordSubmit(
    values: z.infer<typeof appReviewPasswordSchema>,
  ) {
    setIsLoading(true);
    setError(null);
    let redirecting = false;

    try {
      const result = await signInWithAppReviewPassword(values);
      if (result?.error) {
        posthog.capture("signin_failed", {
          email_domain: values.email.split("@")[1],
          auth_method: "app_review_password",
          error_type: "password_verification_failed",
          error_message: result.error,
        });
        setError(result.error);
      } else if (result?.success && result?.redirectTo) {
        posthog.capture("signin_completed", {
          email_domain: values.email.split("@")[1],
          auth_method: "app_review_password",
          redirect_to: result.redirectTo,
        });
        redirecting = true;
        window.location.href = result.redirectTo;
        return;
      }
    } catch (err) {
      posthog.capture("signin_failed", {
        email_domain: values.email.split("@")[1],
        auth_method: "app_review_password",
        error_type: "password_exception",
        error_message: err instanceof Error ? err.message : "Unknown error",
      });
      setError("An unexpected error occurred. Please try again.");
      console.error(err);
    } finally {
      if (!redirecting) setIsLoading(false);
    }
  }

  function goBackToEmailForm() {
    setShowOtpInput(false);
    setShowPasswordInput(false);
    setError(null);
    setSuccess(null);
  }

  function handleOtpChange(value: string) {
    setOtpValue(value);
  }

  return {
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
    isAppReviewEmail,
    onEmailSubmit,
    onOtpSubmit,
    onPasswordSubmit,
    goBackToEmailForm,
    handleOtpChange,
  };
}