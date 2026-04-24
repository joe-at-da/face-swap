import { RequestDemoButton } from "../request-demo-button";

export function CTASection() {
  return (
    <section
      className="py-12 md:py-20 lg:px-8"
      aria-labelledby="cta-heading"
    >
      <div className="lg:container mx-auto w-full">
        <div className="bg-foreground text-primary-foreground p-8 md:p-12 text-center overflow-hidden">

          <h4
            id="cta-heading"
            className="text-2xl md:text-3xl lg:text-4xl font-bold"
          >
            Ready to See It in Action?
          </h4>
          <p className="mt-6 text-xl max-w-2xl mx-auto font-medium leading-relaxed">
            Join over 150 MPs who are already using ParliamentConnect to amplify their voice and connect with constituents more effectively.
          </p>
          <div className="mt-8">
            <RequestDemoButton variant="outline" className="text-foreground" />
          </div>

        </div>

      </div>
    </section>
  );
}