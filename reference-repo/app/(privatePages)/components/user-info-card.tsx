import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { User, Shield, Mail } from "lucide-react";

interface UserInfoCardProps {
  email: string;
  isParliamentMember?: boolean;
  isFirstLogin?: boolean;
}

export function UserInfoCard({ email, isParliamentMember, isFirstLogin }: UserInfoCardProps) {
  return (
    <Card className="border-border/50 shadow-lg">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-semibold">User Information</CardTitle>
          {isParliamentMember && (
            <Badge variant="secondary" className="px-3 py-1">
              <Shield className="mr-1.5 h-3 w-3" />
              MP Account
            </Badge>
          )}
        </div>
        <CardDescription>
          Your account details and status
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-start space-x-3">
          <Mail className="h-5 w-5 text-muted-foreground mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">Email Address</p>
            <p className="text-base font-medium text-foreground">{email}</p>
          </div>
        </div>

        <div className="flex items-start space-x-3">
          <User className="h-5 w-5 text-muted-foreground mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">Account Type</p>
            <p className="text-base font-medium text-foreground">
              {isParliamentMember ? "Parliament Member" : "Regular User"}
            </p>
          </div>
        </div>

        {isFirstLogin !== undefined && (
          <div className="pt-3 border-t border-border">
            <Badge variant={isFirstLogin ? "outline" : "default"} className="text-xs">
              {isFirstLogin ? "Setup Required" : "Setup Complete"}
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}