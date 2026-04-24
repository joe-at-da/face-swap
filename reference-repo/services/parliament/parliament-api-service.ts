import {
  ParliamentMembersSearchResponse,
  MemberContact,
  MemberPortraits,
  ParliamentMember,
  Portrait,
} from "./parliament-api-types";

const BASE_URL = "https://members-api.parliament.uk/api";
const BURST_LIMIT = 4;
const MIN_REQUEST_INTERVAL = 500;
const RETRY_DELAY_BASE = 3000;
const REQUEST_TIMEOUT = 15000; // 15 second timeout

export class ParliamentApiService {
  private requestTimestamps: number[] = []; // Track request timestamps for burst limiting
  private lastRequestTime = 0;
  private consecutiveErrors = 0;
  private maxRetries = 3;

  private async delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private async waitForRateLimit(): Promise<void> {
    const now = Date.now();

    // Clean old timestamps (older than 1 second for burst calculation)
    this.requestTimestamps = this.requestTimestamps.filter(
      (timestamp) => now - timestamp < 1000
    );

    // Check burst limit
    if (this.requestTimestamps.length >= BURST_LIMIT) {
      const oldestInBurst = this.requestTimestamps[0];
      const waitTime = 1000 - (now - oldestInBurst) + 5;
      await this.delay(waitTime);
      return this.waitForRateLimit(); // Recheck after waiting
    }

    // Check RPS limit (minimum interval between requests)
    const timeSinceLastRequest = now - this.lastRequestTime;
    if (timeSinceLastRequest < MIN_REQUEST_INTERVAL) {
      const waitTime = MIN_REQUEST_INTERVAL - timeSinceLastRequest;
      await this.delay(waitTime);
    }

    // Record this request
    this.lastRequestTime = Date.now();
    this.requestTimestamps.push(this.lastRequestTime);
  }

