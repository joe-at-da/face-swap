import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  Video,
  Share2,
} from "lucide-react";

export function StatsSection() {
  return (
    <section className="px-4 py-12 md:px-6 md:py-20 lg:px-8 bg-gradient-to-b from-muted/50 to-background">
      <div className="container mx-auto">
        <div className="text-center mb-8">
          <h3 className="font-serif text-2xl md:text-3xl font-bold text-foreground">
            Trusted by Parliament
          </h3>
          <p className="mt-2 text-muted-foreground">
            The platform of choice for modern MPs
          </p>
        </div>
        <div className="grid gap-8 md:grid-cols-3 max-w-4xl mx-auto">
          <Card className="relative p-6 text-center bg-gradient-to-br from-background via-background/98 to-primary/5 transition-all duration-300 group hover:-translate-y-1 border border-border/50 hover:border-primary/30 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-t from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative">
              <p className="relative z-10 font-serif text-5xl md:text-6xl font-bold bg-gradient-to-r from-primary via-purple-500 to-primary bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient-shift">
                650+
              </p>
              <div className="absolute -top-2 -right-2">
                <Badge
                  variant="secondary"
                  className="text-xs font-semibold px-2.5 py-0.5 bg-primary/10 text-primary border border-primary/20"
                >
                  <TrendingUp className="h-3 w-3 mr-1" />
                  Growing
                </Badge>
              </div>
            </div>
            <p className="relative z-10 mt-3 text-muted-foreground font-medium">
              MPs Using The Platform
            </p>
            <div className="relative z-10 mt-3 h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full w-4/5 bg-gradient-to-r from-primary to-primary/70 rounded-full" />
            </div>
          </Card>

          <Card className="relative p-6 text-center bg-gradient-to-br from-background via-background/98 to-primary/5 transition-all duration-300 group hover:-translate-y-1 border border-border/50 hover:border-primary/30 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-t from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative">
              <p className="relative z-10 font-serif text-5xl md:text-6xl font-bold bg-gradient-to-r from-primary via-purple-500 to-primary bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient-shift">
                50K+
              </p>
              <div className="absolute -top-2 -right-2">
                <Badge
                  variant="secondary"
                  className="text-xs font-semibold px-2.5 py-0.5 bg-primary/10 text-primary border border-primary/20"
                >
                  <Video className="h-3 w-3 mr-1" />
                  Monthly
                </Badge>
              </div>
            </div>
            <p className="relative z-10 mt-3 text-muted-foreground font-medium">
              Clips Created
            </p>
            <div className="relative z-10 mt-3 h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full w-3/4 bg-gradient-to-r from-primary to-primary/70 rounded-full" />
            </div>
          </Card>

          <Card className="relative p-6 text-center bg-gradient-to-br from-background via-background/98 to-primary/5 transition-all duration-300 group hover:-translate-y-1 border border-border/50 hover:border-primary/30 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-t from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative">
              <p className="relative z-10 font-serif text-5xl md:text-6xl font-bold bg-gradient-to-r from-primary via-purple-500 to-primary bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient-shift">
                10M+
              </p>
              <div className="absolute -top-2 -right-2">
                <Badge
                  variant="secondary"
                  className="text-xs font-semibold px-2.5 py-0.5 bg-primary/10 text-primary border border-primary/20"
                >
                  <Share2 className="h-3 w-3 mr-1" />
                  Reach
                </Badge>
              </div>
            </div>
            <p className="relative z-10 mt-3 text-muted-foreground font-medium">
              Social Media Impact
            </p>
            <div className="relative z-10 mt-3 h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full w-full bg-gradient-to-r from-primary to-primary/70 rounded-full animate-pulse" />
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}