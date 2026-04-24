import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Users, CheckCircle2, Clock, Image as ImageIcon, ListChecks } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PortraitCollectionStats } from "@/app/(privatePages)/dashboard/portrait-collection/constants";

interface CollectionProgressProps {
  stats: PortraitCollectionStats;
}

export function CollectionProgress({ stats }: CollectionProgressProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">Collection Progress</CardTitle>
          <div className={cn(
            "flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium",
            stats.completionPercentage === 100
              ? "bg-green-500/10 text-green-700 dark:text-green-400"
              : "bg-primary/10 text-primary"
          )}>
            <ListChecks className="h-4 w-4" />
            {stats.completionPercentage}% Complete
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Enhanced Progress Bar */}
        <div className="space-y-3">
          <div className="relative">
            <Progress value={stats.completionPercentage} className="h-3" />
            {stats.evaluatedCount > 0 && (
              <div
                className="absolute top-0 h-3 rounded-full bg-gradient-to-r from-primary to-primary/80 transition-all"
                style={{ width: `${stats.completionPercentage}%` }}
              />
            )}
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{stats.evaluatedCount} of {stats.totalUnidentified} segments evaluated</span>
            <span>{stats.remainingCount} remaining</span>
          </div>
        </div>

        {/* Enhanced Stats Grid */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {/* Total Segments */}
          <div className="rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent/50">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-muted p-2">
                <ListChecks className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex-1 space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Total Segments</p>
                <p className="text-2xl font-bold tracking-tight">{stats.totalUnidentified}</p>
              </div>
            </div>
          </div>

          {/* Evaluated */}
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 transition-colors hover:bg-primary/10">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-primary/10 p-2">
                <CheckCircle2 className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1 space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Completed</p>
                <p className="text-2xl font-bold tracking-tight text-primary">
                  {stats.evaluatedCount}
                </p>
              </div>
            </div>
          </div>

          {/* Remaining */}
          <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-4 transition-colors hover:bg-orange-500/10">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-orange-500/10 p-2">
                <Clock className="h-4 w-4 text-orange-600 dark:text-orange-400" />
              </div>
              <div className="flex-1 space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Remaining</p>
                <p className="text-2xl font-bold tracking-tight text-orange-600 dark:text-orange-400">
                  {stats.remainingCount}
                </p>
              </div>
            </div>
          </div>

          {/* Portraits Added */}
          <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-4 transition-colors hover:bg-green-500/10">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-green-500/10 p-2">
                <ImageIcon className="h-4 w-4 text-green-600 dark:text-green-400" />
              </div>
              <div className="flex-1 space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Portraits</p>
                <p className="text-2xl font-bold tracking-tight text-green-600 dark:text-green-400">
                  {stats.portraitsAddedCount}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Active Evaluators */}
        {stats.activeEvaluators > 0 && (
          <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/50 p-4">
            <div className="rounded-full bg-primary/10 p-2">
              <Users className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">
                {stats.activeEvaluators}{" "}
                {stats.activeEvaluators === 1 ? "person is" : "people are"} currently evaluating
              </p>
              <p className="text-xs text-muted-foreground">
                Working together to complete the collection
              </p>
            </div>
          </div>
        )}

        {/* Completion Message */}
        {stats.completionPercentage === 100 && (
          <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              <div>
                <p className="font-medium text-green-600 dark:text-green-400">
                  All segments evaluated! 🎉
                </p>
                <p className="text-sm text-muted-foreground">
                  Great work! {stats.portraitsAddedCount} portraits have been collected.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
