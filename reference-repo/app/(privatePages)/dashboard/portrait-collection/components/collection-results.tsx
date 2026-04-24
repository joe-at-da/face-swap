import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { PortraitCollectionStats } from "@/app/(privatePages)/dashboard/portrait-collection/constants";

interface CollectionResultsProps {
  stats: PortraitCollectionStats;
}

export function CollectionResults({ stats }: CollectionResultsProps) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="flex justify-center mb-4">
            <div className="rounded-full bg-primary/10 p-3">
              <CheckCircle2 className="h-12 w-12 text-primary" />
            </div>
          </div>
          <CardTitle className="text-center text-2xl">
            All Segments Evaluated!
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Summary Stats */}
          <div className="space-y-3 rounded-lg border border-border bg-muted/50 p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Total Evaluated
              </span>
              <span className="text-lg font-semibold">
                {stats.evaluatedCount}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Portraits Added
              </span>
              <span className="text-lg font-semibold text-primary">
                {stats.portraitsAddedCount}
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-3">
            <Button asChild className="w-full">
              <Link href="/dashboard">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Dashboard
              </Link>
            </Button>
          </div>

          {/* Additional Info */}
          <p className="text-center text-sm text-muted-foreground">
            Great job! All unidentified segments have been reviewed. The
            portraits you added will help improve MP identification accuracy in
            future processing runs.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
