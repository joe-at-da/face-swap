import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Video, Calendar, PlayCircle, Users } from "lucide-react";

export function StatsOverview() {
  const stats = [
    {
      title: "Total Clips",
      value: "0",
      description: "Start creating clips",
      icon: Video,
    },
    {
      title: "Scheduled Posts", 
      value: "0",
      description: "No upcoming posts",
      icon: Calendar,
    },
    {
      title: "Total Views",
      value: "0", 
      description: "Across all platforms",
      icon: PlayCircle,
    },
    {
      title: "Following",
      value: "0",
      description: "MPs you follow", 
      icon: Users,
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.title}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}