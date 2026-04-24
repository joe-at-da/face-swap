import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { User, MapPin, Calendar } from "lucide-react";

interface PublicClipInfoProps {
  mpName: string;
  party: string | null;
  partyAbbreviation: string | null;
  constituency: string | null;
  debateTopic: string | null;
  sessionType: string | null;
  sessionDate: string | null;
  createdAt: string;
}

export function PublicClipInfo({
  mpName,
  party,
  partyAbbreviation,
  constituency,
  debateTopic,
  sessionType,
  sessionDate,
  createdAt,
}: PublicClipInfoProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <User className="h-5 w-5" />
          Clip Information
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* MP Details */}
        <div>
          <h3 className="font-semibold text-lg">{mpName}</h3>
          {party && (
            <p className="text-sm text-muted-foreground">
              {party} {partyAbbreviation && `(${partyAbbreviation})`}
            </p>
          )}
          {constituency && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
              <MapPin className="h-3 w-3" />
              {constituency}
            </div>
          )}
        </div>

        {/* Session Info */}
        {(debateTopic || sessionType) && (
          <div className="space-y-2 border-t pt-4">
            <h4 className="text-sm font-medium">Session Details</h4>
            {debateTopic && (
              <p className="text-sm text-muted-foreground">{debateTopic}</p>
            )}
            <div className="flex flex-wrap gap-2">
              {sessionType && (
                <Badge variant="secondary">{sessionType}</Badge>
              )}
              {sessionDate && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Calendar className="h-3 w-3" />
                  {new Date(sessionDate).toLocaleDateString("en-GB", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Clip Created Date */}
        <div className="border-t pt-4">
          <p className="text-xs text-muted-foreground">
            Clip created on {new Date(createdAt).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
