"use client";

import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { usePostHog } from "posthog-js/react";
import { SetupStep3Data, setupStep3Schema } from "@/schemas/authSchema";
import { Button } from "@/components/ui/button";
import { Form, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SmartAvatar } from "@/components/smart-avatar";
import { Badge } from "@/components/ui/badge";
import { Search, Loader2, Check, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface MP {
  member_id: number;
  display_name: string;
  party_abbreviation: string;
  party_name?: string;
  constituency_name: string;
  parliament_member_portraits: Array<{
    image_url: string;
    is_primary: boolean;
  }>;
}

interface MpSelectionStepProps {
  onNext: (data: SetupStep3Data) => void;
  onPrevious: () => void;
  initialData?: Partial<SetupStep3Data>;
  isLoading?: boolean;
  initialMps: MP[];
}

export function MpSelectionStep({ onNext, onPrevious, initialData, isLoading, initialMps }: MpSelectionStepProps) {
  const posthog = usePostHog();
  const [allMps] = useState<MP[]>(initialMps);
  const [filteredMps, setFilteredMps] = useState<MP[]>(initialMps);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedMp, setSelectedMp] = useState<MP | null>(null);

  const form = useForm<SetupStep3Data>({
    resolver: zodResolver(setupStep3Schema),
    defaultValues: {
      selectedMpId: initialData?.selectedMpId,
    },
  });

  // Filter MPs based on search term
  const filterMps = useCallback((search: string) => {
    if (!search.trim()) {
      setFilteredMps(allMps);
      return;
    }
    
    const filtered = allMps.filter(mp => 
      // Search by display name
      (mp.display_name?.toLowerCase() || '').includes(search.toLowerCase()) ||
      // Search by party abbreviation (e.g., "Lab", "Con")
      (mp.party_abbreviation?.toLowerCase() || '').includes(search.toLowerCase()) ||
      // Search by constituency name
      (mp.constituency_name?.toLowerCase() || '').includes(search.toLowerCase()) ||
      // Search by member ID (convert to string for searching)
      mp.member_id?.toString().includes(search) ||
      // Search by full party name if available in the data
      (mp.party_name?.toLowerCase() || '').includes(search.toLowerCase())
    );
    setFilteredMps(filtered);
  }, [allMps]);

  // Initialize filtered MPs
  useEffect(() => {
    setFilteredMps(allMps);
  }, [allMps]);

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      filterMps(searchTerm);
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [searchTerm, allMps, filterMps]);

  const handleMpSelect = (mp: MP) => {
    // Track MP selection
    posthog.capture("setup_mp_selected", {
      mp_id: mp.member_id,
      mp_name: mp.display_name,
      mp_party: mp.party_abbreviation,
      mp_constituency: mp.constituency_name,
    });

    setSelectedMp(mp);
    form.setValue("selectedMpId", mp.member_id);
    form.clearErrors("selectedMpId");
  };

  const onSubmit = (data: SetupStep3Data) => {
    onNext(data);
  };

  const getPartyColor = (party: string) => {
    const partyColors: Record<string, string> = {
      "Lab": "bg-red-500",
      "Con": "bg-blue-500", 
      "SNP": "bg-yellow-500",
      "LD": "bg-orange-500",
      "PC": "bg-green-500",
      "Green": "bg-green-600",
      "DUP": "bg-orange-600",
      "SF": "bg-green-700",
    };
    return partyColors[party] || "bg-gray-500";
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl font-semibold">Follow an MP</CardTitle>
        <CardDescription>
          Get notified when your chosen MP speaks in Parliament
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="Search by name, party, constituency, or member ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
                disabled={isLoading}
              />
            </div>

            {/* Selected MP */}
            {selectedMp && (
              <div className="p-4 border-2 border-primary rounded-lg bg-primary/5">
                <div className="flex items-center space-x-4">
                  <SmartAvatar
                    mpPortraitUrl={selectedMp.parliament_member_portraits?.[0]?.image_url}
                    firstName={selectedMp.display_name?.split(' ')?.[0]}
                    lastName={selectedMp.display_name?.split(' ')?.slice(1).join(' ')}
                    isMP={true}
                    className="h-12 w-12"
                    enableLazyLoading={true}
                  />
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <h3 className="font-semibold text-foreground">
                        {selectedMp.display_name}
                      </h3>
                      <Check className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex items-center space-x-2 mt-1">
                      <Badge 
                        className={cn(
                          "text-xs text-white",
                          getPartyColor(selectedMp.party_abbreviation)
                        )}
                      >
                        {selectedMp.party_abbreviation}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {selectedMp.constituency_name}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <FormField
              control={form.control}
              name="selectedMpId"
              render={() => (
                <FormItem>
                  <FormLabel className="sr-only">Selected MP</FormLabel>
                  <FormMessage 
                    role="alert" 
                    aria-live="polite"
                  />
                </FormItem>
              )}
            />

            {/* MP Grid */}
            <div className="max-h-96 overflow-y-auto">
              {filteredMps.length === 0 ? (
                <div className="text-center py-8 space-y-2">
                  <p className="text-muted-foreground">
                    {searchTerm ? "No MPs found matching your search." : "No MPs available at the moment."}
                  </p>
                  {searchTerm && (
                    <p className="text-xs text-muted-foreground">Try a different search term or browse all MPs.</p>
                  )}
                  {!searchTerm && allMps.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      The MP database is currently being populated. Please contact support if this persists.
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">Please select an MP to continue. You can change this later from your dashboard.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {filteredMps.map((mp) => (
                    <button
                      key={mp.member_id}
                      type="button"
                      onClick={() => handleMpSelect(mp)}
                      className={cn(
                        "flex items-center space-x-3 p-3 rounded-lg border text-left transition-all hover:bg-muted/50",
                        selectedMp?.member_id === mp.member_id
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-border"
                      )}
                      disabled={isLoading}
                    >
                      <SmartAvatar
                        mpPortraitUrl={mp.parliament_member_portraits?.[0]?.image_url}
                        firstName={mp.display_name?.split(' ')?.[0]}
                        lastName={mp.display_name?.split(' ')?.slice(1).join(' ')}
                        isMP={true}
                        className="h-10 w-10 text-xs"
                        enableLazyLoading={true}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-foreground truncate">
                          {mp.display_name}
                        </p>
                        <div className="flex items-center space-x-2 mt-1">
                          <Badge 
                            variant="outline"
                            className={cn(
                              "text-xs",
                              getPartyColor(mp.party_abbreviation),
                              "text-white border-transparent"
                            )}
                          >
                            {mp.party_abbreviation}
                          </Badge>
                          <span className="text-xs text-muted-foreground truncate">
                            {mp.constituency_name}
                          </span>
                        </div>
                      </div>
                      {selectedMp?.member_id === mp.member_id && (
                        <Check className="h-4 w-4 text-primary flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Navigation Buttons */}
            <div className="flex justify-between pt-4">
              <Button 
                type="button" 
                variant="outline" 
                onClick={onPrevious}
                disabled={isLoading}
              >
                Previous
              </Button>
              
              <Button 
                type="submit"
                disabled={isLoading || !selectedMp}
                className="w-full sm:w-auto"
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Complete Setup
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}