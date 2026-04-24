"use client";

import { useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AnalyticsChannelSummary } from "@/services/postiz/analytics/types";
import {
  ANALYTICS_PLATFORM_COLORS,
  ANALYTICS_PLATFORM_ICONS,
  getPlatformLabel,
} from "./platform-utils";

const ALL_CHANNELS_VALUE = "__all__";

type ChannelPickerProps = {
  channels: AnalyticsChannelSummary[];
  selectedIntegrationId?: string;
};

export function ChannelPicker({
  channels,
  selectedIntegrationId,
}: ChannelPickerProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const handleChange = (nextValue: string) => {
    const params = new URLSearchParams(searchParams.toString());

    if (nextValue === ALL_CHANNELS_VALUE) {
      params.delete("integrationId");
    } else {
      params.set("integrationId", nextValue);
    }

    startTransition(() => {
      router.replace(`${pathname}?${params.toString()}`);
    });
  };

  return (
    <Select
      value={selectedIntegrationId ?? ALL_CHANNELS_VALUE}
      onValueChange={handleChange}
      disabled={isPending}
    >
      <SelectTrigger className={`w-full min-w-[260px] ${isPending ? "opacity-60" : ""}`}>
        <SelectValue placeholder="Choose a channel" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ALL_CHANNELS_VALUE}>All Channels</SelectItem>
        {channels.map((channel) => {
          const Icon = ANALYTICS_PLATFORM_ICONS[channel.platform];
          const color = ANALYTICS_PLATFORM_COLORS[channel.platform];
          return (
            <SelectItem key={channel.integrationId} value={channel.integrationId}>
              <span className="flex items-center gap-2">
                <Icon className={`h-4 w-4 ${color}`} />
                {channel.label} · {getPlatformLabel(channel.platform)}
              </span>
            </SelectItem>
          );
        })}
      </SelectContent>
    </Select>
  );
}
