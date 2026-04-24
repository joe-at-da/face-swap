"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SmartAvatar } from "@/components/smart-avatar";
import { 
  CheckCircle2,
  ArrowLeft,
  Crown,
  Building,
  Users,
  Loader2,
  Shield
} from "lucide-react";
import { SetupStep1Data } from "@/schemas/authSchema";

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

interface MpSetupData {
  profile?: SetupStep1Data;
  mpRecord?: MP | null;
}

interface MpSummaryStepProps {
  onNext: () => void;
  onPrevious: () => void;
  isLoading?: boolean;
  setupData: MpSetupData;
}

export function MpSummaryStep({ onNext, onPrevious, isLoading, setupData }: MpSummaryStepProps) {
  const { profile, mpRecord } = setupData;

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="text-center">
        <div className="flex justify-center mb-2">
          <Shield className="h-8 w-8 text-primary" />
        </div>
        <CardTitle className="text-2xl font-semibold">Setup Summary</CardTitle>
        <CardDescription>
          Review your MP profile and complete setup
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Profile Summary */}
        <div className="p-4 border border-primary/20 bg-primary/5 rounded-lg">
          <div className="flex items-center space-x-4 mb-4">
            <SmartAvatar
              profileImage={profile?.profileImage as string}
              mpPortraitUrl={mpRecord?.parliament_member_portraits?.[0]?.image_url}
              firstName={profile?.firstName}
              lastName={profile?.lastName}
              isMP={true}
              className="h-16 w-16"
              enableLazyLoading={false}
            />
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <h3 className="font-semibold text-lg">
                  {profile?.firstName} {profile?.lastName}
                </h3>
                <Badge className="text-xs bg-primary/20 text-primary">
                  MP
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                Parliament Member Account
              </p>
            </div>
            <Crown className="h-6 w-6 text-primary" />
          </div>

          {/* MP Details */}
          {mpRecord && (
            <div className="border-t border-primary/10 pt-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Parliamentary Name:</span>
                <span className="font-medium">{mpRecord.display_name}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Constituency:</span>
                <span className="font-medium">{mpRecord.constituency_name}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Party:</span>
                <div className="flex items-center space-x-2">
                  <Badge variant="outline" className="text-xs">
                    {mpRecord.party_abbreviation}
                  </Badge>
                  {mpRecord.party_name && (
                    <span className="text-xs text-muted-foreground">{mpRecord.party_name}</span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Setup Features */}
        <div className="space-y-3">
          <h4 className="font-medium flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 text-primary" />
            <span>Your MP Setup Includes:</span>
          </h4>
          
          <div className="space-y-3">
            <div className="flex items-start space-x-3 p-3 rounded-lg border border-green-200 bg-green-50 dark:bg-green-950/20 dark:border-green-800/50">
              <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium text-sm text-green-800 dark:text-green-200">
                  Self-Following Enabled
                </p>
                <p className="text-xs text-green-700 dark:text-green-300">
                  You will automatically follow your own parliamentary activity
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3 p-3 rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800/50">
              <Building className="h-5 w-5 text-blue-600 mt-0.5" />
              <div>
                <p className="font-medium text-sm text-blue-800 dark:text-blue-200">
                  MP Exclusive Features
                </p>
                <p className="text-xs text-blue-700 dark:text-blue-300">
                  Priority processing, extended limits, and advanced analytics
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3 p-3 rounded-lg border border-purple-200 bg-purple-50 dark:bg-purple-950/20 dark:border-purple-800/50">
              <Users className="h-5 w-5 text-purple-600 mt-0.5" />
              <div>
                <p className="font-medium text-sm text-purple-800 dark:text-purple-200">
                  Team Management Ready
                </p>
                <p className="text-xs text-purple-700 dark:text-purple-300">
                  Invite staff members and manage permissions from your dashboard
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Social Media Status */}
        <div className="p-4 border border-orange-200 bg-orange-50 dark:bg-orange-950/20 dark:border-orange-800/50 rounded-lg">
          <div className="flex items-center space-x-2 mb-2">
            <Crown className="h-4 w-4 text-orange-600" />
            <span className="text-sm font-medium text-orange-800 dark:text-orange-200">
              Social Media Integration
            </span>
          </div>
          <p className="text-xs text-orange-700 dark:text-orange-300">
            Coming soon - You&apos;ll be able to connect Twitter, Facebook, Instagram, and LinkedIn for automated posting
          </p>
        </div>

        {/* Navigation Buttons */}
        <div className="flex justify-between pt-4">
          <Button 
            type="button" 
            variant="outline" 
            onClick={onPrevious}
            disabled={isLoading}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Previous
          </Button>
          
          <Button 
            type="button"
            onClick={onNext}
            disabled={isLoading}
            className="bg-primary hover:bg-primary/90"
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Complete MP Setup
            <Crown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}