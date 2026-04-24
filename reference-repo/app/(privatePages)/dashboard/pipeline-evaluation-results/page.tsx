import { Suspense } from "react";
import { PipelineEvaluationResultsClient } from "./components/pipeline-evaluation-results-client";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata = {
  title: "Pipeline Evaluation Results | MP AI",
  description: "View failed pipeline evaluation results",
};

function ResultsLoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-64 mb-2" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export default function PipelineEvaluationResultsPage() {
  return (
    <div className="container mx-auto py-8 px-4">
      <Suspense fallback={<ResultsLoadingSkeleton />}>
        <PipelineEvaluationResultsClient />
      </Suspense>
    </div>
  );
}
