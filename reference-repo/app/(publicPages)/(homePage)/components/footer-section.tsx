import { Mail } from "lucide-react";
import Link from "next/link";
import { Logo } from "@/components/logo";

export function FooterSection() {
  return (
    <footer className=" px-4 py-8 md:px-6 md:py-12 lg:px-8" role="contentinfo">
      <div className="container mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
          {/* Left side - Logo and description */}
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-[127px] h-[44px]">
                <Logo />
              </div>
            </div>
            <p className="text-foreground text-sm mb-2 max-w-md">
              Empowering British MPs with cutting-edge tools for parliamentary
              communication and constituent engagement.
            </p>
            <div className="text-xs text-muted-foreground space-y-1 mt-8">
              <p>© 2025 ParliamentConnect. All rights reserved.</p>
              <p>Developed by Veedoo.</p>
            </div>
          </div>

          {/* Right side - Privacy Policy and Contact info */}
          <div className="flex flex-col md:flex-row items-start md:items-center gap-4">
            <Link
              href="/privacy-policy"
              className="text-muted-foreground text-sm font-medium hover:text-primary-hover"
            >
              Privacy Policy
            </Link>
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-muted-foreground hover:text-primary-hover" />
              <a
                href="mailto:info@parliamentconnect.com"
                className="text-muted-foreground text-sm font-medium hover:text-primary-hover"
              >
                info@parliamentconnect.com
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
