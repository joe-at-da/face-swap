"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Users,
  Search,
  User,
  MapPin,
  Building,
  Save,
  Loader2
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface MP {
  member_id: number;
  display_name: string;
  party_name: string | null;
  party_abbreviation: string | null;
  constituency_name: string | null;
  house_name: string | null;
}

interface Party {
  abbreviation: string;
  name: string;
}

interface CurrentMP {
  member_id: number;
  display_name: string;
  party_name: string | null;
  party_abbreviation: string | null;
  constituency_name: string | null;
}

interface MPFollowingSettingsProps {
  currentMP: CurrentMP | null;
  onMPUpdate: (newMP: CurrentMP) => void;
}

export function MPFollowingSettings({ currentMP, onMPUpdate }: MPFollowingSettingsProps) {
  const [isChanging, setIsChanging] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedParty, setSelectedParty] = useState<string>("");
  const [selectedMP, setSelectedMP] = useState<MP | null>(null);
  
  const [availableMPs, setAvailableMPs] = useState<MP[]>([]);
  const [parties, setParties] = useState<Party[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch available MPs
  useEffect(() => {
    const fetchMPs = async () => {
      setIsLoading(true);
      
      try {
        const params = new URLSearchParams();
        if (searchTerm.length > 1) params.append("search", searchTerm);
        if (selectedParty) params.append("party", selectedParty);

        const response = await fetch(`/api/settings/mp-following?${params}`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch MPs");
        }

        setAvailableMPs(data.data.mps || []);
        setParties(data.data.parties || []);
      } catch (error) {
        console.error("Error fetching MPs:", error);
        toast.error("Failed to load available MPs");
      } finally {
        setIsLoading(false);
      }
    };

    if (isChanging) {
      fetchMPs();
    }
  }, [isChanging, searchTerm, selectedParty]);

  const handleStartChanging = () => {
    setIsChanging(true);
    setSelectedMP(null);
    setSearchTerm("");
    setSelectedParty("");
  };

  const handleCancel = () => {
    setIsChanging(false);
    setSelectedMP(null);
    setSearchTerm("");
    setSelectedParty("");
  };

  const handleSave = async () => {
    if (!selectedMP) {
      toast.error("Please select an MP to follow");
      return;
    }

    setIsSaving(true);

    try {
      const response = await fetch("/api/settings/mp-following", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          member_id: selectedMP.member_id,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to update MP following");
      }

      // Update parent component
      onMPUpdate({
        member_id: selectedMP.member_id,
        display_name: selectedMP.display_name,
        party_name: selectedMP.party_name,
        party_abbreviation: selectedMP.party_abbreviation,
        constituency_name: selectedMP.constituency_name,
      });

      setIsChanging(false);
      toast.success(data.message || "Successfully updated MP following");
    } catch (error) {
      console.error("Error updating MP following:", error);
      toast.error(error instanceof Error ? error.message : "Failed to update MP following");
    } finally {
      setIsSaving(false);
    }
  };

  const filteredMPs = availableMPs.filter(mp => {
    if (!searchTerm) return true;
    const searchLower = searchTerm.toLowerCase();
    return mp.display_name.toLowerCase().includes(searchLower) ||
           mp.party_name?.toLowerCase().includes(searchLower) ||
           mp.constituency_name?.toLowerCase().includes(searchLower);
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Following MP
          </CardTitle>
          
          {!isChanging ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartChanging}
            >
              Change MP
            </Button>
          ) : (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancel}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={isSaving || !selectedMP}
                className="flex items-center gap-2"
              >
                {isSaving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Save Changes
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {!isChanging ? (
          // Current MP Display
          <div className="space-y-4">
            {currentMP ? (
              <div className="border rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{currentMP.display_name}</span>
                      {currentMP.party_abbreviation && (
                        <Badge variant="outline">
                          {currentMP.party_abbreviation}
                        </Badge>
                      )}
                    </div>
                    
                    {currentMP.party_name && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground ml-6">
                        <Building className="h-3 w-3" />
                        <span>{currentMP.party_name}</span>
                      </div>
                    )}

                    {currentMP.constituency_name && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground ml-6">
                        <MapPin className="h-3 w-3" />
                        <span>{currentMP.constituency_name}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-muted-foreground">
                <Users className="h-8 w-8 mx-auto mb-2" />
                <p>No MP currently followed</p>
              </div>
            )}

            <div className="text-sm text-muted-foreground bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p>
                You&apos;ll receive notifications when your followed MP speaks in Parliament, 
                and new clips featuring them will be available for you to create.
              </p>
            </div>
          </div>
        ) : (
          // MP Selection Interface
          <div className="space-y-4">
            {/* Search and Filter Controls */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="mp-search">Search MPs</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="mp-search"
                    placeholder="Search by name, party, or constituency..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="party-filter">Filter by Party</Label>
                <Select value={selectedParty} onValueChange={setSelectedParty}>
                  <SelectTrigger>
                    <SelectValue placeholder="All parties" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All parties</SelectItem>
                    {parties.map((party) => (
                      <SelectItem key={party.abbreviation} value={party.abbreviation}>
                        {party.abbreviation} - {party.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* MPs List */}
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : filteredMPs.length > 0 ? (
                filteredMPs.map((mp) => (
                  <div
                    key={mp.member_id}
                    className={cn(
                      "border rounded-lg p-3 cursor-pointer transition-colors hover:bg-muted/50",
                      selectedMP?.member_id === mp.member_id && "bg-primary/10 border-primary"
                    )}
                    onClick={() => setSelectedMP(mp)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{mp.display_name}</span>
                          {mp.party_abbreviation && (
                            <Badge variant="outline" className="text-xs">
                              {mp.party_abbreviation}
                            </Badge>
                          )}
                        </div>
                        
                        <div className="text-sm text-muted-foreground">
                          {mp.party_name && (
                            <span>{mp.party_name}</span>
                          )}
                          {mp.party_name && mp.constituency_name && " • "}
                          {mp.constituency_name && (
                            <span>{mp.constituency_name}</span>
                          )}
                        </div>
                      </div>

                      {selectedMP?.member_id === mp.member_id && (
                        <div className="h-4 w-4 rounded-full bg-primary" />
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <Users className="h-6 w-6 mx-auto mb-2" />
                  <p>No MPs found matching your search</p>
                </div>
              )}
            </div>

            {selectedMP && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-green-800">
                  <User className="h-4 w-4" />
                  <span className="text-sm font-medium">
                    Selected: {selectedMP.display_name}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}