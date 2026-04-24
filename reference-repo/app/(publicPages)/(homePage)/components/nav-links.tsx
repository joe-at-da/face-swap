"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavLinksProps {
    onLinkClick?: () => void;
}

export default function NavLinks({ onLinkClick }: NavLinksProps) {
    const pathname = usePathname();
    const isHomePage = pathname === "/";

    const handleSectionClick = (e: React.MouseEvent<HTMLAnchorElement>, sectionId: string) => {
        if (isHomePage) {
            e.preventDefault();
            const section = document.getElementById(sectionId);
            if (section) {
                section.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            // When on another page, navigate to home with hash
            // Using window.location.href ensures hash is preserved during navigation
            e.preventDefault();
            window.location.href = `/#${sectionId}`;
        }
        onLinkClick?.();
    };

    return (
        <nav className="flex flex-col space-y-6 lg:flex-row lg:items-center lg:space-y-0 lg:space-x-8">
            <Link
                href="/#features"
                onClick={(e) => handleSectionClick(e, 'features')}
                className="text-left text-foreground cursor-pointer text-lg lg:text-base font-medium hover:text-accent-foreground transition-colors"
            >
                Features
            </Link>
            <Link
                href="/#how-it-works"
                onClick={(e) => handleSectionClick(e, 'how-it-works')}
                className="text-left text-foreground cursor-pointer text-lg lg:text-base font-medium hover:text-accent-foreground transition-colors"
            >
                How It Works
            </Link>
            <Link
                href="/contact"
                className="text-left text-foreground text-lg lg:text-base font-medium hover:text-accent-foreground transition-colors"
                onClick={onLinkClick}
            >
                Contact
            </Link>
        </nav>
    );
}
