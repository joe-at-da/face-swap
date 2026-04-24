import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { ParliamentApiService } from "./parliament-api-service";
import { ParliamentDataTransformer } from "./parliament-data-transformer";
// Removed unused imports - all types are handled by the transformer
import { Database } from "@/supabaseTypes";

const DIGITALOCEAN_SPACES_FILTER = "%digitaloceanspaces.com%";

// Type definitions for the sync service
type ParliamentMemberInsert =
  Database["public"]["Tables"]["parliament_members"]["Insert"];
type ParliamentMemberUpdate =
  Database["public"]["Tables"]["parliament_members"]["Update"];

type ParliamentContactInsert =
  Database["public"]["Tables"]["parliament_member_contacts"]["Insert"];
type ParliamentContactUpdate =
  Database["public"]["Tables"]["parliament_member_contacts"]["Update"];

type ParliamentPortraitInsert =
  Database["public"]["Tables"]["parliament_member_portraits"]["Insert"];
type ParliamentPortraitUpdate =
  Database["public"]["Tables"]["parliament_member_portraits"]["Update"];

// Contact type for the getContactKey function
interface ContactForComparison {
  contact_type?: string | null;
  typeDescription?: string;
  typeId?: string | number;
  email?: string | null;
  phone?: string | null;
  line1?: string;
  fax?: string | null;
  website_url?: string | null;
  address_line_1?: string | null;
  id?: string;
}

// Configuration constants for memory-efficient processing
const MEMBER_CHUNK_SIZE = 50; // Process members in chunks of 50 for contacts/portraits
const UPDATE_BATCH_SIZE = 5; // Reduced from 20-25 to prevent CPU spikes
const BATCH_DELAY_MS = 50; // Delay between batches to allow GC

export class ParliamentSyncService {
  private supabase = supabaseAdminClient;
  private apiService = new ParliamentApiService();

  async syncAllData(): Promise<void> {
    try {
      await this.syncMembers();

      await this.syncMemberContacts();

      try {
        await this.syncMemberPortraits();
      } catch (error) {
        console.error(
          "Portrait sync failed but continuing with voting history:",
          error
        );
        await this.updateSyncStatus(
          "portraits",
          "failed",
          0,
          0,
          error as Error
        );
      }

    } catch (error) {
      console.error("Sync failed:", error);
      throw error;
    }
  }

  async syncSpecific(
    syncTypes: ("members" | "contacts" | "portraits")[]
  ): Promise<void> {
    try {
      for (const syncType of syncTypes) {
        switch (syncType) {
          case "members":
            await this.syncMembers();
            break;
          case "contacts":
            await this.syncMemberContacts();
            break;
          case "portraits":
            await this.syncMemberPortraits();
            break;
        }
      }

    } catch (error) {
      console.error("Specific sync failed:", error);
      throw error;
    }
  }

