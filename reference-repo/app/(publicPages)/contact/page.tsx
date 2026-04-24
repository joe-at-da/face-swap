import type { Metadata } from "next";
import { ContactForm } from "@/app/(publicPages)/contact/components/contact-form";
import { Mail } from "lucide-react";

export const metadata: Metadata = {
  title: "Contact Us | Parliament Connect",
  description:
    "Get in touch with the Parliament Connect team. We'd love to hear from you.",
};

export default function ContactPage() {
  return (
    <div className="flex-1 px-4 py-12 sm:py-16">
        <div className="mx-auto w-full max-w-lg space-y-8">
          <div className="text-center space-y-3">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
              <Mail className="h-7 w-7 text-primary" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Get in touch
            </h1>
            <p className="text-muted-foreground text-base sm:text-lg">
              Contact Us or Request a Demo
            </p>
          </div>
          <ContactForm />
        </div>
      </div>
  );
}
