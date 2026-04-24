"use client";

import { Check, User, Share2, Users } from "lucide-react";
import { cn } from "@/lib/utils";

interface SetupProgressProps {
  currentStep: number;
  totalSteps: number;
}

export function SetupProgress({ currentStep, totalSteps }: SetupProgressProps) {
  const steps = [
    {
      step: 1,
      title: "Profile",
      description: "Basic information",
      icon: User,
    },
    {
      step: 2,
      title: "Social Media",
      description: "Connect accounts",
      icon: Share2,
    },
    {
      step: 3,
      title: "Follow MPs",
      description: "Choose to follow",
      icon: Users,
    },
  ];

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-6">
      <div className="flex items-center justify-center">
        {steps.map((stepData, index) => {
          const isActive = currentStep === stepData.step;
          const isCompleted = currentStep > stepData.step;
          const isLast = index === steps.length - 1;
          const IconComponent = stepData.icon;

          return (
            <div key={stepData.step} className="flex items-center">
              {/* Step Circle */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all",
                    isCompleted
                      ? "bg-primary border-primary text-primary-foreground"
                      : isActive
                      ? "bg-primary border-primary text-primary-foreground"
                      : "bg-background border-border text-muted-foreground"
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-5 w-5" />
                  ) : (
                    <IconComponent className="h-5 w-5" />
                  )}
                </div>
                
                {/* Step Labels */}
                <div className="mt-2 text-center">
                  <p
                    className={cn(
                      "text-sm font-medium",
                      isActive || isCompleted
                        ? "text-foreground"
                        : "text-muted-foreground"
                    )}
                  >
                    {stepData.title}
                  </p>
                  <p className="text-xs text-muted-foreground hidden sm:block">
                    {stepData.description}
                  </p>
                </div>
              </div>

              {/* Connector Line */}
              {!isLast && (
                <div
                  className={cn(
                    "flex-1 h-0.5 mx-4 transition-all",
                    "w-12 sm:w-20 md:w-32",
                    isCompleted
                      ? "bg-primary"
                      : "bg-border"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
      
      {/* Progress Bar */}
      <div className="mt-6">
        <div className="flex justify-between text-sm text-muted-foreground mb-2">
          <span>Step {currentStep} of {totalSteps}</span>
          <span>{Math.round((currentStep / totalSteps) * 100)}% complete</span>
        </div>
        <div className="w-full bg-border rounded-full h-2">
          <div
            className="bg-primary h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${(currentStep / totalSteps) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}