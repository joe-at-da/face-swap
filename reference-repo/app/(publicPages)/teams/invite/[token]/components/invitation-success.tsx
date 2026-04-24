import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, Loader2 } from "lucide-react";

interface InvitationSuccessProps {
  teamName: string;
}

export function InvitationSuccess({ teamName }: InvitationSuccessProps) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center pb-6">
          <div className="flex justify-center mb-6">
            <div className="rounded-full bg-primary/10 p-4">
              <Check className="h-8 w-8 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl font-semibold">Welcome to the Team!</CardTitle>
          <CardDescription className="text-base mt-2">
            You&apos;ve successfully joined <strong>{teamName}</strong>.
            Redirecting you now...
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center pb-8">
          <Loader2 className="h-6 w-6 motion-safe:animate-spin text-primary" />
        </CardContent>
      </Card>
    </div>
  );
}
