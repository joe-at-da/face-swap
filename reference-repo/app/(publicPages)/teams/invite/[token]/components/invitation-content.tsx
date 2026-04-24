"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, Loader2 } from "lucide-react";
import { useInvitationState } from "../hooks/use-invitation-state";
import { InvitationError } from "./invitation-error";
import { InvitationSuccess } from "./invitation-success";
import { InvitationVerify } from "./invitation-verify";
import { InvitationDetails } from "./invitation-details";
import { InvitationActions } from "./invitation-actions";

interface InvitationContentProps {
  token: string;
  currentUserEmail: string | null;
  initialErrorCode?: string | null;
}

export function InvitationContent({
  token,
  currentUserEmail,
  initialErrorCode,
}: InvitationContentProps) {
  const state = useInvitationState(token, currentUserEmail, initialErrorCode);

  if (state.loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 motion-safe:animate-spin text-primary" />
      </div>
    );
  }

  if (state.error && !state.invitation) {
    return <InvitationError message={state.error} />;
  }

  if (!state.invitation) return null;

  if (state.step === "success") {
    return <InvitationSuccess teamName={state.invitation.team.name} />;
  }

  if (state.step === "verify") {
    return (
      <InvitationVerify
        email={state.invitation.email}
        otpValue={state.otpValue}
        onOtpChange={state.setOtpValue}
        onVerify={state.handleVerifyOtp}
        onBack={state.goBackToView}
        isSubmitting={state.isSubmitting}
        isSignIn={state.authMode === "signin"}
        error={state.error}
      />
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-lg space-y-6">
          <div className="text-center space-y-2">
            <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
              Team Invitation
            </h1>
            <p className="text-muted-foreground text-base md:text-lg">
              You&apos;ve been invited to join a team on Parliament Connect
            </p>
          </div>

          <Card className="border-border/50 shadow-lg">
            <CardContent className="p-6 space-y-6">
              {state.error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{state.error}</AlertDescription>
                </Alert>
              )}

              <InvitationDetails invitation={state.invitation} />

              <InvitationActions
                invitation={state.invitation}
                canDirectAccept={state.canDirectAccept}
                emailMismatch={state.emailMismatch}
                currentUserEmail={state.currentUserEmail}
                userExists={state.userExists}
                isSubmitting={state.isSubmitting}
                acceptedTerms={state.acceptedTerms}
                onDirectAccept={state.handleDirectAccept}
                onAcceptInvitation={state.handleAcceptInvitation}
                onAcceptedTermsChange={state.setAcceptedTerms}
                onSignOut={state.handleSignOutAndStay}
              />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Background Gradient */}
      <div className="fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
        <div className="absolute left-[50%] top-0 h-[600px] w-[600px] -translate-x-[50%] rounded-full bg-gradient-to-r from-primary/20 via-primary/10 to-primary/5 blur-[120px]" />
        <div className="absolute right-0 bottom-0 h-[400px] w-[400px] rounded-full bg-gradient-to-br from-primary/10 to-primary/5 blur-[100px]" />
      </div>
    </div>
  );
}
