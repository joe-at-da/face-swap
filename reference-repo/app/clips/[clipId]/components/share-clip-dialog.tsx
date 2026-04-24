"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";

interface ShareClipDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clipUrl: string;
  clipTitle: string;
}

export function ShareClipDialog({
  open,
  onOpenChange,
  clipUrl,
  clipTitle,
}: ShareClipDialogProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(clipUrl);
      setCopied(true);
      toast.success("Link copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy link");
    }
  };

  const shareToTwitter = () => {
    const url = `https://twitter.com/intent/tweet?url=${encodeURIComponent(
      clipUrl
    )}&text=${encodeURIComponent(clipTitle)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const shareToFacebook = () => {
    const url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(
      clipUrl
    )}&quote=${encodeURIComponent(clipTitle)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const shareToLinkedIn = () => {
    const url = `https://www.linkedin.com/shareArticle?mini=true&url=${encodeURIComponent(
      clipUrl
    )}&title=${encodeURIComponent(clipTitle)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Share This Clip</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-4">
          {/* Social Media Buttons */}
          <div className="grid grid-cols-3 gap-3">
            {/* Twitter/X */}
            <Button
              variant="outline"
              className="flex flex-col h-auto py-4 gap-2 hover:bg-slate-50"
              onClick={shareToTwitter}
            >
              <div className="w-10 h-10 rounded-full bg-black flex items-center justify-center text-white font-bold text-lg">
                𝕏
              </div>
              <span className="text-xs font-medium">Twitter</span>
            </Button>

            {/* Facebook */}
            <Button
              variant="outline"
              className="flex flex-col h-auto py-4 gap-2 hover:bg-blue-50"
              onClick={shareToFacebook}
            >
              <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-lg">
                f
              </div>
              <span className="text-xs font-medium">Facebook</span>
            </Button>

            {/* LinkedIn */}
            <Button
              variant="outline"
              className="flex flex-col h-auto py-4 gap-2 hover:bg-blue-50"
              onClick={shareToLinkedIn}
            >
              <div className="w-10 h-10 rounded-full bg-blue-700 flex items-center justify-center text-white font-bold text-lg">
                in
              </div>
              <span className="text-xs font-medium">LinkedIn</span>
            </Button>
          </div>

          {/* Share Link Section */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">
              Share Link
            </label>
            <div className="flex gap-2">
              <Input
                value={clipUrl}
                readOnly
                className="flex-1 font-mono text-sm"
              />
              <Button
                variant={copied ? "default" : "outline"}
                size="icon"
                onClick={handleCopyLink}
                className="shrink-0"
              >
                {copied ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
