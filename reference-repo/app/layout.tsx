import type { Metadata } from "next";
import { Inter, Playfair_Display, Fira_Code } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import { UserStoreProvider } from "@/stores/providers/UserStoreProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PostHogProvider } from "@/components/providers/PostHogProvider";
import { Toaster } from "@/components/ui/sonner";
import { VibeKanbanProvider } from "@/components/providers/VibeKanbanProvider";

const fontSans = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const fontSerif = Playfair_Display({
  variable: "--font-serif",
  subsets: ["latin"],
});

const fontMono = Fira_Code({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Parliament Connect - Transform Your Parliamentary Voice Into Social Impact",
  description:
    "AI-powered platform for UK MPs and staff to create, search, and share video clips from parliament sessions. Schedule social media posts and track engagement.",
  keywords:
    "parliament, MP, AI, video clips, social media, UK politics, parliament sessions, content creation",
  openGraph: {
    title: "Parliament Connect - Transform Your Parliamentary Voice Into Social Impact",
    description:
      "Transform parliament sessions into powerful social media content with AI-powered tools.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${fontSans.variable} ${fontSerif.variable} ${fontMono.variable} antialiased`}
      >
        <ErrorBoundary componentName="RootLayout">
          <UserStoreProvider>
            <Suspense fallback={null}>
              <PostHogProvider>{children}</PostHogProvider>
            </Suspense>
          </UserStoreProvider>
        </ErrorBoundary>
        <Toaster />
        <VibeKanbanProvider />
      </body>
    </html>
  );
}
