"use client";

import { useEffect, useRef, useState } from "react";
import { signUp, verifyOtp, checkUserExistsByEmail, signInWithOtp } from "@/app/actions/auth";
import { acceptInvitationDirectly } from "@/app/actions/teams";
import type { AcceptInvitationError } from "@/app/actions/teams";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import { ErrorLogger } from "@/lib/errorLogger";
import { toast } from "sonner";
import type { InvitationData, InvitationStep } from "../types";
import { CALLBACK_ERROR_MESSAGES } from "@/lib/auth/callback-errors";

const UNKNOWN_CALLBACK_ERROR =
  "Something went wrong during sign-in. Please try again or contact support.";

const ERROR_MESSAGES: Record<AcceptInvitationError, string> = {
  SESSION_EXPIRED: "Your session has expired. Please sign in again to accept this invitation.",
  INVITATION_EXPIRED: "This invitation is no longer valid. It may have expired or already been accepted.",
  EMAIL_MISMATCH: "Your session changed. This invitation was sent to a different email address.",
  TERMS_REQUIRED: "You must agree to the Terms & Conditions before continuing.",
  TERMS_RECORDING_FAILED: "Could not record your terms acceptance. Please try again.",
  ACCEPTANCE_FAILED: "Failed to accept the invitation. Please try again or contact support.",
  INVALID_TOKEN: "This invitation link appears to be invalid.",
  UNEXPECTED_ERROR: "Something went wrong. Please try again or contact support.",
};

