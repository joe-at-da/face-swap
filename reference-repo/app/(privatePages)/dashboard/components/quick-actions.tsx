import { Button } from "@/components/ui/button";
import { Plus, Settings, MonitorPlay, TrendingUp } from "lucide-react";
import Link from "next/link";

type QuickActionsProps = {
  canAccessAnalytics: boolean;
};

export function QuickActions({ canAccessAnalytics }: QuickActionsProps) {
  const actions = [
    {
      title: "Create New Clip",
      description: "Create a video clip from parliamentary sessions",
      href: "/dashboard/create-clips",
      icon: Plus,
      variant: "default" as const,
      primary: true,
    },
    {
      title: "View My Clips",
      description: "Browse and manage your personal clips",
      href: "/dashboard/my-clips",
      icon: MonitorPlay,
      variant: "outline" as const,
      primary: false,
    },
    ...(canAccessAnalytics
      ? [
          {
            title: "View Analytics",
            description: "Review connected social channel performance",
            href: "/dashboard/analytics",
            icon: TrendingUp,
            variant: "outline" as const,
            primary: false,
          },
        ]
      : []),
    {
      title: "Manage Settings",
      description: "Update your profile and preferences",
      href: "/dashboard/settings",
      icon: Settings,
      variant: "outline" as const,
      primary: false,
    },
  ];

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
      <div className="grid gap-4">
        {actions.map((action) => {
          const Icon = action.icon
          return (
            <Button
              key={action.title}
              asChild
              variant={action.variant}
              className={`h-auto p-4 justify-start shadow-none ${action.primary ? 'ring-2 ring-primary/20' : ''}`}
            >
              <Link href={action.href} className="block">
                <div className="flex items-start space-x-3 text-left">
                  <div className={`rounded-lg p-2 ${action.primary
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground'
                    }`}>
                    <Icon className={`h-4 w-4 ${action.primary ? 'text-primary-foreground' : 'text-foreground'}`} />
                  </div>
                  <div className="flex-1 space-y-1 min-w-0">
                    <h3 className="font-medium text-sm break-words">
                      {action.title}
                    </h3>
                    <p className={`text-sm leading-relaxed ${action.primary ? 'text-primary-foreground/80' : 'text-muted-foreground'}`}>
                      {action.description}
                    </p>
                  </div>
                </div>
              </Link>
            </Button>
          )
        })}
      </div>
    </div>
  );
}