  async syncMembers(): Promise<void> {
    const startTime = Date.now();
    let recordsProcessed = 0;
    let recordsFailed = 0;

    try {
      await this.updateSyncStatus("members", "running");

      // Fetch all current members from API
      const members = await this.apiService.getAllCurrentMembers();

      // Get existing members from database
      const { data: existingMembers, error: fetchError } = await this.supabase
        .from("parliament_members")
        .select("*")
        .eq("is_deleted", false);

      if (fetchError) {
        throw new Error(
          `Failed to fetch existing members from database: ${fetchError.message}`
        );
      }

      const existingMembersArray = existingMembers || [];

      // Transform API data for comparison
      const now = new Date().toISOString();
      const apiMemberMap = new Map();

      members.forEach((member) => {
        const transformed = ParliamentDataTransformer.transformMember(member);
        apiMemberMap.set(transformed.member_id, {
          ...transformed,
          last_synced_at: now,
        });
      });

      // Process updates and insertions
      const existingMemberMap = new Map(
        existingMembersArray.map((m) => [m.member_id, m])
      );
      const toUpdate: (ParliamentMemberUpdate & { id: string })[] = [];
      const toInsert: ParliamentMemberInsert[] = [];

      // Check for updates and new records
      for (const [memberId, apiMember] of apiMemberMap) {
        const existingMember = existingMemberMap.get(memberId);

        if (existingMember) {
          // Compare relevant fields (excluding timestamps and IDs)
          if (this.hasMemberChanges(existingMember, apiMember)) {
            toUpdate.push({
              ...apiMember,
              id: existingMember.id, // Keep existing database ID
            });
          }
        } else {
          // New member
          toInsert.push(apiMember);
        }
      }

      // Check for deletions (members in DB but not in API)
      const toMarkDeleted: string[] = [];
      for (const existingMember of existingMembersArray) {
        if (!apiMemberMap.has(existingMember.member_id)) {
          toMarkDeleted.push(existingMember.id);
        }
      }

      // Execute updates in batches with reduced concurrency for memory efficiency
      if (toUpdate.length > 0) {
        for (let i = 0; i < toUpdate.length; i += UPDATE_BATCH_SIZE) {
          const batch = toUpdate.slice(i, i + UPDATE_BATCH_SIZE);

          const promises = batch.map(async (member) => {
            const { error } = await this.supabase
              .from("parliament_members")
              .update(member)
              .eq("id", member.id);

            if (error) {
              console.error(
                `Failed to update member ${member.member_id}:`,
                error
              );
              return { success: false };
            }
            return { success: true };
          });

          const results = await Promise.all(promises);
          const successCount = results.filter((r) => r.success).length;
          const failCount = results.length - successCount;

          recordsProcessed += successCount;
          recordsFailed += failCount;

          // Add delay between batches to prevent CPU spikes
          if (i + UPDATE_BATCH_SIZE < toUpdate.length) {
            await new Promise((resolve) => setTimeout(resolve, BATCH_DELAY_MS));
          }
        }
      }

      // Execute insertions (already batched)
      if (toInsert.length > 0) {
        const { error } = await this.supabase
          .from("parliament_members")
          .insert(toInsert);

        if (error) {
          console.error("Failed to insert new members:", error);
          recordsFailed += toInsert.length;
        } else {
          recordsProcessed += toInsert.length;
        }
      }

      // Mark deletions (already batched)
      if (toMarkDeleted.length > 0) {
        const { error } = await this.supabase
          .from("parliament_members")
          .update({
            is_deleted: true,
            deleted_at: now,
            last_synced_at: now,
          })
          .in("id", toMarkDeleted);

        if (error) {
          console.error("Failed to mark members as deleted:", error);
          recordsFailed += toMarkDeleted.length;
        } else {
          recordsProcessed += toMarkDeleted.length;
        }
      }

      // Clear large objects to help GC
      toUpdate.length = 0;
      toInsert.length = 0;
      toMarkDeleted.length = 0;

      const duration = Math.round((Date.now() - startTime) / 1000);
      await this.updateSyncStatus(
        "members",
        "completed",
        recordsProcessed,
        recordsFailed,
        undefined,
        duration
      );

    } catch (error) {
      const duration = Math.round((Date.now() - startTime) / 1000);
      await this.updateSyncStatus(
        "members",
        "failed",
        recordsProcessed,
        recordsFailed,
        error as Error,
        duration
      );
      throw error;
    }
  }

