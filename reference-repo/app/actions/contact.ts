"use server";

import "server-only";

import { headers } from "next/headers";

import { contactSchema, type ContactFormData } from "@/schemas/contactSchema";
import { ErrorLogger } from "@/lib/errorLogger";

const FIBERY_API_URL = "https://parliament-connect.fibery.io/api/commands";
const FIBERY_ENTITY_TYPE = "Website Enquiries/Enquiry";
const FIBERY_STATUS_NEW_ID = "04bb1d77-a03d-444d-8190-5acd70797c89";

// --- In-memory IP-based rate limiter ---
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000; // 15 minutes

const submissionTimestamps = new Map<string, number[]>();

function getClientIp(headersList: Headers): string | null {
  const realIp = headersList.get("x-real-ip");
  if (realIp) {
    return realIp.trim();
  }
  const forwarded = headersList.get("x-forwarded-for");
  if (forwarded) {
    const ips = forwarded.split(",");
    return ips[0].trim();
  }
  return null;
}

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const timestamps = submissionTimestamps.get(ip) ?? [];

  // Remove entries outside the current window
  const recent = timestamps.filter((t) => now - t < RATE_LIMIT_WINDOW_MS);

  if (recent.length >= RATE_LIMIT_MAX) {
    submissionTimestamps.set(ip, recent);
    return true;
  }

  // Record this request
  recent.push(now);
  submissionTimestamps.set(ip, recent);

  // Periodically clean up stale entries (every 100 requests)
  if (submissionTimestamps.size > 100) {
    for (const [key, ts] of submissionTimestamps) {
      const active = ts.filter((t) => now - t < RATE_LIMIT_WINDOW_MS);
      if (active.length === 0) {
        submissionTimestamps.delete(key);
      }
    }
  }

  return false;
}

type ContactResult = { success: true } | { success: false; error: string };

export async function submitContactForm(
  data: ContactFormData
): Promise<ContactResult> {
  const headersList = await headers();
  const clientIp = getClientIp(headersList);

  if (!clientIp) {
    ErrorLogger.logEvent("Contact form submission with unidentifiable IP", {
      component: "contact-form",
      action: "submitContactForm",
    });
  }

  if (clientIp && isRateLimited(clientIp)) {
    ErrorLogger.logError(
      new Error(`Rate limited contact form submission from IP: ${clientIp}`),
      {
        component: "contact-form",
        action: "submitContactForm",
      }
    );
    return {
      success: false,
      error: "Too many submissions. Please try again later.",
    };
  }

  const parsed = contactSchema.safeParse(data);
  if (!parsed.success) {
    return { success: false, error: "Invalid form data." };
  }

  const apiKey = process.env.FIBERY_API_KEY;
  if (!apiKey) {
    ErrorLogger.logError(new Error("FIBERY_API_KEY not configured"), {
      component: "contact-form",
      action: "submitContactForm",
    });
    return {
      success: false,
      error: "Something went wrong. Please try again later.",
    };
  }

  try {
    let messageBody = parsed.data.message;
    if (parsed.data.productInterest && parsed.data.productInterest.length > 0) {
      messageBody = `Products of interest: ${parsed.data.productInterest.join(", ")}\n\n${messageBody}`;
    }

    const response = await fetch(FIBERY_API_URL, {
      method: "POST",
      headers: {
        Authorization: `Token ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify([
        {
          command: "fibery.entity/create",
          args: {
            type: FIBERY_ENTITY_TYPE,
            entity: {
              "Website Enquiries/Name": parsed.data.contactName,
              "Website Enquiries/Contact Name": parsed.data.contactName,
              "Website Enquiries/Contact Email": parsed.data.contactEmail,
              "Website Enquiries/Phone number":
                parsed.data.phoneNumber || "",
              "Website Enquiries/Message": messageBody,
              "Website Enquiries/Status": {
                "fibery/id": FIBERY_STATUS_NEW_ID,
              },
            },
          },
        },
      ]),
      signal: AbortSignal.timeout(10_000),
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Fibery API returned ${response.status}`);
    }

    type FiberyCommandResponse = {
      success: boolean;
      result?: { message?: string };
    };

    const result = (await response.json()) as FiberyCommandResponse[];
    if (!result[0]?.success) {
      throw new Error(
        result[0]?.result?.message || "Fibery entity creation failed"
      );
    }

    return { success: true };
  } catch (error) {
    ErrorLogger.logApiError(
      error instanceof Error ? error : new Error(String(error)),
      FIBERY_API_URL,
      "POST"
    );
    return {
      success: false,
      error: "Failed to send your message. Please try again.",
    };
  }
}
