import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

import {
  Search,
  Mic,
  Pencil,
  Share2,
} from "lucide-react";

export function FeaturesSection() {
  return (
    <section
      className="px-4 py-12 md:px-6 md:py-20 lg:px-8"
      id="features"
      aria-labelledby="features-heading"
    >
      <div className="container mx-auto">
        <div className="mx-auto max-w-3xl text-center mb-12">
          <h2
            id="features-heading"
            className="text-3xl md:text-4xl font-bold text-foreground"
          >
            Powerful Features Built for MPs
          </h2>
          <p className="mt-4 text-muted-foreground text-xl  leading-relaxed">
            Everything you need to transform your parliamentary contributions into engaging social media content that connects with your constituents.
          </p>
        </div>

        {/* Feature Highlights with Enhanced Visuals */}
        <div className="space-y-20">

          <div className="grid md:grid-cols-2 gap-8">
            <Card className="border-slate-300">
              <CardHeader className="flex flex-row gap-4">
                <div className="w-8 h-8 p-[8px] bg-primary/10 rounded-xs flex items-center justify-center mb-4">
                  <Search className="w-6 h-6 not-only-of-type:text-foreground" />
                </div>
                <div>
                  <CardTitle className="pb-2 text-foreground text-xl font-bold">Automated Speech Discovery</CardTitle>
                  <CardDescription className="text-muted-foreground text-base">
                    Our AI automatically scans Parliamentary archives and identifies your speeches, debates, and contributions in real-time.
                  </CardDescription>
                </div>
              </CardHeader>
            </Card>

            <Card className="border-slate-300">
              <CardHeader className="flex flex-row gap-4">
                <div className="w-8 h-8 p-[8px] bg-primary/10 rounded-xs flex items-center justify-center mb-4">
                  <Mic className="w-6 h-6 text-foreground" />
                </div>
                <div>
                  <CardTitle className="pb-2 text-foreground text-xl font-bold">AI-Powered Transcription</CardTitle>
                  <CardDescription className="text-muted-foreground text-base">
                    Industry-leading speech recognition technology converts your parliamentary contributions into accurate, searchable text with 99% accuracy.
                  </CardDescription>
                </div>
              </CardHeader>
            </Card>

            <Card className="border-slate-300">
              <CardHeader className="flex flex-row gap-4">
                <div className="w-8 h-8 p-[8px] bg-primary/10 rounded-xs flex items-center justify-center mb-4">
                  <Pencil className="w-6 h-6 text-foreground" />
                </div>
                <div>
                  <CardTitle className="pb-2 text-foreground text-xl font-bold">Intelligent Video Editing</CardTitle>
                  <CardDescription className="text-muted-foreground text-base">
                    Smart editing tools automatically create engaging clips from your speeches, optimised for each social media platform&apos;s requirements.
                  </CardDescription>
                </div>
              </CardHeader>
            </Card>

            <Card className="border-slate-300">
              <CardHeader className="flex flex-row gap-4">
                <div className="w-8 h-8 p-[8px] bg-primary/10 rounded-xs flex items-center justify-center mb-4">
                  <Share2 className="w-6 h-6 text-foreground" />
                </div>
                <div>
                  <CardTitle className="pb-2 text-foreground text-xl font-bold">Multi-Platform Publishing</CardTitle>
                  <CardDescription className="text-muted-foreground text-base">
                    Seamlessly publish your content across Twitter, LinkedIn, Facebook, TikTok, and Instagram with platform-specific formatting.
                  </CardDescription>
                </div>
              </CardHeader>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}
