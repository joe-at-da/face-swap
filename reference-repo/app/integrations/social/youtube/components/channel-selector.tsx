"use client";

import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Loader2, Check, Youtube } from "lucide-react";

interface YouTubeChannel {
  id: string;
  name: string;
  username?: string;
  picture?: string;
  subscriberCount?: string;
}

interface ChannelSelectorProps {
  channels: YouTubeChannel[];
  selectedChannel: string | null;
  onSelect: (channelId: string) => void;
  onSubmit: () => void;
  submitting: boolean;
}

function formatSubscriberCount(count?: string): string {
  if (!count) return "";
  const num = parseInt(count, 10);
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M subscribers`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K subscribers`;
  }
  return `${num} subscribers`;
}

export function ChannelSelector({
  channels,
  selectedChannel,
  onSelect,
  onSubmit,
  submitting,
}: ChannelSelectorProps) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <div className="mx-auto w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
          <Youtube className="w-6 h-6 text-red-600" />
        </div>
        <h2 className="text-xl font-semibold">Select a YouTube Channel</h2>
        <p className="text-muted-foreground text-sm">
          Choose which channel you want to post videos to
        </p>
      </div>

      <RadioGroup value={selectedChannel || ""} onValueChange={onSelect}>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {channels.map((channel) => (
            <div
              key={channel.id}
              className={`flex items-center space-x-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                selectedChannel === channel.id
                  ? "border-red-500 bg-red-50"
                  : "border-border hover:bg-muted/50"
              }`}
              onClick={() => onSelect(channel.id)}
            >
              <RadioGroupItem value={channel.id} id={channel.id} />
              <Avatar className="h-10 w-10">
                <AvatarImage src={channel.picture} alt={channel.name} />
                <AvatarFallback className="bg-red-100 text-red-600">
                  {channel.name.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <Label htmlFor={channel.id} className="font-medium cursor-pointer">
                  {channel.name}
                </Label>
                <div className="flex items-center gap-2">
                  {channel.username && (
                    <p className="text-xs text-muted-foreground truncate">
                      {channel.username}
                    </p>
                  )}
                  {channel.subscriberCount && (
                    <p className="text-xs text-muted-foreground">
                      · {formatSubscriberCount(channel.subscriberCount)}
                    </p>
                  )}
                </div>
              </div>
              {selectedChannel === channel.id && (
                <Check className="h-5 w-5 text-red-500 flex-shrink-0" />
              )}
            </div>
          ))}
        </div>
      </RadioGroup>

      <Button
        onClick={onSubmit}
        disabled={!selectedChannel || submitting}
        className="w-full bg-red-600 hover:bg-red-700"
        size="lg"
      >
        {submitting ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Connecting...
          </>
        ) : (
          "Connect to This Channel"
        )}
      </Button>
    </div>
  );
}
