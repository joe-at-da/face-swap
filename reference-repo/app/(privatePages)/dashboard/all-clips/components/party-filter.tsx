"use client";

import { useState } from "react";
import { Check, ChevronsUpDown, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import type { PartyOption } from "@/types/parliament";

interface PartyFilterProps {
  parties: PartyOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

export default function PartyFilter({ parties, selected, onChange }: PartyFilterProps) {
  const [open, setOpen] = useState(false);

  const toggleParty = (partyName: string) => {
    if (selected.includes(partyName)) {
      onChange(selected.filter((p) => p !== partyName));
    } else {
      onChange([...selected, partyName]);
    }
  };

  const removeParty = (partyName: string) => {
    onChange(selected.filter((p) => p !== partyName));
  };

  return (
    <div className="flex flex-col gap-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full sm:w-[200px] justify-between"
          >
            {selected.length > 0
              ? `${selected.length} ${selected.length === 1 ? "party" : "parties"}`
              : "Filter by party"}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[280px] p-0" align="start">
          <Command>
            <CommandInput placeholder="Search parties..." />
            <CommandList>
              <CommandEmpty>No party found.</CommandEmpty>
              <CommandGroup>
                {parties.map((party) => (
                  <CommandItem
                    key={party.party_name}
                    value={party.party_name}
                    onSelect={() => toggleParty(party.party_name)}
                  >
                    <div className="flex items-center gap-2 flex-1">
                      <div
                        className="h-3 w-3 rounded-full shrink-0"
                        style={{
                          backgroundColor: party.party_background_colour
                            ? `#${party.party_background_colour}`
                            : "var(--muted)",
                        }}
                      />
                      <span className="truncate">{party.party_name}</span>
                      <span className="text-xs text-muted-foreground ml-auto">
                        {party.party_abbreviation}
                      </span>
                    </div>
                    {selected.includes(party.party_name) && (
                      <Check className="h-4 w-4 shrink-0" />
                    )}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((partyName) => {
            const party = parties.find((p) => p.party_name === partyName);
            return (
              <Badge
                key={partyName}
                variant="secondary"
                className="gap-1 pr-1"
                style={{
                  backgroundColor: party?.party_background_colour
                    ? `#${party.party_background_colour}20`
                    : undefined,
                  borderColor: party?.party_background_colour
                    ? `#${party.party_background_colour}`
                    : undefined,
                  borderWidth: 1,
                }}
              >
                <div
                  className="h-2 w-2 rounded-full"
                  style={{
                    backgroundColor: party?.party_background_colour
                      ? `#${party.party_background_colour}`
                      : "var(--muted)",
                  }}
                />
                <span className="text-xs">{party?.party_abbreviation || partyName}</span>
                <button
                  type="button"
                  onClick={() => removeParty(partyName)}
                  className="ml-0.5 rounded-sm hover:bg-muted p-0.5"
                  aria-label={`Remove ${partyName}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            );
          })}
          <button
            type="button"
            onClick={() => onChange([])}
            className="text-xs text-muted-foreground hover:text-foreground underline"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
