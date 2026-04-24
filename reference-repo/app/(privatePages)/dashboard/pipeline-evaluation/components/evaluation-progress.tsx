"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, XCircle, HelpCircle } from "lucide-react";
import type { EvaluationStats } from "../constants";

interface EvaluationProgressProps {
  stats: EvaluationStats;
}

export function EvaluationProgress({ stats }: EvaluationProgressProps) {
  const progressPercentage =
    stats.totalSegments > 0
      ? Math.round((stats.evaluatedCount / stats.totalSegments) * 100)
      : 0;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Progress header */}
          <div className="flex justify-between items-center">
            <div className="space-y-1">
              <p className="text-sm font-medium">Evaluation Progress</p>
              <p className="text-xs text-muted-foreground">
                {stats.evaluatedCount.toLocaleString()} of{" "}
                {stats.totalSegments.toLocaleString()} segments evaluated
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold">{progressPercentage}%</p>
              <p className="text-xs text-muted-foreground">
                {stats.remainingCount.toLocaleString()} remaining
              </p>
            </div>
          </div>

          {/* Progress bar */}
          <Progress value={progressPercentage} className="h-2" />

          {/* Stats breakdown */}
          <div className="grid grid-cols-3 gap-4 pt-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <div>
                <p className="text-sm font-medium">
                  {stats.correctCount.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground">Correct</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-500" />
              <div>
                <p className="text-sm font-medium">
                  {stats.wrongSpeakerCount.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground">Wrong Speaker</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-orange-500" />
              <div>
                <p className="text-sm font-medium">
                  {stats.wrongMpCount.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground">Wrong MP</p>
              </div>
            </div>
          </div>

          {/* Accuracy */}
          {stats.evaluatedCount > 0 && (
            <div className="pt-2 border-t">
              <div className="flex justify-between items-center">
                <p className="text-sm text-muted-foreground">
                  Current Accuracy
                </p>
                <p
                  className={`text-lg font-semibold ${
                    stats.accuracyPercentage >= 80
                      ? "text-green-500"
                      : stats.accuracyPercentage >= 60
                      ? "text-yellow-500"
                      : "text-red-500"
                  }`}
                >
                  {stats.accuracyPercentage}%
                </p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
