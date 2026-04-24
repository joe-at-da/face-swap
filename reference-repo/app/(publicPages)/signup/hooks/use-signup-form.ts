"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { usePostHog } from "posthog-js/react";
import { signupSchema, otpVerificationSchema } from "@/schemas/authSchema";
import { signUp, verifyOtp } from "@/app/actions/auth";
import { CALLBACK_ERROR_MESSAGES } from "@/lib/auth/callback-errors";

const UNKNOWN_CALLBACK_ERROR =
  "Something went wrong during sign-up. Please try again or contact support.";

export function useSignUpForm(initialErrorCode?: string | null) {
  const posthog = usePostHog();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(
    initialErrorCode
      ? CALLBACK_ERROR_MESSAGES[initialErrorCode] ?? UNKNOWN_CALLBACK_ERROR
      : null,
  );
  const [success, setSuccess] = useState<string | null>(null);
  const [showOtpInput, setShowOtpInput] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [isParliamentMember, setIsParliamentMember] = useState(false);
  const [otpValue, setOtpValue] = useState("");

  // Email form
  const emailForm = useForm<z.infer<typeof signupSchema>>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      email: "",
      acceptedTerms: false,
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

  async function onEmailSubmit(values: z.infer<typeof signupSchema>) {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await signUp(values);

      if (result.success && result.requiresOtp) {
        // Track successful email submission
        posthog.capture("signup_email_submitted", {
          email_domain: values.email.split("@")[1],
          is_parliament_member: result.isParliamentMember || false,
        });

        // Track if parliament member detected
        if (result.isParliamentMember) {
          posthog.capture("signup_parliament_detected", {
            email_domain: values.email.split("@")[1],
          });
        }

        setUserEmail(values.email);
        setIsParliamentMember(result.isParliamentMember || false);
        setOtpValue(""); // Clear OTP value
        otpForm.reset({
          email: values.email,
          token: "",
        });
        setShowOtpInput(true);
        setSuccess("Verification code sent! Check your email to complete signup.");
      } else if (result.error) {
        // Track signup failure
        posthog.capture("signup_failed", {
          email_domain: values.email.split("@")[1],
          error_type: "server_error",
          error_message: result.error,
        });
        setError(result.error);
      } else {
        // Track unexpected failure
        posthog.capture("signup_failed", {
          email_domain: values.email.split("@")[1],
          error_type: "unexpected_result",
        });
        setError("Signup failed. Please try again.");
      }
    } catch (err) {
      // Track exception
      posthog.capture("signup_failed", {
        email_domain: values.email.split("@")[1],
        error_type: "exception",
        error_message: err instanceof Error ? err.message : "Unknown error",
      });
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  async function onOtpSubmit(values: z.infer<typeof otpVerificationSchema>) {
    setIsLoading(true);
    setError(null);
    let redirecting = false;

    // Track OTP submission attempt
    posthog.capture("signup_otp_submitted", {
      email_domain: values.email.split("@")[1],
      is_parliament_member: isParliamentMember,
    });

    try {
      const result = await verifyOtp(values);
      if (result?.error) {
        if (result.redirectPath) {
          redirecting = true;
          window.location.href = result.redirectPath;
          return;
        }
        // Track OTP verification failure
        posthog.capture("signup_failed", {
          email_domain: values.email.split("@")[1],
          error_type: "otp_verification_failed",
          error_message: result.error,
        });
        setError(result.error);
      } else if (result?.success && result?.redirectTo) {
        // Track successful signup completion
        posthog.capture("signup_completed", {
          email_domain: values.email.split("@")[1],
          is_parliament_member: isParliamentMember,
          redirect_to: result.redirectTo,
        });
        // Don't set isLoading to false, let the navigation happen
        redirecting = true;
        window.location.href = result.redirectTo;
        return;
      }
    } catch (err) {
      // Track exception during OTP verification
      posthog.capture("signup_failed", {
        email_domain: values.email.split("@")[1],
        error_type: "otp_exception",
        error_message: err instanceof Error ? err.message : "Unknown error",
      });
      setError("Verification failed. Please try again.");
    } finally {
      if (!redirecting) setIsLoading(false);
    }
  }

  function goBackToEmailForm() {
    setShowOtpInput(false);
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
    userEmail,
    isParliamentMember,
    otpValue,
    emailForm,
    otpForm,
    onEmailSubmit,
    onOtpSubmit,
    goBackToEmailForm,
    handleOtpChange,
  };
}
