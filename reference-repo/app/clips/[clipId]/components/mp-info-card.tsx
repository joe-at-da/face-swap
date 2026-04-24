"use client";

import { SmartAvatar } from "@/components/smart-avatar";

interface MpInfoCardProps {
  mpName: string;
  constituency: string | null;
  profileImage?: string | null;
  isMP?: boolean;
}

export function MpInfoCard({
  mpName,
  constituency,
  profileImage,
  isMP = true,
}: MpInfoCardProps) {
  // Extract first and last name for SmartAvatar
  const nameParts = mpName.split(" ");
  const firstName = nameParts[0] || "";
  const lastName = nameParts[nameParts.length - 1] || "";

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      {/* MP Photo */}
      <div className="aspect-square w-full bg-muted flex items-center justify-center overflow-hidden">
        <SmartAvatar
          profileImage={profileImage}
          firstName={firstName}
          lastName={lastName}
          email="" // Not needed for display
          isMP={isMP}
          className="w-full h-full rounded-none"
          enableLazyLoading={false}
        />
      </div>

      {/* MP Info */}
      <div className="p-4 space-y-1">
        <h3 className="font-semibold text-base">{mpName}</h3>
        {constituency && (
          <p className="text-sm text-muted-foreground">{constituency}</p>
        )}
      </div>
    </div>
  );
}
