"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ArrowUp } from "lucide-react";

export function FloatingTopButton() {
    const [isVisible, setIsVisible] = useState(false);

    // Show button when page is scrolled down
    useEffect(() => {
        const toggleVisibility = () => {
            if (window.pageYOffset > 300) {
                setIsVisible(true);
            } else {
                setIsVisible(false);
            }
        };

        window.addEventListener("scroll", toggleVisibility);

        return () => window.removeEventListener("scroll", toggleVisibility);
    }, []);

    // Scroll to top smoothly
    const scrollToTop = () => {
        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    };

    return (
        <>
            {isVisible && (
                <Button
                    onClick={scrollToTop}
                    className="fixed bottom-8 right-8 z-50 h-12 w-12 rounded-full bg-muted-foreground text-primary-foreground hover:bg-foreground/90 shadow-lg transition-all duration-300 hover:scale-110"
                    aria-label="Scroll to top"
                >
                    <ArrowUp className="h-5 w-5" />
                </Button>
            )}
        </>
    );
}
