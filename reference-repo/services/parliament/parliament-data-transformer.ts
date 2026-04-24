import {
  ParliamentMember,
  ContactDetail,
  Portrait,
  ParliamentMemberRecord,
  ParliamentMemberContactRecord,
  ParliamentMemberPortraitRecord,
} from "./parliament-api-types";

export class ParliamentDataTransformer {
  static transformMember(member: ParliamentMember): ParliamentMemberRecord {
    // Since we're fetching with IsCurrentMember=true, all members are current
    const isCurrentMember = true;

    // Member is eligible if they have active house membership
    const hasActiveMembership =
      member.latestHouseMembership &&
      (!member.latestHouseMembership.membershipEndDate ||
        new Date(member.latestHouseMembership.membershipEndDate) > new Date());

    const isEligible = hasActiveMembership;

    return {
      member_id: member.id,
      display_name: member.nameDisplayAs,
      given_name: this.extractGivenName(member.nameDisplayAs),
      family_name: this.extractFamilyName(member.nameDisplayAs),
      full_title: member.nameFullTitle,
      list_as: member.nameListAs,
      is_current_member: isCurrentMember, // All fetched members are current (IsCurrentMember=true)
      is_eligible: isEligible, // Inferred from active membership status
      house_id: member.latestHouseMembership?.house,
      house_name: this.getHouseName(member.latestHouseMembership?.house),
      party_id: member.latestParty?.id,
      party_name: member.latestParty?.name,
      party_abbreviation: member.latestParty?.abbreviation,
      party_background_colour: member.latestParty?.backgroundColour,
      party_foreground_colour: member.latestParty?.foregroundColour,
      party_is_lord_spiritual: member.latestParty?.isLordSpiritual,
      party_is_independent: member.latestParty?.isIndependent,
      constituency_id: member.latestHouseMembership?.membershipFromId,
      constituency_name: member.latestHouseMembership?.membershipFrom,
      constituency_start_date:
        member.latestHouseMembership?.membershipStartDate,
      constituency_end_date: member.latestHouseMembership?.membershipEndDate,
      membership_start_date: member.latestHouseMembership?.membershipStartDate,
      membership_end_date: member.latestHouseMembership?.membershipEndDate,
      membership_start_reason: undefined, // Not available in search API
      membership_end_reason: member.latestHouseMembership?.membershipEndReason,
      lords_membership_type_id: undefined, // Would need additional API call
      lords_membership_type: undefined, // Would need additional API call
      date_of_birth: undefined, // Not available in search API
      date_of_death: undefined, // Not available in search API
      gender: this.mapGender(member.gender),
    };
  }

  static transformContacts(
    memberId: number,
    contacts: ContactDetail[]
  ): ParliamentMemberContactRecord[] {
    return contacts.map((contact) => ({
      member_id: memberId,
      contact_type: this.mapContactType(contact.typeDescription, contact.type),
      contact_type_id: contact.typeId,
      is_primary: contact.isPreferred,
      is_physical: !contact.isWebAddress,
      address_line_1: contact.line1,
      address_line_2: contact.line2,
      address_line_3: contact.line3,
      address_line_4: contact.line4,
      address_line_5: contact.line5,
      postcode: contact.postcode,
      email: contact.email,
      phone: contact.phone,
      fax: contact.fax,
      website_url: contact.isWebAddress ? contact.line1 : undefined,
      website_display_as: contact.isWebAddress
        ? contact.typeDescription || contact.type
        : undefined,
      twitter_url: this.extractSocialMediaUrl(contact, "twitter"),
      facebook_url: this.extractSocialMediaUrl(contact, "facebook"),
      instagram_url: this.extractSocialMediaUrl(contact, "instagram"),
      linkedin_url: this.extractSocialMediaUrl(contact, "linkedin"),
      youtube_url: this.extractSocialMediaUrl(contact, "youtube"),
      note: contact.notes,
    }));
  }