  async syncMemberContacts(): Promise<void> {
    const startTime = Date.now();
    let recordsProcessed = 0;
    let recordsFailed = 0;

    try {
      await this.updateSyncStatus("contacts", "running");

      // Get total count of members first
      const { count: totalMembers } = await this.supabase
        .from("parliament_members")
        .select("member_id", { count: "exact", head: true });

      if (!totalMembers || totalMembers === 0) {
        throw new Error("No members found in database. Run member sync first.");
      }

      // Process members in chunks to limit memory usage
      let chunkOffset = 0;

      while (chunkOffset < totalMembers) {

        const { data: memberChunk } = await this.supabase
          .from("parliament_members")
          .select("member_id")
          .order("member_id")
          .range(chunkOffset, chunkOffset + MEMBER_CHUNK_SIZE - 1);

        if (!memberChunk || memberChunk.length === 0) {
          break;
        }

        const chunkMemberIds = memberChunk.map((m) => m.member_id);

        const contactsMap = await this.apiService.getMemberContactsWithRetry(
          chunkMemberIds
        );

        for (const [memberId, contacts] of contactsMap) {
          try {
            const now = new Date().toISOString();

            // Get existing contacts for this member
            const { data: existingContacts } = await this.supabase
              .from("parliament_member_contacts")
              .select("*")
              .eq("member_id", memberId)
              .eq("is_deleted", false);

            if (!existingContacts) {
              console.error(
                `Failed to fetch existing contacts for member ${memberId}`
              );
              recordsFailed++;
              continue;
            }

            // Transform API contacts
            const apiContacts = ParliamentDataTransformer.transformContacts(
              memberId,
              contacts.value
            ).map((record) => ({
              ...record,
              last_synced_at: now,
            }));

            // Create maps for comparison (use contact_type + primary identifier as unique key)
            const getContactKey = (contact: ContactForComparison) => {
              // Use email as primary identifier if available
              if (contact.email)
                return `${
                  contact.contact_type || contact.typeDescription
                }-email-${contact.email}`;

              // Use phone as identifier if available
              if (contact.phone)
                return `${
                  contact.contact_type || contact.typeDescription
                }-phone-${contact.phone}`;

              // Use fax as identifier if available
              if (contact.fax)
                return `${
                  contact.contact_type || contact.typeDescription
                }-fax-${contact.fax}`;

              // Use website URL as identifier if available
              if (contact.website_url)
                return `${
                  contact.contact_type || contact.typeDescription
                }-website-${contact.website_url}`;

              // Use address line 1 as identifier (for transformed contacts)
              if (contact.address_line_1)
                return `${
                  contact.contact_type || contact.typeDescription
                }-address-${contact.address_line_1}`;

              // Use line1 as identifier (for raw API contacts)
              if (contact.line1)
                return `${
                  contact.contact_type || contact.typeDescription
                }-address-${contact.line1}`;

              // Fallback using type and id
              return `${contact.contact_type || contact.typeDescription}-${
                contact.id || contact.typeId || "unknown"
              }`;
            };

            const existingContactMap = new Map(
              existingContacts.map((c) => [getContactKey(c), c])
            );
            const apiContactMap = new Map(
              apiContacts.map((c) => [getContactKey(c), c])
            );

            const toUpdate: (ParliamentContactUpdate & { id: string })[] = [];
            const toInsert: ParliamentContactInsert[] = [];
            const toMarkDeleted: string[] = [];

            // Check for updates and new records
            for (const [contactKey, apiContact] of apiContactMap) {
              const existingContact = existingContactMap.get(contactKey);

              if (existingContact) {
                // Compare for changes
                if (this.hasContactChanges(existingContact, apiContact)) {
                  toUpdate.push({
                    ...apiContact,
                    id: existingContact.id,
                  });
                }
              } else {
                // New contact
                toInsert.push(apiContact);
              }
            }

            // Check for deletions
            for (const existingContact of existingContacts) {
              const contactKey = getContactKey(existingContact);
              if (!apiContactMap.has(contactKey)) {
                toMarkDeleted.push(existingContact.id);
              }
            }

            // Execute updates in smaller batches with delays to prevent CPU spikes
            if (toUpdate.length > 0) {
              for (let i = 0; i < toUpdate.length; i += UPDATE_BATCH_SIZE) {
                const batch = toUpdate.slice(i, i + UPDATE_BATCH_SIZE);

                const promises = batch.map(async (contact) => {
                  const { error } = await this.supabase
                    .from("parliament_member_contacts")
                    .update(contact)
                    .eq("id", contact.id);

                  if (error) {
                    console.error(
                      `Failed to update contact ${contact.id}:`,
                      error
                    );
                    return { success: false };
                  }
                  return { success: true };
                });

                const results = await Promise.all(promises);
                const successCount = results.filter((r) => r.success).length;
                const failCount = results.length - successCount;

                recordsProcessed += successCount;
                recordsFailed += failCount;

                // Add delay between batches
                if (i + UPDATE_BATCH_SIZE < toUpdate.length) {
                  await new Promise((resolve) =>
                    setTimeout(resolve, BATCH_DELAY_MS)
                  );
                }
              }
            }

            // Execute insertions (keep single batch for integrity)
            if (toInsert.length > 0) {
              const { error } = await this.supabase
                .from("parliament_member_contacts")
                .insert(toInsert);

              if (error) {
                console.error("Failed to insert new contacts:", error);
                recordsFailed += toInsert.length;
              } else {
                recordsProcessed += toInsert.length;
              }
            }

            // Mark deletions (keep single batch)
            if (toMarkDeleted.length > 0) {
              const { error } = await this.supabase
                .from("parliament_member_contacts")
                .update({
                  is_deleted: true,
                  deleted_at: now,
                  last_synced_at: now,
                })
                .in("id", toMarkDeleted);

              if (error) {
                console.error("Failed to mark contacts as deleted:", error);
                recordsFailed += toMarkDeleted.length;
              } else {
                recordsProcessed += toMarkDeleted.length;
              }
            }
          } catch (error) {
            console.error(
              `Failed to process contacts for member ${memberId}:`,
              error
            );
            recordsFailed += 1;
          }
        }

        contactsMap.clear();

        // Move to next chunk
        chunkOffset += MEMBER_CHUNK_SIZE;

        // Allow GC between chunks
        await new Promise((resolve) => setImmediate(resolve));
      }

      const duration = Math.round((Date.now() - startTime) / 1000);
      await this.updateSyncStatus(
        "contacts",
        "completed",
        recordsProcessed,
        recordsFailed,
        undefined,
        duration
      );

    } catch (error) {
      const duration = Math.round((Date.now() - startTime) / 1000);
      await this.updateSyncStatus(
        "contacts",
        "failed",
        recordsProcessed,
        recordsFailed,
        error as Error,
        duration
      );
      throw error;
    }
  }

