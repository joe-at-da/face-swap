// Components
import { HeroSection } from "@/app/(publicPages)/(homePage)/components/sections/hero-section";
import { FeaturesSection } from "@/app/(publicPages)/(homePage)/components/sections/features-section";
import { WorkflowSection } from "@/app/(publicPages)/(homePage)/components/sections/workflow-section";
import { CTASection } from "@/app/(publicPages)/(homePage)/components/sections/cta-section";
import { FloatingTopButton } from "@/app/(publicPages)/(homePage)/components/floating-top-button";
import { HashScrollHandler } from "@/app/(publicPages)/(homePage)/components/hash-scroll-handler";

export default function HomePage() {
  return (
    <>
      <HashScrollHandler />
      <HeroSection />

      <FeaturesSection />


      <WorkflowSection />

      <CTASection />

      <FloatingTopButton />
    </>
  );
}
