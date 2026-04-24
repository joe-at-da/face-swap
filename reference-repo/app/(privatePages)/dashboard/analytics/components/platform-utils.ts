import { Facebook, Twitter, Youtube, type LucideIcon } from "lucide-react";
import type { SupportedAnalyticsPlatform } from "@/services/postiz/analytics/types";

export const ANALYTICS_PLATFORM_ICONS: Record<SupportedAnalyticsPlatform, LucideIcon> = {
  x: Twitter,
  facebook: Facebook,
  youtube: Youtube,
};

export const ANALYTICS_PLATFORM_COLORS: Record<SupportedAnalyticsPlatform, string> = {
  x: "text-blue-500",
  facebook: "text-blue-600",
  youtube: "text-red-600",
};

export function getPlatformLabel(platform: SupportedAnalyticsPlatform) {
  if (platform === "x") return "X";
  if (platform === "youtube") return "YouTube";
  return "Facebook";
}
