"use server";

import { after } from "next/server";
import {
  createPublicClipReport,
  notifyAdminOfPublicClipReport,
  type PublicClipReportActionResult,
} from "@/lib/clips/reporting";
import { ErrorLogger } from "@/lib/errorLogger";
import type { PublicClipReportInput } from "@/schemas/publicClipReportSchema";

export async function submitPublicClipReport(
  input: PublicClipReportInput,
): Promise<PublicClipReportActionResult> {
  try {
    const result = await createPublicClipReport(input);

    if (!result.ok) {
      // Safe: SubmitPublicClipReportResult failure cases are a subset of
      // PublicClipReportActionResult (PublicClipReportActionFailure is
      // derived from it), so the structural match is intentional.
      return result;
    }

    // after() defers the callback until AFTER the response is sent.
    // Errors in the callback do not bubble up to this try/catch.
    after(async () => {
      try {
        await notifyAdminOfPublicClipReport(result.notificationJob);
      } catch (e) {
        ErrorLogger.logError(
          e instanceof Error ? e : new Error(String(e)),
          { action: "after:notifyAdmin", feature: "clips" },
        );
      }
    });

    return { ok: true };
  } catch (error) {
    ErrorLogger.logError(
      error instanceof Error ? error : new Error(String(error)),
      {
        component: "public-clip-reporting",
        action: "submitPublicClipReport",
        feature: "clips",
      },
    );
    return { ok: false, code: "persistence_error" };
  }
}