  static transformPortraits(
    memberId: number,
    portraits: Portrait[]
  ): ParliamentMemberPortraitRecord[] {
    const records: ParliamentMemberPortraitRecord[] = [];

    portraits.forEach((portrait) => {
      portrait.files.forEach((file) => {
        // Extract web version from the URL
        const urlParams = new URLSearchParams(file.url.split("?")[1]);
        const webVersion = urlParams.get("webVersion") === "true";

        records.push({
          member_id: memberId,
          image_url: file.url,
          crop_type: file.typeId, // 0, 1, 2, or 3
          web_version: webVersion, // Extract from URL parameter
          is_primary: portrait.isDefault, // crop_type 0 full resolution is primary
        });
      });
    });

    return records;
  }

  // Helper methods
  private static extractGivenName(displayName: string): string | undefined {
    if (!displayName) return undefined;
    const parts = displayName.split(" ");
    return parts.length > 1 ? parts[0] : undefined;
  }

  private static extractFamilyName(displayName: string): string | undefined {
    if (!displayName) return undefined;
    const parts = displayName.split(" ");
    return parts.length > 1 ? parts.slice(1).join(" ") : displayName;
  }

  private static getHouseName(
    houseId?: number
  ): "Commons" | "Lords" | undefined {
    switch (houseId) {
      case 1:
        return "Commons";
      case 2:
        return "Lords";
      default:
        return undefined;
    }
  }

  private static extractSocialMediaUrl(
    contact: ContactDetail,
    platform: string
  ): string | undefined {
    if (!contact.isWebAddress) return undefined;

    // Use typeDescription first, then fallback to type field
    const typeToCheck = contact.typeDescription || contact.type;
    if (!typeToCheck) return undefined;

    const lowerType = typeToCheck.toLowerCase();
    const lowerPlatform = platform.toLowerCase();

    if (lowerType.includes(lowerPlatform)) {
      return contact.line1;
    }

    return undefined;
  }

  private static mapGender(
    gender: string
  ): "M" | "F" | "Other" | "Unknown" | undefined {
    if (!gender) return undefined;

    const normalizedGender = gender.toLowerCase().trim();
    switch (normalizedGender) {
      case "m":
      case "male":
        return "M";
      case "f":
      case "female":
        return "F";
      case "other":
        return "Other";
      default:
        return "Unknown";
    }
  }

  private static mapContactType(
    typeDescription: string | null | undefined,
    type?: string
  ):
    | "Parliamentary"
    | "Constituency"
    | "Website"
    | "Social Media"
    | "Email"
    | "Phone"
    | "Address"
    | "Other"
    | undefined {
    // Use typeDescription first, then fallback to type field
    const typeToCheck = typeDescription || type;
    if (!typeToCheck) return "Other";

    const normalizedType = typeToCheck.toLowerCase().trim();

    if (normalizedType.includes("parliamentary")) {
      return "Parliamentary";
    }
    if (normalizedType.includes("constituency")) {
      return "Constituency";
    }
    if (normalizedType.includes("website") || normalizedType.includes("web")) {
      return "Website";
    }
    if (
      normalizedType.includes("social") ||
      normalizedType.includes("twitter") ||
      normalizedType.includes("facebook") ||
      normalizedType.includes("instagram") ||
      normalizedType.includes("linkedin") ||
      normalizedType.includes("youtube")
    ) {
      return "Social Media";
    }
    if (normalizedType.includes("email") || normalizedType.includes("e-mail")) {
      return "Email";
    }
    if (
      normalizedType.includes("phone") ||
      normalizedType.includes("telephone") ||
      normalizedType.includes("mobile") ||
      normalizedType.includes("fax")
    ) {
      return "Phone";
    }
    if (
      normalizedType.includes("address") ||
      normalizedType.includes("postal")
    ) {
      return "Address";
    }

    return "Other";
  }
}