export function useInvitationState(
  token: string,
  currentUserEmail: string | null,
  initialErrorCode?: string | null,
) {
  const tokenRef = useRef(token);
  tokenRef.current = token;
  const expectedSessionEmailRef = useRef(currentUserEmail);
  const initialErrorCodeRef = useRef(initialErrorCode);

  const [invitation, setInvitation] = useState<InvitationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(
    initialErrorCode
      ? CALLBACK_ERROR_MESSAGES[initialErrorCode] ?? UNKNOWN_CALLBACK_ERROR
      : null,
  );
  const [step, setStep] = useState<InvitationStep>("view");
  const [otpValue, setOtpValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [userExists, setUserExists] = useState<boolean | null>(null);
  const [authMode, setAuthMode] = useState<"signup" | "signin" | null>(null);
  const [canDirectAccept, setCanDirectAccept] = useState(false);
  const [sessionMismatch, setSessionMismatch] = useState(false);
  const [sessionEmail, setSessionEmail] = useState(currentUserEmail);
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  // Show mismatch notice if server-detected mismatch OR if direct-accept returned EMAIL_MISMATCH
  const emailMismatch = sessionMismatch || (
    sessionEmail && invitation
      ? sessionEmail.toLowerCase() !== invitation.email.toLowerCase()
      : false
  );

  useEffect(() => {
    expectedSessionEmailRef.current = currentUserEmail;
    setSessionEmail(currentUserEmail);
  }, [currentUserEmail]);

  // Reload when user returns to the tab after signing in/out elsewhere,
  // so the server-rendered currentUserEmail prop stays fresh.
  useEffect(() => {
    function handleVisibilityChange() {
      if (document.visibilityState !== "visible") return;
      const supabase = createSupabaseBrowserClient();
      supabase.auth.getUser().then(({ data: { user } }) => {
        const browserEmail = user?.email ?? null;
        if (browserEmail !== expectedSessionEmailRef.current) {
          window.location.reload();
        }
      });
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  useEffect(() => {
    const abortController = new AbortController();
    let stale = false;

    // Reset all state when token/email changes (e.g. client-side navigation between invites)
    setInvitation(null);
    setCanDirectAccept(false);
    setSessionMismatch(false);
    setUserExists(null);
    // Consume the initial error code once, then clear so subsequent effect
    // re-runs (e.g. visibility-change reload) don't re-display a stale error.
    const pendingErrorCode = initialErrorCodeRef.current;
    const hadInitialError = !!pendingErrorCode;
    initialErrorCodeRef.current = null;
    setError(
      pendingErrorCode
        ? CALLBACK_ERROR_MESSAGES[pendingErrorCode] ?? UNKNOWN_CALLBACK_ERROR
        : null,
    );
    setLoading(true);
    setStep("view");
    setOtpValue("");
    setAuthMode(null);
    setIsSubmitting(false);
    setAcceptedTerms(false);

    async function loadInvitation() {
      try {
        const timeoutSignal = typeof AbortSignal.timeout === "function"
          ? AbortSignal.timeout(15_000)
          : undefined;
        const signal = timeoutSignal && typeof AbortSignal.any === "function"
          ? AbortSignal.any([abortController.signal, timeoutSignal])
          : abortController.signal;
        const response = await fetch(`/api/teams/invitation/${token}`, { signal });
        if (stale) return;
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch invitation");
        }

        setInvitation(data.invitation);
        if (!hadInitialError) {
          setError(null);
        }

        if (currentUserEmail && data.invitation?.email &&
            currentUserEmail.toLowerCase() === data.invitation.email.toLowerCase()) {
          setCanDirectAccept(true);
          setUserExists(true);
        } else if (data.invitation?.email) {
          const { exists } = await checkUserExistsByEmail(data.invitation.email);
          if (stale) return;
          setUserExists(exists);
        }
      } catch (err) {
        if (stale) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        ErrorLogger.logClientError(err, "useInvitationState:loadInvitation", undefined, `/teams/invite/${token}`);
        setError(err instanceof Error ? err.message : "Failed to load invitation");
      } finally {
        if (!stale) setLoading(false);
      }
    }

    loadInvitation();
    return () => { stale = true; abortController.abort(); };
  }, [token, currentUserEmail]);

  async function handleAcceptInvitation(mode: "signup" | "signin") {
    if (!invitation) return;
    if (!acceptedTerms) {
      setError(ERROR_MESSAGES.TERMS_REQUIRED);
      return;
    }
    const callingToken = token;
    setIsSubmitting(true);
    setError(null);
    setAuthMode(mode);

    try {
      // Sign out first if logged in as a different user
      if (emailMismatch && currentUserEmail) {
        const supabase = createSupabaseBrowserClient();
        const { error: signOutError } = await supabase.auth.signOut();
        if (signOutError) {
          ErrorLogger.logClientError(signOutError, "useInvitationState:handleAcceptInvitation:signOut", undefined, `/teams/invite/${callingToken}`);
          setError("Could not sign out of the current account. Please try again.");
          return;
        }
        expectedSessionEmailRef.current = null;
        setSessionEmail(null);
        setSessionMismatch(false);
      }

      const result = mode === "signup"
        ? await signUp({
            email: invitation.email,
            invitationToken: callingToken,
            acceptedTerms,
          })
        : await signInWithOtp({
            email: invitation.email,
            invitationToken: callingToken,
            acceptedTerms,
          });

      if (callingToken !== tokenRef.current) return;

      if (result.error) {
        setError("message" in result && result.message ? result.message : result.error);
      } else if (result.success) {
        setStep("verify");
        toast.success("Verification code sent to your email!");
      }
    } catch (err) {
      if (callingToken !== tokenRef.current) return;
      ErrorLogger.logClientError(err, "useInvitationState:handleAcceptInvitation", undefined, `/teams/invite/${callingToken}`);
      setError("Could not send verification code. Please check your connection and try again.");
    } finally {
      if (callingToken === tokenRef.current) setIsSubmitting(false);
    }
  }

  async function handleVerifyOtp() {
    if (!invitation || otpValue.length !== 6) return;
    const callingToken = token;
    setIsSubmitting(true);
    setError(null);
    let redirecting = false;

    try {
      const result = await verifyOtp({
        email: invitation.email,
        token: otpValue,
      });

      if (callingToken !== tokenRef.current) return;

      if (result?.error) {
        if (result.redirectPath) {
          redirecting = true;
          window.location.href = result.redirectPath;
          return;
        }
        setError(result.error);
      } else if (result?.success && result?.redirectTo) {
        setStep("success");
        toast.success("Successfully joined the team!");
        redirecting = true;
        window.location.href = result.redirectTo;
      }
    } catch (err) {
      if (callingToken !== tokenRef.current) return;
      ErrorLogger.logClientError(err, "useInvitationState:handleVerifyOtp", undefined, `/teams/invite/${callingToken}`);
      setError("Verification failed. Please check your code or request a new one.");
    } finally {
      if (callingToken === tokenRef.current && !redirecting) setIsSubmitting(false);
    }
  }

  async function handleDirectAccept() {
    if (!invitation) return;
    if (!acceptedTerms) {
      setError(ERROR_MESSAGES.TERMS_REQUIRED);
      return;
    }
    const acceptingToken = token;
    setIsSubmitting(true);
    setError(null);
    let redirecting = false;

    try {
      const result = await acceptInvitationDirectly(acceptingToken, acceptedTerms);

      // If the token changed while the request was in flight (user navigated
      // to a different invite), discard this result to avoid hijacking the UI.
      if (acceptingToken !== tokenRef.current) return;

      if (!result.success) {
        // Permanent errors: disable the direct-accept button.
        // Transient errors (ACCEPTANCE_FAILED, UNEXPECTED_ERROR): keep it enabled for retry.
        const retriable = result.error === "UNEXPECTED_ERROR" || result.error === "ACCEPTANCE_FAILED" || result.error === "TERMS_RECORDING_FAILED";
        if (!retriable) {
          setCanDirectAccept(false);
        }
        if (result.error === "EMAIL_MISMATCH") {
          setSessionMismatch(true);
        }
        // For expired/invalid invitations, clear the invitation data so
        // the error screen shows instead of falling back to the OTP flow.
        if (result.error === "INVITATION_EXPIRED" || result.error === "INVALID_TOKEN") {
          setInvitation(null);
        }
        setError(ERROR_MESSAGES[result.error]);
        return;
      }

      setStep("success");
      toast.success("Successfully joined the team!");
      redirecting = true;
      window.location.href = result.redirectTo;
    } catch (err) {
      if (acceptingToken !== tokenRef.current) return;
      ErrorLogger.logClientError(err, "useInvitationState:handleDirectAccept", undefined, `/teams/invite/${acceptingToken}`);
      setError("Something went wrong. Please try again or contact support.");
    } finally {
      if (acceptingToken === tokenRef.current && !redirecting) setIsSubmitting(false);
    }
  }

  async function handleSignOutAndStay() {
    const supabase = createSupabaseBrowserClient();
    const { error: signOutError } = await supabase.auth.signOut();
    if (signOutError) {
      ErrorLogger.logClientError(signOutError, "useInvitationState:handleSignOutAndStay", undefined, `/teams/invite/${tokenRef.current}`);
      setError("Could not sign out right now. Please try again.");
      return;
    }
    expectedSessionEmailRef.current = null;
    setSessionEmail(null);
    window.location.reload();
  }

  function goBackToView() {
    setStep("view");
  }

  return {
    invitation,
    loading,
    error,
    step,
    otpValue,
    setOtpValue,
    isSubmitting,
    userExists,
    authMode,
    canDirectAccept,
    emailMismatch,
    currentUserEmail: sessionEmail,
    acceptedTerms,
    setAcceptedTerms,
    handleAcceptInvitation,
    handleVerifyOtp,
    handleDirectAccept,
    handleSignOutAndStay,
    goBackToView,
  };
}