  async syncMemberPortraits(): Promise<void> {
    const startTime = Date.now();
    let recordsProcessed = 0;
    let recordsFailed = 0;

    try {
      await this.updateSyncStatus("portraits", "running");

      // Get total count of members first
      const { count: totalMembers } = await this.supabase
        .from("parliament_members")
        .select("member_id", { count: "exact", head: true });

      if (!totalMembers || totalMembers === 0) {
        throw new Error("No members found in database. Run member sync first.");
      }

      // Process members in chunks to limit memory usage
      let chunkOffset = 0;

      while (chunkOffset < totalMembers) {

        const { data: memberChunk } = await this.supabase
          .from("parliament_members")
          .select("member_id")
          .order("member_id")
          .range(chunkOffset, chunkOffset + MEMBER_CHUNK_SIZE - 1);

        if (!memberChunk || memberChunk.length === 0) {
          break;
        }

        const chunkMemberIds = memberChunk.map((m) => m.member_id);

        const portraitsMap = await this.apiService.getMemberPortraitsWithRetry(
          chunkMemberIds
        );

        // Process each member's portraits in this chunk
        for (const [memberId, portraits] of portraitsMap) {
          try {
            const now = new Date().toISOString();

            // Get existing portraits for this member
            const { data: existingPortraits } = await this.supabase
              .from("parliament_member_portraits")
              .select("*")
              .eq("member_id", memberId)
              .eq("is_deleted", false)
              .not("image_url", "ilike", DIGITALOCEAN_SPACES_FILTER);

            if (!existingPortraits) {
              console.error(
                `Failed to fetch existing portraits for member ${memberId}`
              );
              recordsFailed++;
              continue;
            }

            // Transform API portraits
            const apiPortraits = ParliamentDataTransformer.transformPortraits(
              memberId,
              portraits.value
            ).map((record) => ({
              ...record,
              last_synced_at: now,
            }));

            // Create maps for comparison (use crop_type as unique key)
            const existingPortraitMap = new Map(
              existingPortraits.map((p) => [p.crop_type, p])
            );
            const apiPortraitMap = new Map(
              apiPortraits.map((p) => [p.crop_type, p])
            );

            const toUpdate: (ParliamentPortraitUpdate & { id: string })[] = [];
            const toInsert: ParliamentPortraitInsert[] = [];
            const toMarkDeleted: string[] = [];

            // Check for updates and new records
            for (const [cropType, apiPortrait] of apiPortraitMap) {
              const existingPortrait = existingPortraitMap.get(cropType);

              if (existingPortrait) {
                // Compare for changes
                if (this.hasPortraitChanges(existingPortrait, apiPortrait)) {
                  toUpdate.push({
                    ...apiPortrait,
                    id: existingPortrait.id,
                  });
                }
              } else {
                // New portrait
                toInsert.push(apiPortrait);
              }
            }

            // Check for deletions
            for (const existingPortrait of existingPortraits) {
              if (!apiPortraitMap.has(existingPortrait.crop_type)) {
                toMarkDeleted.push(existingPortrait.id);
              }
            }

            // Execute updates
            for (const portrait of toUpdate) {
              const { error } = await this.supabase
                .from("parliament_member_portraits")
                .update(portrait)
                .eq("id", portrait.id);

              if (error) {
                console.error(
                  `Failed to update portrait for member ${memberId}:`,
                  error
                );
                recordsFailed++;
              } else {
                recordsProcessed++;
              }
            }

            // Execute insertions
            if (toInsert.length > 0) {
              const { error } = await this.supabase
                .from("parliament_member_portraits")
                .insert(toInsert);

              if (error) {
                console.error(
                  `Failed to insert portraits for member ${memberId}:`,
                  error
                );
                recordsFailed += toInsert.length;
              } else {
                recordsProcessed += toInsert.length;
              }
            }

            // Mark deletions
            if (toMarkDeleted.length > 0) {
              const { error } = await this.supabase
                .from("parliament_member_portraits")
                .update({
                  is_deleted: true,
                  deleted_at: now,
                  last_synced_at: now,
                })
                .in("id", toMarkDeleted)
                .not("image_url", "ilike", DIGITALOCEAN_SPACES_FILTER);

              if (error) {
                console.error(
                  `Failed to mark portraits as deleted for member ${memberId}:`,
                  error
                );
                recordsFailed += toMarkDeleted.length;
              } else {
                recordsProcessed += toMarkDeleted.length;
              }
            }
          } catch (error) {
            console.error(
              `Failed to process portraits for member ${memberId}:`,
              error
            );
            recordsFailed += 1;
          }
        }

        portraitsMap.clear();

        // Move to next chunk
        chunkOffset += MEMBER_CHUNK_SIZE;

        // Allow GC between chunks
        await new Promise((resolve) => setImmediate(resolve));
      }

      const duration = Math.round((Date.now() - startTime) / 1000);
      await this.updateSyncStatus(
        "portraits",
        "completed",
        recordsProcessed,
        recordsFailed,
        undefined,
        duration
      );

    } catch (error) {
      const duration = Math.round((Date.now() - startTime) / 1000);
      await this.updateSyncStatus(
        "portraits",
        "failed",
        recordsProcessed,
        recordsFailed,
        error as Error,
        duration
      );
      throw error;
    }
  }

