"use client";

import dynamic from "next/dynamic";
import type { RemotionEditorProps } from "@/types/remotionEditor";

const RemotionEditorLayout = dynamic(
  () =>
    import("./RemotionEditorLayout").then((mod) => mod.RemotionEditorLayout),
  {
    ssr: false,
    loading: () => <EditorSkeleton />,
  }
);

function EditorSkeleton() {
  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-background">
      <div className="flex-shrink-0 border-b border-border px-4 py-2">
        <div className="h-4 w-40 bg-muted animate-pulse rounded" />
        <div className="h-3 w-24 bg-muted animate-pulse rounded mt-1" />
      </div>
      <div className="flex-1 flex items-center justify-center bg-black/90">
        <div className="w-3/4 aspect-video bg-muted/20 animate-pulse rounded" />
      </div>
      <div className="h-48 border-t border-border bg-muted/30 animate-pulse" />
    </div>
  );
}

export function RemotionEditorWrapper(props: RemotionEditorProps) {
  return <RemotionEditorLayout {...props} />;
}
