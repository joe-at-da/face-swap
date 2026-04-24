// TypeScript types for UK Parliament Members API

export interface ParliamentMember {
  id: number;
  nameListAs: string;
  nameDisplayAs: string;
  nameFullTitle: string;
  nameAddressAs: string;
  latestParty?: {
    id: number;
    name: string;
    abbreviation: string;
    backgroundColour: string;
    foregroundColour: string;
    isLordSpiritual: boolean;
    isIndependent: boolean;
  };
  gender: string;
  latestHouseMembership?: {
    membershipFrom: string;
    membershipFromId: number;
    house: number;
    membershipStartDate: string;
    membershipEndDate?: string;
    membershipEndReason?: string;
  };
  thumbnailUrl?: string;
}

export interface ParliamentMemberWrapper {
  value: ParliamentMember;
  links: Array<{
    rel: string;
    href: string;
    method: string;
  }>;
}

export interface ParliamentMembersSearchResponse {
  items: ParliamentMemberWrapper[];
  itemsPerPage: number;
  totalResults: number;
  links: Array<{
    rel: string;
    href: string;
    method: string;
  }>;
}

export interface ContactDetail {
  id?: number;
  type: string;
  typeDescription: string | null;
  typeId: number;
  isPreferred: boolean;
  isWebAddress: boolean;
  line1?: string;
  line2?: string;
  line3?: string;
  line4?: string;
  line5?: string;
  postcode?: string;
  phone?: string;
  fax?: string;
  email?: string;
  addressTypeId?: number;
  notes?: string;
}

export interface MemberContact {
  value: ContactDetail[];
  links: Array<{
    rel: string;
    href: string;
    method: string;
  }>;
}

export interface Portrait {
  id: number;
  description: string;
  isDefault: boolean;
  files: Array<{
    id: number;
    url: string;
    typeId: number;
    typeDescription: string;
  }>;
}

export interface MemberPortraits {
  value: Portrait[];
  links: Array<{
    rel: string;
    href: string;
    method: string;
  }>;
}

// Database record types (for inserting into Supabase)
export interface ParliamentMemberRecord {
  member_id: number;
  display_name?: string;
  given_name?: string;
  family_name?: string;
  full_title?: string;
  list_as?: string;
  is_current_member?: boolean;
  is_eligible?: boolean;
  house_id?: number;
  house_name?: "Commons" | "Lords";
  party_id?: number;
  party_name?: string;
  party_abbreviation?: string;
  party_background_colour?: string;
  party_foreground_colour?: string;
  party_is_lord_spiritual?: boolean;
  party_is_independent?: boolean;
  constituency_id?: number;
  constituency_name?: string;
  constituency_start_date?: string;
  constituency_end_date?: string;
  membership_start_date?: string;
  membership_end_date?: string;
  membership_start_reason?: string;
  membership_end_reason?: string;
  lords_membership_type_id?: number;
  lords_membership_type?: string;
  date_of_birth?: string;
  date_of_death?: string;
  gender?: "M" | "F" | "Other" | "Unknown";
}

export interface ParliamentMemberContactRecord {
  member_id: number;
  contact_type?:
    | "Parliamentary"
    | "Constituency"
    | "Website"
    | "Social Media"
    | "Email"
    | "Phone"
    | "Address"
    | "Other";
  contact_type_id?: number;
  is_primary?: boolean;
  is_physical?: boolean;
  address_line_1?: string;
  address_line_2?: string;
  address_line_3?: string;
  address_line_4?: string;
  address_line_5?: string;
  postcode?: string;
  email?: string;
  phone?: string;
  fax?: string;
  website_url?: string;
  website_display_as?: string;
  twitter_url?: string;
  facebook_url?: string;
  instagram_url?: string;
  linkedin_url?: string;
  youtube_url?: string;
  note?: string;
}

export interface ParliamentMemberPortraitRecord {
  member_id: number;
  image_url: string;
  crop_type: number; // 0, 1, 2, or 3
  web_version?: boolean; // Always false for full resolution
  is_primary?: boolean; // crop_type 0 is primary
}

export interface SyncStatusRecord {
  id?: string;
  sync_type: "members" | "contacts" | "portraits" | "cron_trigger";
  last_sync_at?: string | null;
  next_sync_at?: string | null;
  status: "pending" | "running" | "completed" | "failed" | null;
  records_processed?: number | null;
  records_failed?: number | null;
  error_message?: string | null;
  duration_seconds?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}
