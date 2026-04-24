"use client";

import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Loader2, Check } from "lucide-react";

interface FacebookPage {
  id: string;
  name: string;
  username?: string;
  picture?: {
    data?: {
      url?: string;
    };
  };
}

interface PageSelectorProps {
  pages: FacebookPage[];
  selectedPage: string | null;
  onSelect: (pageId: string) => void;
  onSubmit: () => void;
  submitting: boolean;
}

export function PageSelector({
  pages,
  selectedPage,
  onSelect,
  onSubmit,
  submitting,
}: PageSelectorProps) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
          <svg
            className="w-6 h-6 text-primary"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold">Select a Facebook Page</h2>
        <p className="text-muted-foreground text-sm">
          Choose which Page you want to post to
        </p>
      </div>

      <RadioGroup value={selectedPage || ""} onValueChange={onSelect}>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {pages.map((page) => (
            <div
              key={page.id}
              className={`flex items-center space-x-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                selectedPage === page.id
                  ? "border-primary bg-primary/5"
                  : "border-border hover:bg-muted/50"
              }`}
              onClick={() => onSelect(page.id)}
            >
              <RadioGroupItem value={page.id} id={page.id} />
              <Avatar className="h-10 w-10">
                <AvatarImage src={page.picture?.data?.url} alt={page.name} />
                <AvatarFallback>
                  {page.name.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <Label htmlFor={page.id} className="font-medium cursor-pointer">
                  {page.name}
                </Label>
                {page.username && (
                  <p className="text-xs text-muted-foreground truncate">
                    @{page.username}
                  </p>
                )}
              </div>
              {selectedPage === page.id && (
                <Check className="h-5 w-5 text-primary flex-shrink-0" />
              )}
            </div>
          ))}
        </div>
      </RadioGroup>

      <Button
        onClick={onSubmit}
        disabled={!selectedPage || submitting}
        className="w-full"
        size="lg"
      >
        {submitting ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Connecting...
          </>
        ) : (
          "Connect to This Page"
        )}
      </Button>
    </div>
  );
}
