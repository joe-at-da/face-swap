"use client";

import { useState, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Edit, FileText } from "lucide-react";
import { EditDescriptionDialog } from "@/app/(privatePages)/dashboard/create-clips/components/edit-description-dialog";
import { EditTranscriptDialog } from "@/components/edit-transcript-dialog";
import { updateClipTranscript } from "@/app/actions/clip-descriptions";
import { getDisplayTranscript } from "@/lib/fixTranscriptCapitalization";

interface DescriptionTranscriptViewerProps {
  description: string | null;
  transcript: string | null;
  transcriptManuallyEdited?: boolean;
  clipId?: string;
  canEditDescription?: boolean;
  canEditTranscript?: boolean;
  onDescriptionUpdated?: (newDescription: string) => void;
  onTranscriptUpdated?: (newTranscript: string) => void;
}

export function DescriptionTranscriptViewer({
  description,
  transcript,
  transcriptManuallyEdited = false,
  clipId,
  canEditDescription = false,
  canEditTranscript = false,
  onDescriptionUpdated,
  onTranscriptUpdated,
}: DescriptionTranscriptViewerProps) {
  const [isEditDescriptionOpen, setIsEditDescriptionOpen] = useState(false);
  const [isEditTranscriptOpen, setIsEditTranscriptOpen] = useState(false);
  const [localDescription, setLocalDescription] = useState(description);
  const [localTranscript, setLocalTranscript] = useState(transcript);
  const [localManuallyEdited, setLocalManuallyEdited] = useState(transcriptManuallyEdited);

  // Update local state when props change
  useEffect(() => {
    setLocalDescription(description);
    setLocalTranscript(transcript);
    setLocalManuallyEdited(transcriptManuallyEdited);
  }, [description, transcript, transcriptManuallyEdited]);

  const handleDescriptionUpdated = (newDescription: string) => {
    setLocalDescription(newDescription);
    onDescriptionUpdated?.(newDescription);
  };

  const handleTranscriptUpdated = useCallback(
    (newTranscript: string) => {
      setLocalTranscript(newTranscript);
      setLocalManuallyEdited(true);
      onTranscriptUpdated?.(newTranscript);
    },
    [onTranscriptUpdated],
  );

  const handleSaveTranscript = useCallback(
    async (transcript: string) => {
      const result = await updateClipTranscript(clipId!, transcript);
      if (!result.success) {
        throw new Error(result.error || "Failed to update transcript");
      }
      if (result.transcript) {
        handleTranscriptUpdated(result.transcript);
      }
    },
    [clipId, handleTranscriptUpdated],
  );
  // Only render if at least one exists
  if (!localDescription && !localTranscript) {
    return null;
  }

  // If only one exists, show it without tabs
  const onlyDescription = localDescription && !localTranscript;
  const onlyTranscript = localTranscript && !localDescription;

  if (onlyDescription) {
    return (
      <>
        <Card className="p-8">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Description</h2>
              {clipId && canEditDescription && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsEditDescriptionOpen(true)}
                >
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </Button>
              )}
            </div>
            <p className="text-base text-muted-foreground whitespace-pre-wrap leading-loose">
              {localDescription}
            </p>
          </div>
        </Card>
        {clipId && canEditDescription && (
          <EditDescriptionDialog
            open={isEditDescriptionOpen}
            onOpenChange={setIsEditDescriptionOpen}
            clipId={clipId}
            currentDescription={localDescription || ""}
            onDescriptionUpdated={handleDescriptionUpdated}
          />
        )}
      </>
    );
  }

  if (onlyTranscript) {
    return (
      <>
        <Card className="p-8">
          <div className="space-y-2">
            <div className="flex items-center justify-between pb-2">
              <div className="flex items-center gap-2">
                <span className="bg-slate-200 rounded p-1">
                  <FileText className="h-5 w-5" />
                </span>
                <h2 className="text-lg font-sans text-foreground font-bold ">Full Transcript</h2>
              </div>
              {clipId && canEditTranscript && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsEditTranscriptOpen(true)}
                >
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </Button>
              )}
            </div>
            <p className="text-lg font-sans font-normal text-foreground ">
              {getDisplayTranscript(localTranscript, localManuallyEdited)}
            </p>
          </div>
        </Card>
        {clipId && canEditTranscript && (
          <EditTranscriptDialog
            open={isEditTranscriptOpen}
            onOpenChange={setIsEditTranscriptOpen}
            currentTranscript={localTranscript || ""}
            transcriptManuallyEdited={localManuallyEdited}
            onSave={handleSaveTranscript}
          />
        )}
      </>
    );
  }

  // Both exist - show tabs with description as default
  return (
    <>
      <Card className="p-8">
        <Tabs defaultValue="description" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="description">Description</TabsTrigger>
            <TabsTrigger value="transcript">Full Transcript</TabsTrigger>
          </TabsList>

          <TabsContent value="description" className="mt-0">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Description</h2>
                {clipId && canEditDescription && (
                  <Button

                    variant="ghost"
                    size="sm"
                    onClick={() => setIsEditDescriptionOpen(true)}
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                )}
              </div>
              <p className="text-base text-muted-foreground whitespace-pre-wrap leading-loose">
                {localDescription}
              </p>
            </div>
          </TabsContent>

          <TabsContent value="transcript" className="mt-0">
            <div className="space-y-2">
              <div className="flex items-center justify-between pb-2">
                <div className="flex items-center gap-2">
                  <span className="bg-slate-200 rounded p-1">
                    <FileText className="h-5 w-5" />
                  </span>
                  <h2 className="text-lg font-sans text-foreground font-bold">Full Transcript</h2>
                </div>
                {clipId && canEditTranscript && (
                  <Button

                    variant="ghost"
                    size="sm"
                    onClick={() => setIsEditTranscriptOpen(true)}
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                )}
              </div>
              <p className="text-lg font-sans font-normal text-foreground">
                {getDisplayTranscript(localTranscript, localManuallyEdited)}
              </p>
            </div>
          </TabsContent>
        </Tabs>
      </Card>
      {clipId && canEditDescription && (
        <EditDescriptionDialog
          open={isEditDescriptionOpen}
          onOpenChange={setIsEditDescriptionOpen}
          clipId={clipId}
          currentDescription={localDescription || ""}
          onDescriptionUpdated={handleDescriptionUpdated}
        />
      )}
      {clipId && canEditTranscript && (
        <EditTranscriptDialog
          open={isEditTranscriptOpen}
          onOpenChange={setIsEditTranscriptOpen}
          currentTranscript={localTranscript || ""}
          transcriptManuallyEdited={localManuallyEdited}
          onSave={handleSaveTranscript}
        />
      )}
    </>
  );
}
