
import { Card } from "@/components/ui/card";
import { CTAButtons } from "../cta-buttons";

export function WorkflowSection() {
  return (
    <section
      className="px-4 py-12 md:px-6 md:py-20 lg:px-8"
      id="how-it-works"
      aria-labelledby="how-it-works-heading"
    >
      <Card className="container mx-auto p-10">
        <div className="mx-auto max-w-3xl text-center md:mb-12 mb-4">
          <h3
            id="how-it-works-heading"
            className="text-2xl md:text-3xl lg:text-4xl font-bold text-foreground"
          >
            Complete Workflow Timeline
          </h3>
          <p className="mt-4 text-muted-foreground text-base md:text-lg leading-relaxed">
            See how your parliamentary contribution transforms into engaging social media content.
          </p>
        </div>

        <div className="relative">
          {/* Timeline line */}
          <div className="hidden md:block absolute top-12 left-0 right-0 h-0.5 bg-gray-200"></div>

          {/* Timeline steps */}
          <div className="grid grid-cols-1 md:grid-cols-5 md:gap-8 gap-4 relative">
            {/* Step 1 */}
            <div className="flex flex-col items-center text-center">
              <div className="w-6 h-6 bg-foreground rounded-full border-4 border-white relative z-10 md:mb-4 md:mt-9"></div>
              <div className="hidden md:block w-px bg-gray-200 absolute top-6 left-1/2 transform -translate-x-1/2"></div>
              <h3 className="font-bold text-lg mt-4 mb-2 text-foreground">Speech Delivered</h3>
              <p className="text-sm  text-muted-foreground">You deliver your speech in Parliament</p>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col items-center text-center">
              <div className="w-6 h-6 bg-foreground rounded-full border-4 border-white relative z-10 md:mb-4 md:mt-9"></div>
              <div className="hidden md:block w-px bg-gray-200 absolute top-6 left-1/2 transform -translate-x-1/2"></div>
              <h3 className="font-bold text-lg mt-4 mb-2 text-foreground">Auto-Detection</h3>
              <p className="text-sm  text-muted-foreground">Our AI identifies and captures your contribution</p>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col items-center text-center">
              <div className="w-6 h-6 bg-foreground rounded-full border-4 border-white relative z-10 md:mb-4 md:mt-9"></div>
              <div className="w-px hidden md:block bg-gray-200 absolute top-6 left-1/2 transform -translate-x-1/2"></div>
              <h3 className="font-bold text-lg mt-4 mb-2 text-foreground">Processing</h3>
              <p className="text-sm text-muted-foreground">Transcription and editing happen automatically</p>
            </div>

            {/* Step 4 */}
            <div className="flex flex-col items-center text-center">
              <div className="w-6 h-6 bg-foreground rounded-full border-4 border-white relative z-10 md:mb-4 md:mt-9"></div>
              <div className="hidden md:block w-px bg-gray-200 absolute top-6 left-1/2 transform -translate-x-1/2"></div>
              <h3 className="font-bold text-lg mt-4 mb-2 text-foreground">Review & Publish</h3>
              <p className="text-sm text-muted-foreground">Quick review and one-click publishing</p>
            </div>

            {/* Step 5 */}
            <div className="flex flex-col items-center text-center">
              <div className="w-6 h-6 bg-foreground rounded-full border-4 border-white relative z-10 md:mb-4 md:mt-9"></div>
              <h3 className="font-bold text-lg mt-4 mb-2 text-foreground">Engagement</h3>
              <p className="text-sm text-muted-foreground">Connect with constituents across all platforms</p>
            </div>
          </div>
          <div className="mt-12 lg:mt-0">
            <CTAButtons />
          </div>
        </div>
      </Card>
    </section >
  );
}