"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { usePostHog } from "posthog-js/react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SmartAvatar } from "@/components/smart-avatar";
import {
  Crown,
  Building,
  CheckCircle2,
  Users,
  Loader2,
  Shield,
} from "lucide-react";
import { handleError } from "@/lib/getErrorMessage";
import { toast } from "sonner";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import { SocialMediaIntegrationStatus } from "./social-media-integration-status";
import { createPostizAccountAction } from "@/app/actions/postizActions";

type MP = {
  member_id: number;
  display_name: string;
  party_abbreviation: string;
  party_name?: string;
  constituency_name: string;
  parliament_member_portraits: Array<{
    image_url: string;
    is_primary: boolean;
  }>;
};

interface MpSetupDisplayProps {
  userData: {
    firstName: string;
    lastName: string;
    profileImage: string | null;
  };
  mpRecord?: MP | null;
}

export function MpSetupDisplay({ userData, mpRecord }: MpSetupDisplayProps) {
  const router = useRouter();
  const posthog = usePostHog();
  const [isLoading, setIsLoading] = useState(false);
  const [postizCreating, setPostizCreating] = useState(false);
  const [postizCreated, setPostizCreated] = useState(false);
  const [postizError, setPostizError] = useState<string | null>(null);
  const setupStartTime = useRef<number>(Date.now());
  const hasTrackedStart = useRef(false);

  // Track MP setup started
  useEffect(() => {
    if (!hasTrackedStart.current) {
      posthog.capture("mp_setup_started", {
        mp_name: mpRecord?.display_name,
        mp_party: mpRecord?.party_abbreviation,
        mp_constituency: mpRecord?.constituency_name,
      });
      hasTrackedStart.current = true;
    }
  }, [posthog, mpRecord]);

  // Auto-create Postiz account on mount
  useEffect(() => {
    const createPostizAccount = async () => {
      setPostizCreating(true);
      setPostizError(null);

      try {
        const response = await createPostizAccountAction();

        if (response.error) {
          // Track Postiz creation failure
          posthog.capture("mp_setup_postiz_failed", {
            error_message: response.error,
          });
          setPostizError(response.error);
          console.error("Postiz creation error:", response.error);
        } else {
          // Track Postiz account creation
          const alreadyExists = "alreadyExists" in response && response.alreadyExists;
          posthog.capture("mp_setup_postiz_created", {
            already_exists: alreadyExists,
          });
          setPostizCreated(true);
          if (alreadyExists) {
            console.log("Postiz account already exists");
          } else {
            console.log("Postiz account created successfully");
          }
        }
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Unknown error";
        // Track Postiz creation exception
        posthog.capture("mp_setup_postiz_failed", {
          error_message: errorMessage,
          error_type: "exception",
        });
        setPostizError(errorMessage);
        console.error("Postiz creation error:", error);
      } finally {
        setPostizCreating(false);
      }
    };

    createPostizAccount();
  }, [posthog]);

  const handleCompleteSetup = async () => {
    setIsLoading(true);
    try {
      // Auto-follow the MP if we found their record
      if (mpRecord) {
        const mpResponse = await fetch("/api/setup/mp-follow", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ selectedMpId: mpRecord.member_id }),
        });

        if (!mpResponse.ok) {
          const error = await mpResponse.json();
          throw new Error(error.error || "Failed to set up MP self-following");
        }
      }

      // Mark setup as complete
      const completeResponse = await fetch("/api/setup/complete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!completeResponse.ok) {
        const error = await completeResponse.json();
        throw new Error(error.error || "Failed to complete setup");
      }

      // Force refresh the Supabase session to get new JWT with updated metadata
      const supabase = createSupabaseBrowserClient();
      const { error: refreshError } = await supabase.auth.refreshSession();

      if (refreshError) {
        console.error("Session refresh error:", refreshError);
        throw new Error("Failed to refresh session after setup completion");
      }

      // Track MP setup completion
      const totalDurationSeconds = Math.round((Date.now() - setupStartTime.current) / 1000);
      posthog.capture("mp_setup_completed", {
        total_duration_seconds: totalDurationSeconds,
        mp_name: mpRecord?.display_name,
        mp_party: mpRecord?.party_abbreviation,
        postiz_created: postizCreated,
      });

      toast.success("MP setup completed successfully!");

      // Redirect to dashboard after session refresh
      router.push("/dashboard");
      router.refresh();
    } catch (error) {
      // Track MP setup failure
      posthog.capture("mp_setup_failed", {
        error_message: error instanceof Error ? error.message : "Unknown error",
      });
      toast.error(
        handleError(error, {
          component: "MpSetupDisplay",
          action: "complete-setup",
          route: "/mp-setup",
        })
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8">
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-2">
            <Shield className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl font-semibold">
            MP Account Setup
          </CardTitle>
          <CardDescription>
            Your parliamentary account is ready to be activated
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* MP Profile Summary */}
          <div className="p-6 border border-primary/20 bg-background rounded-lg">
            <div className="flex items-center space-x-4 mb-6">
              <SmartAvatar
                profileImage={userData?.profileImage as string}
                mpPortraitUrl={
                  mpRecord?.parliament_member_portraits?.[0]?.image_url
                }
                firstName={userData?.firstName}
                lastName={userData?.lastName}
                isMP={true}
                className="h-20 w-20 text-lg"
                enableLazyLoading={false}
              />
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <h3 className="font-semibold text-xl">
                    {userData?.firstName && userData?.lastName
                      ? `${userData.firstName} ${userData.lastName}`
                      : "MP Account"}
                  </h3>
                  <Badge className="bg-primary/20 text-primary border-primary/30">
                    <Crown className="h-3 w-3 mr-1" />
                    Parliament Member
                  </Badge>
                </div>
                <p className="text-muted-foreground">
                  UK Parliament • @parliament.gov.uk
                </p>
              </div>
            </div>

            {/* Parliamentary Information */}
            {mpRecord && (
              <div className="border-t border-border pt-6 space-y-4">
                <div className="flex items-center space-x-2 mb-3">
                  <Building className="h-5 w-5 text-primary" />
                  <span className="font-medium text-primary">
                    Parliamentary Information
                  </span>
                </div>
                <div className="grid gap-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Official Name:
                    </span>
                    <span className="font-medium">{mpRecord.display_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Constituency:</span>
                    <span className="font-medium">
                      {mpRecord.constituency_name}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Party:</span>
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline" className="text-xs">
                        {mpRecord.party_abbreviation}
                      </Badge>
                      {mpRecord.party_name && (
                        <span className="text-xs text-muted-foreground">
                          {mpRecord.party_name}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Setup Features */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="p-4 rounded-lg border border-green-200 bg-green-50 dark:bg-green-950/20 dark:border-green-800/50">
              <div className="flex items-start space-x-3">
                <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <p className="font-medium text-sm text-green-800 dark:text-green-200">
                    Self-Following Enabled
                  </p>
                  <p className="text-xs text-green-700 dark:text-green-300 mt-1">
                    You will automatically follow your own parliamentary
                    activity and receive notifications
                  </p>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800/50">
              <div className="flex items-start space-x-3">
                <Users className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="font-medium text-sm text-blue-800 dark:text-blue-200">
                    MP Exclusive Features
                  </p>
                  <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                    Priority processing, extended limits, advanced analytics,
                    and team management
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Social Media Integration Status */}
          <SocialMediaIntegrationStatus
            postizCreating={postizCreating}
            postizCreated={postizCreated}
            postizError={postizError}
          />

          {/* Complete Setup Button */}
          <div className="pt-4">
            <Button
              onClick={handleCompleteSetup}
              disabled={isLoading}
              className="w-full bg-primary hover:bg-primary/90"
              size="lg"
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Complete MP Setup & Access Dashboard
              <Crown className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
