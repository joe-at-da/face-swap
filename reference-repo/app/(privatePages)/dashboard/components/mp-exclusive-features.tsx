import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, ArrowRight } from "lucide-react";

export function MPExclusiveFeatures() {
  const features = [
    "Priority clip processing and rendering",
    "Extended clip duration limits", 
    "Advanced analytics and insights",
    "Team collaboration features",
  ];

  return (
    <Card className="bg-gradient-to-br from-primary/5 via-background to-background border-primary/20">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <CardTitle>MP Exclusive Features</CardTitle>
        </div>
        <CardDescription>
          As a verified Parliament member, you have access to premium features
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2 text-sm">
          {features.map((feature) => (
            <li key={feature} className="flex items-center">
              <ArrowRight className="h-4 w-4 mr-2 text-primary" />
              {feature}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}