  private async fetchWithRetry<T>(url: string, retries = 3): Promise<T> {
    for (let i = 0; i < retries; i++) {
      try {
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

        const response = await fetch(url, {
          headers: {
            Accept: "application/json",
            "User-Agent": "Parliament-Sync-Service/1.0",
          },
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          if (response.status === 429) {
            await this.delay(RETRY_DELAY_BASE * Math.pow(2, i + 1));
            continue;
          }
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        await this.waitForRateLimit();

        return data as T;
      } catch (error) {
        console.error(`Attempt ${i + 1} failed:`, error);

        if (i === retries - 1) {
          throw error;
        }

        const backoffDelay = RETRY_DELAY_BASE * Math.pow(2, i);
        await this.delay(backoffDelay);
      }
    }

    throw new Error("All retry attempts failed");
  }

  async getCurrentMembers(
    house?: number,
    skip = 0,
    take = 20 // Parliament API only returns max 20 items per request
  ): Promise<ParliamentMembersSearchResponse> {
    const params = new URLSearchParams({
      IsCurrentMember: "true",
      skip: skip.toString(),
      take: take.toString(),
    });

    if (house) {
      params.append("House", house.toString());
    }

    const url = `${BASE_URL}/Members/Search?${params.toString()}`;

    const response = await this.fetchWithRetry<ParliamentMembersSearchResponse>(
      url
    );

    return response;
  }

  async getAllCurrentMembers(): Promise<ParliamentMember[]> {
    const allMembers: ParliamentMember[] = [];

    const allHousesMembers = await this.fetchAllCurrentMembersForHouse(
      undefined
    );
    allMembers.push(...allHousesMembers);

    // If we got less than expected, try fetching each house separately
    if (allMembers.length < 600) {
      allMembers.length = 0;

      const commonsMembers = await this.fetchAllCurrentMembersForHouse(1);
      allMembers.push(...commonsMembers);

      const lordsMembers = await this.fetchAllCurrentMembersForHouse(2);
      allMembers.push(...lordsMembers);
    }

    // Final validation - check for any members without IDs
    const membersWithoutId = allMembers.filter((m) => !m.id);
    if (membersWithoutId.length > 0) {
      console.error(
        `Found ${membersWithoutId.length} members without ID:`,
        membersWithoutId
      );
    }

    // Remove duplicates based on member ID
    const uniqueMembers = allMembers.filter(
      (member, index, self) =>
        index === self.findIndex((m) => m.id === member.id)
    );

    return uniqueMembers;
  }

  private async fetchAllCurrentMembersForHouse(
    house?: number
  ): Promise<ParliamentMember[]> {
    const allMembers: ParliamentMember[] = [];
    let skip = 0;
    const take = 20; // Parliament API only returns 20 items max per request

    while (true) {
      const response = await this.getCurrentMembers(house, skip, take);

      if (response.items.length === 0) {
        break;
      }

      // Extract the actual member data from the wrapper objects
      const extractedMembers = response.items.map((item) => item.value);
      allMembers.push(...extractedMembers);

      // If we've fetched all available items, break
      if (allMembers.length >= response.totalResults) {
        break;
      }

      skip += take; // Increment by 20, not 100
      // Rate limiting handled by fetchWithRetry method

      // Safety check to prevent infinite loops
      if (skip > 10000) {
        console.error(
          `Safety limit reached for house ${
            house || "all"
          } - stopping at 10,000 skip to prevent infinite loop`
        );
        break;
      }
    }

    return allMembers;
  }

  async getMemberContact(memberId: number): Promise<MemberContact> {
    const url = `${BASE_URL}/Members/${memberId}/Contact`;
    return this.fetchWithRetry<MemberContact>(url);
  }

  // Specialized contact method with extra conservative rate limiting
  async getMemberContactSafe(memberId: number): Promise<MemberContact> {
    // Add extra delay before contact requests to be extra safe with rate limits
    await this.delay(150); // 150ms delay before each contact request

    const url = `${BASE_URL}/Members/${memberId}/Contact`;
    return this.fetchWithRetry<MemberContact>(url);
  }

  async getMemberPortraits(memberId: number): Promise<MemberPortraits> {
    // Generate all crop types - we just need the URLs, no need to fetch
    const cropTypes = [0, 1, 2, 3]; // All available crop types
    const webVersion = false; // Only full resolution as requested
    const allPortraits: Portrait[] = [];

    for (const cropType of cropTypes) {
      const url = `${BASE_URL}/Members/${memberId}/Portrait?cropType=${cropType}&webVersion=${webVersion}`;

      // Create a Portrait object with the URL - no need to fetch
      const portrait: Portrait = {
        id: parseInt(`${memberId}${cropType}${webVersion ? "1" : "0"}`),
        description: `Portrait of member ${memberId} (crop type ${cropType}, ${
          webVersion ? "web" : "full"
        } version)`,
        isDefault: cropType === 1, // Crop type 1 is primary
        files: [
          {
            id: parseInt(`${memberId}${cropType}${webVersion ? "1" : "0"}01`),
            url: url,
            typeId: cropType,
            typeDescription: `Crop Type ${cropType} (${
              webVersion ? "Web" : "Full"
            } Resolution)`,
          },
        ],
      };
      allPortraits.push(portrait);
    }

    return {
      value: allPortraits,
      links: [],
    };
  }

  async getMemberContactsWithRetry(
    memberIds: number[]
  ): Promise<Map<number, MemberContact>> {
    const contacts = new Map<number, MemberContact>();
    const failedMembers: number[] = [];

    const batchSize = 1;
    for (let i = 0; i < memberIds.length; i += batchSize) {
      const batch = memberIds.slice(i, i + batchSize);

      // Process contacts sequentially to avoid burst limits
      for (const memberId of batch) {
        try {
          const contact = await this.getMemberContactSafe(memberId);
          contacts.set(memberId, contact);
        } catch (error) {
          console.error(
            `✗ Failed to fetch contact for member ${memberId}:`,
            error
          );
          failedMembers.push(memberId);
        }

        // Add extra delay between sequential requests to help with rate limiting
        if (i + 1 < memberIds.length) {
          await this.delay(100); // 100ms delay between individual contact requests
        }
      }

      // Add longer delay between batches
      if (i + batchSize < memberIds.length) {
        await this.delay(200); // 200ms delay between batches
      }
    }

    // Retry failed members with exponential backoff
    if (failedMembers.length > 0) {
      for (const memberId of failedMembers) {
        try {
          await this.delay(500);
          const contact = await this.getMemberContactSafe(memberId);
          contacts.set(memberId, contact);
        } catch (error) {
          console.error(`✗ Retry failed for member ${memberId}:`, error);
        }
      }
    }

    return contacts;
  }

  async getMemberPortraitsWithRetry(
    memberIds: number[]
  ): Promise<Map<number, MemberPortraits>> {
    const portraits = new Map<number, MemberPortraits>();

    // Since we're just generating URLs, we can process all members quickly
    for (const memberId of memberIds) {
      try {
        const portrait = await this.getMemberPortraits(memberId);
        portraits.set(memberId, portrait);
      } catch (error) {
        console.error(
          `Failed to generate portraits for member ${memberId}:`,
          error
        );
      }
    }

    return portraits;
  }

  // Rate limiting is now handled by the waitForRateLimit() method
}
