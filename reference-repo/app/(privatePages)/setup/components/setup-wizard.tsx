"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { usePostHog } from "posthog-js/react";
import { useStep } from "@/hooks/use-step";
import { SetupProgress } from "./setup-progress";
import { ProfileSetupStep } from "./profile-setup-step";
import { SocialMediaStep } from "./social-media-step";
import { MpSelectionStep } from "./mp-selection-step";
import { SetupStep1Data, SetupStep3Data } from "@/schemas/authSchema";
import { handleError } from "@/lib/getErrorMessage";
import { toast } from "sonner";

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

interface SetupWizardProps {
  initialMps: MP[];
  initialUserData?: {
    firstName: string;
    lastName: string;
    profileImage: string | null;
  };
  initialMpSelection?: {
    selectedMpId: number;
  } | null;
}

interface SetupData {
  profile?: SetupStep1Data;
  mp?: SetupStep3Data;
  initialMps?: MP[];
}

export function SetupWizard({ initialMps, initialUserData, initialMpSelection }: SetupWizardProps) {
  const router = useRouter();
  const posthog = usePostHog();
  const [currentStep, stepActions] = useStep(3);
  const [setupData, setSetupData] = useState<SetupData>({
    initialMps,
    profile: initialUserData,
    mp: initialMpSelection || undefined
  });
  const [isLoading, setIsLoading] = useState(false);
  const setupStartTime = useRef<number>(Date.now());
  const lastTrackedStep = useRef<number>(0);

  // Track setup started and step changes
  useEffect(() => {
    // Track setup started only once on mount
    if (lastTrackedStep.current === 0) {
      posthog.capture("setup_started", {
        step: 1,
        has_initial_data: !!initialUserData,
      });
    }

    // Track step viewed when step changes
    if (currentStep !== lastTrackedStep.current) {
      const stepNames = ["", "profile", "social_media", "mp_selection"];
      posthog.capture("setup_step_viewed", {
        step: currentStep,
        step_name: stepNames[currentStep],
      });
      lastTrackedStep.current = currentStep;
    }
  }, [currentStep, posthog, initialUserData]);

  const handleProfileSubmit = async (data: SetupStep1Data) => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/setup/profile", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to save profile");
      }

      // Track profile completion
      posthog.capture("setup_profile_completed", {
        has_profile_image: !!data.profileImage,
        has_first_name: !!data.firstName,
        has_last_name: !!data.lastName,
      });

      setSetupData(prev => ({ ...prev, profile: data }));
      stepActions.goToNextStep();
      toast.success("Profile information saved!");
    } catch (error) {
      // Track profile submission failure
      posthog.capture("setup_profile_failed", {
        error_message: error instanceof Error ? error.message : "Unknown error",
      });
      toast.error(handleError(error, {
        component: 'SetupWizard',
        action: 'profile-submit',
        route: '/setup',
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialMediaNext = () => {
    // Track social media step skipped (currently "coming soon")
    posthog.capture("setup_social_media_skipped", {
      step: 2,
    });
    stepActions.goToNextStep();
  };

  const handleMpSubmit = async (data: SetupStep3Data) => {
    setIsLoading(true);
    try {
      // Save MP selection (required)
      if (data.selectedMpId) {
        const mpResponse = await fetch("/api/setup/mp-follow", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        });

        if (!mpResponse.ok) {
          const error = await mpResponse.json();
          throw new Error(error.error || "Failed to save MP selection");
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

      // Track setup completion
      const totalDurationSeconds = Math.round((Date.now() - setupStartTime.current) / 1000);
      posthog.capture("setup_completed", {
        total_duration_seconds: totalDurationSeconds,
        selected_mp_id: data.selectedMpId,
        has_profile_image: !!setupData.profile?.profileImage,
      });

      setSetupData(prev => ({ ...prev, mp: data }));
      toast.success("Setup completed successfully!");

      // Redirect to dashboard
      router.push("/dashboard");
      router.refresh();
    } catch (error) {
      // Track setup completion failure
      posthog.capture("setup_failed", {
        step: 3,
        error_message: error instanceof Error ? error.message : "Unknown error",
      });
      toast.error(handleError(error, {
        component: 'SetupWizard',
        action: 'mp-submit',
        route: '/setup',
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <ProfileSetupStep
            onNext={handleProfileSubmit}
            initialData={setupData.profile}
            isLoading={isLoading}
          />
        );
      case 2:
        return (
          <SocialMediaStep
            onNext={handleSocialMediaNext}
            onPrevious={stepActions.goToPrevStep}
            isLoading={isLoading}
          />
        );
      case 3:
        return (
          <MpSelectionStep
            onNext={handleMpSubmit}
            onPrevious={stepActions.goToPrevStep}
            initialData={setupData.mp}
            isLoading={isLoading}
            initialMps={setupData.initialMps || []}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <SetupProgress currentStep={currentStep} totalSteps={3} />
      <div className="flex justify-center">
        {renderCurrentStep()}
      </div>
    </div>
  );
}