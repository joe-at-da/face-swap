"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Copy, Check, Code, Link as LinkIcon, ChevronDown } from "lucide-react";
import { getClipEmbedCode } from "@/lib/clipHelpers";
import { toast } from "sonner";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface ClipShareLinksProps {
  clipId: string;
}

export function ClipShareLinks({ clipId }: ClipShareLinksProps) {
  const embedCode = getClipEmbedCode(clipId);

  const [copiedEmbed, setCopiedEmbed] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [isEmbedOpen, setIsEmbedOpen] = useState(false);

  // Generate public video page URL
  const baseUrl =
    process.env.NEXT_PUBLIC_FRONTEND_URL ||
    (typeof window !== "undefined"
      ? window.location.origin
      : "http://localhost:3000");
  const publicUrl = `${baseUrl}/clips/${clipId}`;

  const handleCopyEmbed = () => {
    navigator.clipboard.writeText(embedCode);
    toast.success("Embed code copied to clipboard");
    setCopiedEmbed(true);
    setTimeout(() => setCopiedEmbed(false), 2000);
  };

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(publicUrl);
    toast.success("Video link copied to clipboard");
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Public Video Page Section - Prominent */}
      <Card className="p-4 border-primary/20 bg-primary/5">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="bg-primary/20 rounded p-1.5">
              <LinkIcon className="h-4 w-4 text-primary" />
            </div>
            <span className="text-lg font-sans font-bold">
              Public Video Page
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            Share this link to let others view your clip
          </p>
          <div className="flex items-center gap-2">
            <div className="flex-1 min-w-0 rounded border border-border bg-background px-3 py-2">
              <p className="text-sm font-mono truncate text-muted-foreground">
                {publicUrl}
              </p>
            </div>
            <Button
              type="button"
              variant="default"
              size="sm"
              className="bg-blue-600 hover:bg-blue-700 text-white shrink-0"
              onClick={handleCopyUrl}
            >
              {copiedUrl ? (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-2" />
                  Copy Link
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>

      {/* Embed Code Section - Collapsible */}
      <Collapsible open={isEmbedOpen} onOpenChange={setIsEmbedOpen}>
        <Card className="p-4">
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="w-full flex items-center justify-between hover:opacity-80 transition-opacity"
            >
              <div className="flex items-center gap-2">
                <div className="bg-slate-200 dark:bg-slate-700 rounded p-1">
                  <Code className="h-4 w-4 text-primary" />
                </div>
                <span className="text-lg font-sans font-bold">Embed Code</span>
              </div>
              <ChevronDown
                className={cn(
                  "h-5 w-5 text-muted-foreground transition-transform duration-200",
                  isEmbedOpen && "rotate-180",
                )}
              />
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-3">
            <div className="space-y-3">
              <div className="group relative overflow-hidden rounded border border-border bg-card p-4 hover:border-primary transition-all duration-300">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <pre className="text-sm font-mono break-all whitespace-pre-wrap text-muted-foreground overflow-x-auto">
                      {embedCode}
                    </pre>
                  </div>
                </div>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full"
                onClick={handleCopyEmbed}
              >
                {copiedEmbed ? (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy Embed Code
                  </>
                )}
              </Button>
            </div>
          </CollapsibleContent>
        </Card>
      </Collapsible>
    </div>
  );
}
