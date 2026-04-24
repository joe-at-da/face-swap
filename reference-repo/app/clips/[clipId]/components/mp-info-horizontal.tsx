"use client";

import { SmartAvatar } from "@/components/smart-avatar";

interface MpInfoHorizontalProps {
  mpName: string;
  constituency: string | null;
  profileImage?: string | null;
  isMP?: boolean;
}

export function MpInfoHorizontal({
  mpName,
  constituency,
  profileImage,
  isMP = true,
}: MpInfoHorizontalProps) {
  // Extract first and last name for SmartAvatar
  const nameParts = mpName.split(" ");
  const firstName = nameParts[0] || "";
  const lastName = nameParts[nameParts.length - 1] || "";

  return (
    <div className="flex items-center gap-3 min-w-0 lg:hidden">
      {/* Avatar */}
      <div className="flex-shrink-0">
        <SmartAvatar
          profileImage={profileImage}
          firstName={firstName}
          lastName={lastName}
          email=""
          isMP={isMP}
          className="w-10 h-10"
          enableLazyLoading={false}
        />
      </div>

      {/* MP Info */}
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-sm truncate">{mpName}</h3>
        {constituency && (
          <p className="text-xs text-muted-foreground truncate">{constituency}</p>
        )}
      </div>
    </div>
  );
}

