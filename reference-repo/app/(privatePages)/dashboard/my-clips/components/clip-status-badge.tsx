"use client";

import { Badge } from "@/components/ui/badge";
import {
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  PlayCircle
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ClipStatusBadgeProps {
  status: string;
  className?: string;
  showIcon?: boolean;
}

export function ClipStatusBadge({
  status,
  className,
  showIcon = true
}: ClipStatusBadgeProps) {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case "pending_review":
        return {
          label: "Processing",
          variant: "secondary" as const,
          className: "bg-sky-200 text-blue-900",
          icon: Loader2,
          description: "Currently being processed",
          animated: true
        };
      case "processing":
        return {
          label: "Processing",
          variant: "secondary" as const,
          className: "bg-sky-200 text-foreground",
          icon: Loader2,
          description: "Currently being processed",
          animated: true
        };
      case "completed":
        return {
          label: "Completed",
          variant: "secondary" as const,
          className: "bg-emerald-200 text-emerald-800 border-emerald-200 hover:bg-emerald-100",
          icon: CheckCircle2,
          description: "Ready to view and share"
        };
      case "failed":
        return {
          label: "Failed",
          variant: "destructive" as const,
          className: "bg-red-100 text-red-900 border-red-200 hover:bg-red-100",
          icon: AlertCircle,
          description: "Processing failed"
        };
      case "ready":
        return {
          label: "Ready",
          variant: "default" as const,
          className: "bg-primary/10 text-primary border-primary/20 hover:bg-primary/20",
          icon: PlayCircle,
          description: "Available for viewing"
        };
      default:
        return {
          label: status,
          variant: "outline" as const,
          className: "",
          icon: Clock,
          description: "Unknown status"
        };
    }
  };

  const config = getStatusConfig(status);
  const Icon = config.icon;

  return (
    <Badge
      variant={config.variant}
      className={cn(
        "flex items-center gap-1 text-xs font-medium",
        config.className,
        className
      )}
      title={config.description}
    >
      {showIcon && status !== "completed" && (
        <Icon
          className={cn(
            "h-3 w-3",
            config.animated && "animate-spin"
          )}
        />
      )}
      {config.label}
    </Badge>
  );
}