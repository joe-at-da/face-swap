"use client";

import { useCallback, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, Pencil, Copy, Check } from "lucide-react";
import { EditDescriptionDialog } from "./edit-description-dialog";
import { EditTranscriptDialog } from "@/components/edit-transcript-dialog";
import { toast } from "sonner";
import { getDisplayTranscript } from "@/lib/fixTranscriptCapitalization";

interface ClipTranscriptProps {
  transcript: string | null;
  transcriptManuallyEdited: boolean;
  description: string | null;
  clipId: string;
  canEdit: boolean;
  onDescriptionUpdate?: (newDescription: string | null) => void;
  onTranscriptUpdate?: (newTranscript: string | null) => void;
}

export function ClipTranscript({
  transcript,
  transcriptManuallyEdited,
  description,
  clipId,
  canEdit,
  onDescriptionUpdate,
  onTranscriptUpdate,
}: ClipTranscriptProps) {
  const [localManuallyEdited, setLocalManuallyEdited] = useState(transcriptManuallyEdited);
  const displayTranscript = useMemo(
    () => getDisplayTranscript(transcript, localManuallyEdited),
    [transcript, localManuallyEdited]
  );
  const [showFullTranscript, setShowFullTranscript] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("description");
  const [isEditDescriptionDialogOpen, setIsEditDescriptionDialogOpen] =
    useState(false);
  const [isEditTranscriptDialogOpen, setIsEditTranscriptDialogOpen] =
    useState(false);
  const [copiedContent, setCopiedContent] = useState(false);

  const handleSaveTranscript = useCallback(
    async (trimmedTranscript: string) => {
      const response = await fetch(`/api/user-clips/${clipId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: trimmedTranscript || null }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to update transcript");
      }
      setLocalManuallyEdited(true);
      onTranscriptUpdate?.(trimmedTranscript || null);
    },
    [clipId, onTranscriptUpdate]
  );

  const handleCopyContent = async () => {
    const content = activeTab === "description" ? description : displayTranscript;
    const contentType =
      activeTab === "description" ? "Description" : "Transcript";

    if (!content) {
      toast.error(`No ${contentType.toLowerCase()} to copy`);
      return;
    }

    try {
      await navigator.clipboard.writeText(content);
      toast.success(`${contentType} copied to clipboard!`);
      setCopiedContent(true);
      setTimeout(() => setCopiedContent(false), 2000);
    } catch {
      toast.error(`Failed to copy ${contentType.toLowerCase()}`);
    }
  };

  // If neither exists, return null
  if (!transcript && !description) {
    return null;
  }

  // If only transcript exists, show transcript without tabs (current behavior)
  if (!description && transcript) {
    return (
      <>
        <Card>
          <CardContent>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <div className="bg-slate-200 rounded p-1">
                  <FileText className="h-5 w-5" />
                </div>
                Transcript Preview
              </h3>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={async () => {
                    if (!transcript) {
                      toast.error("No transcript to copy");
                      return;
                    }
                    try {
                      await navigator.clipboard.writeText(displayTranscript || transcript);
                      toast.success("Transcript copied to clipboard!");
                      setCopiedContent(true);
                      setTimeout(() => setCopiedContent(false), 2000);
                    } catch {
                      toast.error("Failed to copy transcript");
                    }
                  }}
                  title="Copy transcript"
                >
                  {copiedContent ? (
                    <Check className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
                {canEdit && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => setIsEditTranscriptDialogOpen(true)}
                    title="Edit transcript"
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
            <div className="rounded-lg">
              <p className="text-lg font-sans leading-relaxed">
                {showFullTranscript || transcript.length <= 300
                  ? displayTranscript
                  : `${displayTranscript.substring(0, 300)}...`}
              </p>
              {transcript.length > 300 && (
                <Button
                  variant="link"
                  className="p-0 h-auto text-xs mt-2 w-full justify-center text-muted-foreground"
                  onClick={() => setShowFullTranscript(!showFullTranscript)}
                >
                  {showFullTranscript ? "Show less" : "Show more"}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
        {canEdit && (
          <>
            <EditTranscriptDialog
              open={isEditTranscriptDialogOpen}
              onOpenChange={setIsEditTranscriptDialogOpen}
              currentTranscript={transcript}
              transcriptManuallyEdited={localManuallyEdited}
              onSave={handleSaveTranscript}
            />
          </>
        )}
      </>
    );
  }

  // Determine title based on active tab
  const title =
    activeTab === "description" ? "Description" : "Transcript Preview";

  // Both exist - show tabs with description as default
  return (
    <>
      <Card>
        <CardContent>
          <Tabs
            defaultValue="description"
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            <TabsList className="grid w-full grid-cols-2 mb-4 bg-slate-200">
              <TabsTrigger
                value="description"
                className="text-sm font-normal font-sans"
              >
                Description
              </TabsTrigger>
              <TabsTrigger
                value="transcript"
                className="text-sm font-normal font-sans"
              >
                Transcript
              </TabsTrigger>
            </TabsList>

            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <div className="bg-slate-200 rounded p-1">
                  <FileText className="h-5 w-5" />
                </div>
                {title}
              </h3>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={handleCopyContent}
                  title={`Copy ${
                    activeTab === "description" ? "description" : "transcript"
                  }`}
                >
                  {copiedContent ? (
                    <Check className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
                {canEdit && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => {
                      if (activeTab === "description") {
                        setIsEditDescriptionDialogOpen(true);
                      } else {
                        setIsEditTranscriptDialogOpen(true);
                      }
                    }}
                    title={`Edit ${
                      activeTab === "description" ? "description" : "transcript"
                    }`}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>

            <TabsContent value="description" className="mt-0">
              <div className="rounded-lg">
                <p className="text-lg font-sans leading-relaxed">
                  {description}
                </p>
              </div>
            </TabsContent>

            <TabsContent value="transcript" className="mt-0">
              <div className="rounded-lg">
                <p className="text-lg font-sans leading-relaxed">
                  {showFullTranscript || !transcript || transcript.length <= 300
                    ? displayTranscript
                    : `${displayTranscript.substring(0, 300)}...`}
                </p>
                {transcript && transcript.length > 300 && (
                  <Button
                    variant="link"
                    className="p-0 h-auto text-base font-sans font-normal mt-2 w-full justify-center text-muted-foreground"
                    onClick={() => setShowFullTranscript(!showFullTranscript)}
                  >
                    {showFullTranscript ? "Show less" : "Show more"}
                  </Button>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      {canEdit && (
        <>
          <EditDescriptionDialog
            open={isEditDescriptionDialogOpen}
            onOpenChange={setIsEditDescriptionDialogOpen}
            clipId={clipId}
            currentDescription={description}
            onUpdate={(newDescription) => {
              if (onDescriptionUpdate) {
                onDescriptionUpdate(newDescription);
              }
            }}
          />
          <EditTranscriptDialog
            open={isEditTranscriptDialogOpen}
            onOpenChange={setIsEditTranscriptDialogOpen}
            currentTranscript={transcript}
            transcriptManuallyEdited={localManuallyEdited}
            onSave={handleSaveTranscript}
          />
        </>
      )}
    </>
  );
}
