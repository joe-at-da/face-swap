"use client";

import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const TEXT_MESSAGES = [
  { text: "Searching...", delay: 0 },
  { text: "Finding matches...", delay: 1500 },
  { text: "Almost there...", delay: 3000 },
];

const AI_MESSAGES = [
  { text: "Searching...", delay: 0 },
  { text: "Analysing your query with AI...", delay: 1500 },
  { text: "Finding the best matches...", delay: 3000 },
];

interface SearchLoadingStateProps {
  searchType: "text" | "hybrid";
}

export default function SearchLoadingState({ searchType }: SearchLoadingStateProps) {
  const [messageIndex, setMessageIndex] = useState(0);
  const messages = searchType === "hybrid" ? AI_MESSAGES : TEXT_MESSAGES;

  useEffect(() => {
    setMessageIndex(0);
    const timers = messages.slice(1).map((msg, i) =>
      setTimeout(() => setMessageIndex(i + 1), msg.delay)
    );

    return () => timers.forEach(clearTimeout);
  }, [messages]);

  return (
    <Card>
      <CardContent className="p-12 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-4" />
        <p className="text-xl md:text-lg text-muted-foreground">
          {messages[messageIndex].text}
        </p>
      </CardContent>
    </Card>
  );
}
