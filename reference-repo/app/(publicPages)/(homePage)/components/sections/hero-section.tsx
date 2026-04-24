import { RequestDemoButton } from "../request-demo-button";
import { HeroImage } from "../hero-image";

export function HeroSection() {
  return (
    <section className="py-20">
      <div className="container mx-auto px-4">
        <div className="flex lg:flex-row flex-col justify-center items-center lg:gap-10">
          <div className="lg:w-1/2 w-full mb-10 lg:mb-0">
            <h1 className="text-4xl lg:text-6xl font-bold mb-6 text-foreground">
              Transform Your Parliamentary Voice Into Social Impact
            </h1>
            <p className="text-xl md:text-2xl text-muted-foreground mb-8">
              Automatically discover, transcribe, and publish your parliamentary
              speeches across all social media platforms. Connect with
              constituents like never before.
            </p>
            <ul className="list-disc list-inside text-muted-foreground mb-8">
              <li>Automated speech discovery from Parliamentary sessions</li>
              <li>AI-powered transcription with 99% accuracy</li>
              <li>One-click publishing to all social platforms</li>
              <li>Searchable library of speeches</li>
            </ul>
            <RequestDemoButton className="bg-foreground text-primary-foreground" />
          </div>
          <div className="lg:w-1/2 lg:block hidden">
            <HeroImage />
          </div>
        </div>
      </div>
    </section>
  );
}
