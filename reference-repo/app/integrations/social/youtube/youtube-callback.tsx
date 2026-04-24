"use client";

import { useEffect, useState, useCallback } from "react";
import { ChannelSelector } from "./components/channel-selector";
import { Button } from "@/components/ui/button";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

interface YouTubeChannel {
  id: string;
  name: string;
  username?: string;
  picture?: string;
  subscriberCount?: string;
}

export default function YouTubeCallback() {
  const [loading, setLoading] = useState(true);
  const [channels, setChannels] = useState<YouTubeChannel[]>([]);
  const [integrationId, setIntegrationId] = useState<string | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const notifyParentAndClose = useCallback((status: string) => {
    if (window.opener) {
      window.opener.postMessage(
        {
          type: "youtube-oauth-complete",
          status,
        },
        window.location.origin
      );
    }
    window.close();
  }, []);

  const handleClose = useCallback(() => {
    notifyParentAndClose("cancelled");
  }, [notifyParentAndClose]);

  // Fetch integration data with retry logic for race condition
  useEffect(() => {
    const fetchWithRetry = async () => {
      const maxAttempts = 5;
      const delayMs = 1500;

      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        console.log(`Fetching YouTube integration (attempt ${attempt}/${maxAttempts})`);

        try {
          const response = await fetch("/api/oauth/youtube/integration");
          const data = await response.json();

          console.log("YouTube integration response:", data);

          // If we got channels, we're done
          if (data.channels && data.channels.length > 0) {
            console.log("Found YouTube channels:", data.channels.length);
            setChannels(data.channels);
            setIntegrationId(data.id);
            // Auto-select if only one channel
            if (data.channels.length === 1) {
              setSelectedChannel(data.channels[0].id);
            }
            setLoading(false);
            return;
          }

          // If already complete (inBetweenSteps=false), close
          if (data.inBetweenSteps === false) {
            console.log("Integration already complete, closing");
            notifyParentAndClose("success");
            return;
          }

          // If it's an error other than "no pending integration", stop retrying
          if (data.error && !data.error.includes("No pending")) {
            console.error("YouTube integration error:", data.error);
            setError(data.error);
            setLoading(false);
            return;
          }

          // Wait before retry (race condition - integration not yet created)
          if (attempt < maxAttempts) {
            console.log(`No integration yet, retrying in ${delayMs}ms...`);
            await new Promise(resolve => setTimeout(resolve, delayMs));
          }
        } catch (err) {
          console.error("Error fetching integration:", err);
          // Only set error on last attempt
          if (attempt === maxAttempts) {
            setError("Failed to load YouTube Channels. Please try again.");
            setLoading(false);
            return;
          }
          // Wait before retry on error
          await new Promise(resolve => setTimeout(resolve, delayMs));
        }
      }

      // All retries exhausted
      console.log("All retry attempts exhausted");
      setError(
        "Could not load YouTube Channels. Please try reconnecting your YouTube account."
      );
      setLoading(false);
    };

    fetchWithRetry();
  }, [notifyParentAndClose]);

  const handleSubmit = async () => {
    if (!selectedChannel || !integrationId) return;

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/oauth/youtube/select-channel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          integrationId,
          channelId: selectedChannel,
        }),
      });

      const result = await response.json();
      if (result.success) {
        setSuccess(true);
        // Brief delay to show success state before closing
        setTimeout(() => {
          notifyParentAndClose("success");
        }, 1000);
      } else {
        setError(result.error || "Failed to select channel. Please try again.");
        setSubmitting(false);
      }
    } catch (err) {
      console.error("Error selecting channel:", err);
      setError("Failed to connect. Please try again.");
      setSubmitting(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-red-600" />
          <p className="text-muted-foreground">Loading YouTube Channels...</p>
        </div>
      </div>
    );
  }

  // Success state
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <CheckCircle2 className="h-12 w-12 mx-auto text-green-500" />
          <h2 className="text-xl font-semibold">Connected!</h2>
          <p className="text-muted-foreground">
            Your YouTube Channel has been connected successfully.
          </p>
        </div>
      </div>
    );
  }

  // Error state (no channels or API error)
  if (error && channels.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-6">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="mx-auto w-12 h-12 bg-destructive/10 rounded-full flex items-center justify-center">
            <AlertCircle className="h-6 w-6 text-destructive" />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-semibold">Connection Issue</h2>
            <p className="text-muted-foreground text-sm">{error}</p>
          </div>
          <div className="space-y-2">
            <Button onClick={() => window.location.reload()} className="w-full bg-red-600 hover:bg-red-700">
              Try Again
            </Button>
            <Button variant="outline" onClick={handleClose} className="w-full">
              Close
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Make sure you have at least one YouTube channel.{" "}
            <a
              href="https://www.youtube.com/create_channel"
              target="_blank"
              rel="noopener noreferrer"
              className="text-red-600 hover:underline"
            >
              Create a Channel
            </a>
          </p>
        </div>
      </div>
    );
  }

  // Channel selection UI
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="max-w-md w-full">
        <ChannelSelector
          channels={channels}
          selectedChannel={selectedChannel}
          onSelect={setSelectedChannel}
          onSubmit={handleSubmit}
          submitting={submitting}
        />

        {error && (
          <p className="mt-4 text-sm text-destructive text-center">{error}</p>
        )}

        <Button
          variant="ghost"
          onClick={handleClose}
          className="w-full mt-4 text-muted-foreground"
        >
          Cancel
        </Button>
      </div>
    </div>
  );
}