  // Helper methods for comparing data changes
  private hasMemberChanges(
    existing: Record<string, unknown>,
    api: Record<string, unknown>
  ): boolean {
    const fieldsToCompare = [
      "display_as",
      "list_as",
      "full_title",
      "layer_name",
      "member_from",
      "house_name",
      "member_start_date",
      "member_end_date",
      "party_name",
      "party_id",
      "party_colour",
      "party_abbreviation",
      "status_is_active",
      "status_description",
      "status_start_date",
      "status_end_date",
      "gender",
    ];

    return fieldsToCompare.some((field) => existing[field] !== api[field]);
  }

  private hasContactChanges(
    existing: Record<string, unknown>,
    api: Record<string, unknown>
  ): boolean {
    const fieldsToCompare = [
      "contact_type",
      "type_description",
      "type_id",
      "is_preferred",
      "is_web_address",
      "value",
      "note",
    ];

    return fieldsToCompare.some((field) => existing[field] !== api[field]);
  }

  private hasPortraitChanges(
    existing: Record<string, unknown>,
    api: Record<string, unknown>
  ): boolean {
    const fieldsToCompare = ["crop_type", "portrait_url"];

    return fieldsToCompare.some((field) => existing[field] !== api[field]);
  }

  private async updateSyncStatus(
    syncType: "members" | "contacts" | "portraits" | "cron_trigger",
    status: "pending" | "running" | "completed" | "failed",
    recordsProcessed = 0,
    recordsFailed = 0,
    error?: Error,
    durationSeconds?: number
  ): Promise<void> {
    const now = new Date().toISOString();

    const updateData = {
      status,
      records_processed: recordsProcessed,
      records_failed: recordsFailed,
      duration_seconds: durationSeconds,
      last_sync_at: status === "running" ? now : undefined,
      error_message: error?.message,
    };

    const { error: updateError } = await this.supabase
      .from("parliament_sync_status")
      .update(updateData)
      .eq("sync_type", syncType);

    if (updateError) {
      console.error(
        `Failed to update sync status for ${syncType}:`,
        updateError
      );
    }
  }

  async getSyncStatus() {
    const { data, error } = await this.supabase
      .from("parliament_sync_status")
      .select("*")
      .order("created_at", { ascending: false });

    if (error) {
      throw new Error(`Failed to get sync status: ${error.message}`);
    }

    return data || [];
  }
}
