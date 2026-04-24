"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Clock,
  Video,
  Bell,
  Share,
  AlertCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import Link from "next/link";

interface Activity {
  id: string;
  type: string;
  title: string;
  description: string;
  time: string;
  status: string;
  metadata: {
    clip_id?: string;
    mp_name?: string;
    user_created?: boolean;
    source_clip?: boolean;
    platform?: string;
    mock?: boolean;
    system?: boolean;
    title?: string;
  };
}

const getActivityIcon = (type: string) => {
  switch (type) {
    case "clip_created":
      return Video;
    case "new_mp_clip":
      return Bell;
    case "social_scheduled":
      return Share;
    case "system_notification":
      return Bell;
    default:
      return Clock;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'bg-green-50 text-green-700 border-green-200';
    case 'processing':
      return 'bg-blue-50 text-blue-700 border-blue-200';
    case 'pending_review':
      return 'bg-orange-50 text-orange-700 border-orange-200';
    case 'available':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'scheduled':
      return 'bg-purple-50 text-purple-700 border-purple-200';
    case 'info':
      return 'bg-blue-50 text-blue-700 border-blue-200';
    case 'failed':
      return 'bg-red-50 text-red-700 border-red-200';
    default:
      return 'bg-muted text-muted-foreground border-border';
  }
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'completed':
      return 'Completed';
    case 'processing':
      return 'Processing';
    case 'pending_review':
      return 'Pending';
    case 'available':
      return 'Available';
    case 'scheduled':
      return 'Scheduled';
    case 'info':
      return 'Info';
    case 'failed':
      return 'Failed';
    default:
      return status;
  }
};

export function RecentActivity() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchActivity = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch("/api/dashboard/activity?limit=8");
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch activity");
        }

        setActivities(data.data || []);
      } catch (error) {
        console.error("Error fetching dashboard activity:", error);
        setError(error instanceof Error ? error.message : "Failed to load activity");
        toast.error("Failed to load recent activity");
      } finally {
        setIsLoading(false);
      }
    };

    fetchActivity();
  }, []);

  const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 1) return "Just now";
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;

    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h ago`;

    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays}d ago`;

    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short'
    });
  };

  if (isLoading) {
    return (
      <div>
        <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
        <Card>
          <CardContent className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-start space-x-4 pb-4 last:pb-0">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </div>
                  <Skeleton className="h-4 w-64" />
                  <Skeleton className="h-3 w-16" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
        <Card>
          <CardContent className="flex items-center justify-center h-32">
            <div className="text-center space-y-2">
              <AlertCircle className="h-6 w-6 mx-auto text-destructive" />
              <p className="text-sm text-muted-foreground">
                {error}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (activities.length === 0) {
    return (
      <div>
        <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
        <Card>
          <CardContent className="flex items-center justify-center h-32">
            <div className="text-center space-y-2">
              <Clock className="h-6 w-6 mx-auto text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                No recent activity to show
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
      <Card>
        <CardContent className="space-y-4">
          {activities.map((activity) => {
            const Icon = getActivityIcon(activity.type);
            const isSystemNotification = activity.type === "system_notification";
            return (
              <div key={activity.id} className={`flex items-start pb-4 last:pb-0 ${!isSystemNotification ? 'space-x-4' : ''}`}>
                {!isSystemNotification && (
                  <Avatar className="h-8 w-8 bg-muted">
                    <AvatarFallback className="bg-primary/10">
                      <Icon className="h-4 w-4 text-primary" />
                    </AvatarFallback>
                  </Avatar>
                )}
                <div className="flex-1 space-y-1">
                  {isSystemNotification ? (
                    <>
                      <div className="flex items-start justify-between gap-2">
                        <div className="text-sm font-normal text-foreground flex-1">
                          {activity.title} {activity.description}
                        </div>
                        <span className="hidden sm:inline text-sm text-muted-foreground whitespace-nowrap">{formatTimeAgo(activity.time)}</span>
                      </div>
                      <div className="sm:hidden">
                        <span className="text-sm text-muted-foreground">{formatTimeAgo(activity.time)}</span>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm text-foreground font-medium">
                        {activity.title}
                        {activity.metadata.mock && (
                          <Badge variant="secondary" className="ml-2 text-xs">
                            Demo
                          </Badge>
                        )}
                      </h4>
                      {activity.status !== 'info' ? (
                        <Badge
                          variant="outline"
                          className={getStatusColor(activity.status)}
                        >
                          {getStatusLabel(activity.status)}
                        </Badge>
                      ) : null}
                    </div>
                  )}
                  {!isSystemNotification && (
                    <p className="text-sm text-muted-foreground">
                      {activity.description}
                    </p>
                  )}
                  {!isSystemNotification && (
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-muted-foreground">
                        {formatTimeAgo(activity.time)}
                      </p>
                      {activity.metadata.clip_id && activity.metadata.user_created && (
                        <Button variant="ghost" size="sm" asChild className="h-6 text-xs">
                          <Link href={`/dashboard/my-clips/${activity.metadata.clip_id}`}>
                            View clip
                          </Link>
                        </Button>
                      )}
                      {activity.metadata.clip_id && activity.metadata.source_clip && (
                        <Button variant="ghost" size="sm" asChild className="h-6 text-xs">
                          <Link href={`/dashboard/create-clips/clip/${activity.metadata.clip_id}`}>
                            Create clip
                          </Link>
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Integration notice */}
          <div className="pt-4">
            <div className="rounded-lg p-3 text-center bg-[#DBEAFE]">
              <p className="text-xs text-[#1E40AF]">
                Real-time notifications and enhanced activity tracking coming soon
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}