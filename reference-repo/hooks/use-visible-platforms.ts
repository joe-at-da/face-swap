"use client";

import { useState, useEffect } from "react";
import { getPlatformsWithUI, type PlatformWithUI } from "@/lib/platformHelpers";
import { getRestrictedPlatformsAction } from "@/app/actions/postizActions";
import { FACEBOOK_ENABLED_FOR_ALL } from "@/lib/facebookAllowlist";

export function useVisiblePlatforms(): PlatformWithUI[] {
  const allPlatforms = getPlatformsWithUI();
  const [restrictedPlatforms, setRestrictedPlatforms] = useState<string[]>(
    FACEBOOK_ENABLED_FOR_ALL ? [] : ["facebook"]
  );

  useEffect(() => {
    if (FACEBOOK_ENABLED_FOR_ALL) return;
    getRestrictedPlatformsAction()
      .then((result) => {
        if (result.error) {
          console.error("Failed to get restricted platforms:", result.error);
          // Fail-closed: keep default restrictive state (Facebook hidden)
          return;
        }
        setRestrictedPlatforms(result.data);
      })
      .catch((error) => {
        console.error("Failed to get restricted platforms:", error);
        // Fail-closed: keep default restrictive state (Facebook hidden)
      });
  }, []);

  return allPlatforms.map((p) =>
    restrictedPlatforms.includes(p.identifier)
      ? { ...p, comingSoon: true }
      : p
  );
}
