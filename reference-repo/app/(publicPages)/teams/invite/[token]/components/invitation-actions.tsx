"use client";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Loader2, ArrowLeft, LogOut } from "lucide-react";
import Link from "next/link";
import type { InvitationData } from "../types";

interface InvitationActionsProps {
  invitation: InvitationData;
  canDirectAccept: boolean;
  emailMismatch: boolean;
  currentUserEmail: string | null;
  userExists: boolean | null;
  isSubmitting: boolean;
  acceptedTerms: boolean;
  onDirectAccept: () => void;
  onAcceptInvitation: (mode: "signup" | "signin") => void;
  onAcceptedTermsChange: (checked: boolean) => void;
  onSignOut: () => void;
}

export function InvitationActions({
  invitation,
  canDirectAccept,
  emailMismatch,
  currentUserEmail,
  userExists,
  isSubmitting,
  acceptedTerms,
  onDirectAccept,
  onAcceptInvitation,
  onAcceptedTermsChange,
  onSignOut,
}: InvitationActionsProps) {
  const mismatchNotice = currentUserEmail
    ? (
      <>
        You&apos;re signed in as <strong>{currentUserEmail}</strong>, but this invitation was sent to{" "}
        <strong>{invitation.email}</strong>. Sign out and continue with the invited email to accept
        this invitation.
      </>
    )
    : null;

  return (
    <>
      {/* Email Mismatch Notice */}
      {emailMismatch && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span>{mismatchNotice}</span>
            <Button variant="ghost" onClick={onSignOut} className="shrink-0 h-11">
              <LogOut className="mr-1 h-3 w-3" />
              Sign out
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col items-center gap-4">
        <div className="w-full rounded-md border border-border/60 p-4">
          <label className="flex items-start gap-3 text-sm leading-relaxed cursor-pointer">
            <Checkbox
              checked={acceptedTerms}
              disabled={isSubmitting}
              onCheckedChange={(checked) => onAcceptedTermsChange(checked === true)}
              className="mt-0.5"
            />
            <span className="font-normal">
              I agree to the{" "}
              <Link
                href="/terms-and-conditions"
                target="_blank"
                rel="noreferrer"
                className="font-medium underline underline-offset-4 hover:text-primary"
              >
                Terms & Conditions
              </Link>
            </span>
          </label>
        </div>

        {canDirectAccept ? (
          <>
            <Button
              onClick={onDirectAccept}
              disabled={isSubmitting || !acceptedTerms}
              className="w-full"
              size="lg"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 motion-safe:animate-spin" />
                  Joining team...
                </>
              ) : (
                "Accept Invitation"
              )}
            </Button>
            <p className="text-xs text-muted-foreground text-center">
              You&apos;re signed in as <strong>{currentUserEmail}</strong>. Click to accept and join
              the team.
            </p>
          </>
        ) : userExists === null ? (
          <div className="w-full flex justify-center py-2">
            <Loader2 className="h-6 w-6 motion-safe:animate-spin text-primary" />
          </div>
        ) : userExists ? (
          <>
            <Button
              onClick={() => onAcceptInvitation("signin")}
              disabled={isSubmitting || !acceptedTerms}
              className="w-full"
              size="lg"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 motion-safe:animate-spin" />
                  Processing...
                </>
              ) : (
                emailMismatch ? "Sign Out and Accept Invitation" : "Sign In to Accept Invitation"
              )}
            </Button>
            <p className="text-xs text-muted-foreground text-center">
              {emailMismatch ? (
                <>
                  We&apos;ll sign you out of <strong>{currentUserEmail}</strong> and send a
                  verification code to <strong>{invitation.email}</strong>.
                </>
              ) : (
                "An account already exists with this email. Sign in to accept the invitation."
              )}
            </p>
          </>
        ) : (
          <>
            <Button
              onClick={() => onAcceptInvitation("signup")}
              disabled={isSubmitting || !acceptedTerms}
              className="w-full"
              size="lg"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 motion-safe:animate-spin" />
                  Processing...
                </>
              ) : (
                emailMismatch ? "Sign Out and Accept Invitation" : "Accept Invitation & Sign Up"
              )}
            </Button>
            {emailMismatch && (
              <p className="text-xs text-muted-foreground text-center">
                We&apos;ll sign you out of <strong>{currentUserEmail}</strong> so you can continue
                with <strong>{invitation.email}</strong> and finish accepting this invitation.
              </p>
            )}
          </>
        )}

        <p className="text-center text-sm text-muted-foreground">
          <Link href="/" className="inline-flex items-center gap-1 hover:text-foreground transition-colors">
            <ArrowLeft className="h-3 w-3" />
            Back to home
          </Link>
        </p>
      </div>
    </>
  );
}
