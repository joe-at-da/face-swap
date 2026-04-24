"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, XCircle, HelpCircle, BarChart3 } from "lucide-react";
import type { EvaluationStats } from "../constants";

interface EvaluationResultsProps {
  stats: EvaluationStats;
}

export function EvaluationResults({ stats }: EvaluationResultsProps) {
  const wrongTotal = stats.wrongSpeakerCount + stats.wrongMpCount;
  const wrongPercentage =
    stats.evaluatedCount > 0
      ? Math.round((wrongTotal / stats.evaluatedCount) * 100)
      : 0;

  return (
    <div className="space-y-6">
      {/* Main result card */}
      <Card className="border-green-500/50">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mb-4">
            <CheckCircle2 className="h-8 w-8 text-green-500" />
          </div>
          <CardTitle className="text-xl">Evaluation Complete!</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-muted-foreground mb-4">
            All {stats.evaluatedCount.toLocaleString()} of{" "}
            {stats.totalSegments.toLocaleString()} segments have been evaluated.
          </p>

          {/* Accuracy display */}
          <div className="inline-block px-6 py-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground mb-1">
              Pipeline Accuracy
            </p>
            <p
              className={`text-4xl font-bold ${
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
        </CardContent>
      </Card>

      {/* Detailed breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <BarChart3 className="h-5 w-5" />
            Results Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Correct identifications */}
            <div className="flex items-center justify-between p-4 bg-green-500/10 rounded-lg">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                <div>
                  <p className="font-medium">Correct Identifications</p>
                  <p className="text-sm text-muted-foreground">
                    MP was correctly identified
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-green-500">
                  {stats.correctCount.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">
                  {stats.evaluatedCount > 0
                    ? Math.round(
                        (stats.correctCount / stats.evaluatedCount) * 100
                      )
                    : 0}
                  %
                </p>
              </div>
            </div>

            {/* Wrong speaker */}
            <div className="flex items-center justify-between p-4 bg-red-500/10 rounded-lg">
              <div className="flex items-center gap-3">
                <XCircle className="h-5 w-5 text-red-500" />
                <div>
                  <p className="font-medium">Wrong Speaker Detected</p>
                  <p className="text-sm text-muted-foreground">
                    Face detection picked wrong person
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-red-500">
                  {stats.wrongSpeakerCount.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">
                  {stats.evaluatedCount > 0
                    ? Math.round(
                        (stats.wrongSpeakerCount / stats.evaluatedCount) * 100
                      )
                    : 0}
                  %
                </p>
              </div>
            </div>

            {/* Wrong MP match */}
            <div className="flex items-center justify-between p-4 bg-orange-500/10 rounded-lg">
              <div className="flex items-center gap-3">
                <HelpCircle className="h-5 w-5 text-orange-500" />
                <div>
                  <p className="font-medium">Wrong MP Matched</p>
                  <p className="text-sm text-muted-foreground">
                    Correct speaker, wrong portrait match
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-orange-500">
                  {stats.wrongMpCount.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">
                  {stats.evaluatedCount > 0
                    ? Math.round(
                        (stats.wrongMpCount / stats.evaluatedCount) * 100
                      )
                    : 0}
                  %
                </p>
              </div>
            </div>

            {/* Summary */}
            <div className="pt-4 border-t">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Total Evaluated</span>
                <span className="font-medium">
                  {stats.evaluatedCount.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between text-sm mt-2">
                <span className="text-muted-foreground">Total Errors</span>
                <span className="font-medium text-red-500">
                  {wrongTotal.toLocaleString()} ({wrongPercentage}%)
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
