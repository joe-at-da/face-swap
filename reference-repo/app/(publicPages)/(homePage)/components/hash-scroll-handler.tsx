"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

export function HashScrollHandler() {
  const pathname = usePathname();

  useEffect(() => {
    const scrollToHash = () => {
      if (pathname === "/") {
        // Check both window.location.hash and the URL hash
        const hash = window.location.hash.substring(1) || window.location.href.split('#')[1];

        if (hash) {
          const attemptScroll = (attempts = 0) => {
            const element = document.getElementById(hash);

            if (element) {
              // Small delay to ensure smooth scroll works
              setTimeout(() => {
                element.scrollIntoView({ behavior: 'smooth' });
              }, 50);
            } else if (attempts < 15) {
              // Retry if element not found yet (page still loading)
              // Increased attempts for slower page loads
              setTimeout(() => attemptScroll(attempts + 1), 150);
            }
          };

          // Start attempting to scroll after a short delay
          setTimeout(() => attemptScroll(), 200);
        }
      }
    };

    // Scroll on pathname change (when navigating to home page)
    scrollToHash();

    // Also listen for hash changes
    const handleHashChange = () => {
      scrollToHash();
    };

    window.addEventListener('hashchange', handleHashChange);

    // Also check hash after a delay in case hashchange doesn't fire
    const timeoutId = setTimeout(() => {
      scrollToHash();
    }, 500);

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      clearTimeout(timeoutId);
    };
  }, [pathname]);

  return null;
}

