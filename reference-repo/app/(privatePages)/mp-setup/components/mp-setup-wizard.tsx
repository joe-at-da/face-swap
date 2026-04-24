"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useStep } from "@/hooks/use-step";
import { SetupProgress } from "../../setup/components/setup-progress";
import { MpProfileSetupStep } from "./mp-profile-setup-step";
import { MpSocialMediaStep } from "./mp-social-media-step";
import { MpSummaryStep } from "./mp-summary-step";
import { SetupStep1Data } from "@/schemas/authSchema";
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

interface MpSetupWizardProps {
  initialUserData?: {
    firstName: string;
    lastName: string;
    profileImage: string | null;
  };
  mpRecord?: MP | null;
}

interface MpSetupData {
  profile?: SetupStep1Data;
  mpRecord?: MP | null;
}

export function MpSetupWizard({ initialUserData, mpRecord }: MpSetupWizardProps) {
  const router = useRouter();
  const [currentStep, stepActions] = useStep(3);
  const [setupData, setSetupData] = useState<MpSetupData>({ 
    profile: initialUserData,
    mpRecord 
  });
  const [isLoading, setIsLoading] = useState(false);

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

      setSetupData(prev => ({ ...prev, profile: data }));
      stepActions.goToNextStep();
      toast.success("Profile information saved!");
    } catch (error) {
      toast.error(handleError(error, {
        component: 'MpSetupWizard',
        action: 'profile-submit',
        route: '/mp-setup',
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialMediaNext = () => {
    stepActions.goToNextStep();
  };

  const handleFinalSubmit = async () => {
    setIsLoading(true);
    try {
      // For MPs, we automatically follow themselves if we found their record
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

      toast.success("MP setup completed successfully!");

      // Redirect to dashboard
      router.push("/dashboard");
      router.refresh();
    } catch (error) {
      toast.error(handleError(error, {
        component: 'MpSetupWizard',
        action: 'final-submit',
        route: '/mp-setup',
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <MpProfileSetupStep
            onNext={handleProfileSubmit}
            initialData={setupData.profile}
            isLoading={isLoading}
            mpRecord={setupData.mpRecord}
          />
        );
      case 2:
        return (
          <MpSocialMediaStep
            onNext={handleSocialMediaNext}
            onPrevious={stepActions.goToPrevStep}
            isLoading={isLoading}
          />
        );
      case 3:
        return (
          <MpSummaryStep
            onNext={handleFinalSubmit}
            onPrevious={stepActions.goToPrevStep}
            isLoading={isLoading}
            setupData={setupData}
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