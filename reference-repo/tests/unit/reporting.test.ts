import assert from "node:assert/strict";
import Module from "node:module";

type ModuleLoad = (
  request: string,
  parent: NodeModule | null | undefined,
  isMain: boolean,
) => unknown;

const moduleWithLoad = Module as typeof Module & { _load: ModuleLoad };

async function main() {
  process.env.SUPABASE_SERVICE_KEY = "test-service-key-for-hmac";
  process.env.NEXT_PUBLIC_FRONTEND_URL = "https://example.test";

  const originalLoad = moduleWithLoad._load;

  // --- Configurable mock state ---
  let fingerprintCountResult: { count: number | null; error: unknown } = { count: 0, error: null };
  let userCountResult: { count: number | null; error: unknown } = { count: 0, error: null };
  let duplicateResult: { data: unknown; error: unknown } = { data: null, error: null };
  let clipResult: { data: unknown; error: unknown } = { data: { id: "clip-1", title: "Test Clip" }, error: null };
  let insertResult: { data: unknown; error: unknown } = {
    data: { id: "report-1", created_at: new Date().toISOString() },
    error: null,
  };
  let emailSendResult: { success: boolean; error?: string } = { success: true };
  let updateCalls: Array<Record<string, unknown>> = [];
  let currentUserId: string | null = null;
  let headersMap: Record<string, string | null> = {
    "x-real-ip": "1.2.3.4",
  };

  // Track fingerprint vs user count queries per createPublicClipReport call
  let countQueryIndex = 0;

  function resetState() {
    fingerprintCountResult = { count: 0, error: null };
    userCountResult = { count: 0, error: null };
    duplicateResult = { data: null, error: null };
    clipResult = { data: { id: "clip-1", title: "Test Clip" }, error: null };
    insertResult = {
      data: { id: "report-1", created_at: new Date().toISOString() },
      error: null,
    };
    emailSendResult = { success: true };
    updateCalls = [];
    currentUserId = null;
    headersMap = { "x-real-ip": "1.2.3.4" };
    countQueryIndex = 0;
  }

  const supabaseAdminMock = {
    from(table: string) {
      if (table === "public_clip_reports") {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const chain: Record<string, (...args: any[]) => any> = {};

        chain.select = (_cols: unknown, opts?: { count?: string; head?: boolean }) => {
          if (opts?.count === "exact" && opts?.head === true) {
            // Count query — rate limiting. First call = fingerprint, second = user.
            const result = countQueryIndex === 0 ? fingerprintCountResult : userCountResult;
            countQueryIndex++;

            const countChain: Record<string, unknown> = {};
            countChain.eq = () => countChain;
            countChain.gte = () => countChain;
            countChain.then = (
              onFulfill: (v: unknown) => unknown,
              onReject?: (e: unknown) => unknown,
            ) => Promise.resolve(result).then(onFulfill, onReject);
            return countChain;
          }

          // Regular select — duplicate check
          const selectChain: Record<string, unknown> = {};
          selectChain.eq = () => selectChain;
          selectChain.gte = () => selectChain;
          selectChain.limit = () => selectChain;
          selectChain.maybeSingle = async () => duplicateResult;
          return selectChain;
        };

        chain.insert = () => {
          const insertChain: Record<string, unknown> = {};
          insertChain.select = () => insertChain;
          insertChain.single = async () => insertResult;
          return insertChain;
        };

        chain.update = (data: Record<string, unknown> = {}) => {
          updateCalls.push(data);
          const updateChain: Record<string, unknown> = {};
          updateChain.eq = () => updateChain;
          updateChain.then = (
            onFulfill: (v: unknown) => unknown,
            onReject?: (e: unknown) => unknown,
          ) => Promise.resolve({ error: null }).then(onFulfill, onReject);
          return updateChain;
        };

        return chain;
      }

      if (table === "user_clips") {
        const chain: Record<string, unknown> = {};
        chain.select = () => chain;
        chain.eq = () => chain;
        chain.single = async () => clipResult;
        return chain;
      }

      const chain: Record<string, unknown> = {};
      chain.select = () => chain;
      chain.eq = () => chain;
      chain.maybeSingle = async () => ({ data: null, error: null });
      return chain;
    },
  };

  moduleWithLoad._load = function patchedLoad(
    request: string,
    parent: NodeModule | null | undefined,
    isMain: boolean,
  ) {
    if (request === "server-only") {
      return {};
    }

    if (request === "@/supabase/supabaseAdmin" || request.endsWith("/supabase/supabaseAdmin")) {
      return { supabaseAdminClient: supabaseAdminMock };
    }

    if (request === "@/supabase/supabaseServerClient" || request.endsWith("/supabase/supabaseServerClient")) {
      return {
        createSupabaseServerClient: async () => ({
          auth: {
            getUser: async () => ({
              data: { user: currentUserId ? { id: currentUserId } : null },
            }),
          },
        }),
      };
    }

    if (request === "@/lib/errorLogger" || request.endsWith("/lib/errorLogger")) {
      return {
        ErrorLogger: {
          logError() {},
          logDatabaseError() {},
          logAuthError() {},
          logApiError() {},
          logEvent() {},
        },
      };
    }

    if (request === "@/lib/getErrorMessage" || request.endsWith("/lib/getErrorMessage")) {
      return { getErrorMessage: (e: unknown) => String(e) };
    }

    if (request === "@/lib/clipHelpers" || request.endsWith("/lib/clipHelpers")) {
      return {
        getPublicClipUrl: (id: string) => `https://example.test/clips/${id}`,
      };
    }

    if (request === "@/lib/mailjet" || request.endsWith("/lib/mailjet")) {
      return {
        sendHtmlEmail: async () => emailSendResult,
      };
    }

    if (request === "@/emails/public-clip-report-admin" || request.endsWith("/emails/public-clip-report-admin")) {
      return { PublicClipReportAdminEmail: () => null };
    }

    // next/headers can resolve through various paths
    if (
      request === "next/headers" ||
      request.includes("next/headers") ||
      request.includes("next/dist/server/request/headers")
    ) {
      return {
        headers: async () => ({
          get: (key: string) => headersMap[key] ?? null,
        }),
      };
    }

    if (request === "@react-email/components" || request.includes("@react-email/components")) {
      return { render: async () => "<html>email</html>" };
    }

    return originalLoad(request, parent, isMain);
  };

  try {
    const { createPublicClipReport, notifyAdminOfPublicClipReport } = await import(
      "@/lib/clips/reporting"
    );

    const validInput = {
      clipId: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      reason: "misleading" as const,
      details: "Test details",
    };

    // --- Test: validation failure ---
    {
      resetState();
      const result = await createPublicClipReport({
        clipId: "not-a-uuid",
        reason: "misleading",
      });
      assert.equal(result.ok, false);
      assert.equal((result as { code: string }).code, "validation_error");
      console.log("  validation failure: passed");
    }

    // --- Test: rate limited (fingerprint at limit) ---
    {
      resetState();
      fingerprintCountResult = { count: 10, error: null };
      const result = await createPublicClipReport(validInput);
      assert.equal(result.ok, false);
      assert.equal((result as { code: string }).code, "rate_limited");
      console.log("  rate limited (fingerprint): passed");
    }

    // --- Test: rate limited (DB error → fail closed) ---
    {
      resetState();
      fingerprintCountResult = {
        count: null,
        error: { message: "connection refused", code: "500", details: null, hint: null },
      };
      const result = await createPublicClipReport(validInput);
      assert.equal(result.ok, false);
      assert.equal((result as { code: string }).code, "rate_limited");
      console.log("  rate limited (DB error → fail closed): passed");
    }

    // --- Test: clip unavailable ---
    {
      resetState();
      clipResult = { data: null, error: null };
      const result = await createPublicClipReport(validInput);
      assert.equal(result.ok, false);
      assert.equal((result as { code: string }).code, "clip_unavailable");
      console.log("  clip unavailable: passed");
    }

    // --- Test: duplicate report ---
    {
      resetState();
      duplicateResult = { data: { id: "existing-report" }, error: null };
      const result = await createPublicClipReport(validInput);
      assert.equal(result.ok, false);
      assert.equal((result as { code: string }).code, "duplicate_report");
      console.log("  duplicate report: passed");
    }

    // --- Test: duplicate check DB error → fail closed ---
    {
      resetState();
      duplicateResult = {
        data: null,
        error: { message: "db error", code: "500", details: null, hint: null },
      };
      const result = await createPublicClipReport(validInput);
      assert.equal(result.ok, false);
      assert.equal((result as { code: string }).code, "duplicate_report");
      console.log("  duplicate check DB error → fail closed: passed");
    }

    // --- Test: successful insert ---
    {
      resetState();
      const result = await createPublicClipReport(validInput);
      assert.equal(result.ok, true);
      if (result.ok) {
        assert.equal(result.notificationJob.clipId, "clip-1");
        assert.equal(result.notificationJob.reason, "misleading");
      }
      console.log("  successful insert: passed");
    }

    // --- Test: notifyAdmin — missing MAILJET_ADMIN_EMAIL ---
    {
      resetState();
      const origAdmin = process.env.MAILJET_ADMIN_EMAIL;
      const origSender = process.env.MAILJET_SENDER_EMAIL;
      delete process.env.MAILJET_ADMIN_EMAIL;
      delete process.env.MAILJET_SENDER_EMAIL;

      await notifyAdminOfPublicClipReport({
        reportId: "report-1",
        clipId: "clip-1",
        clipTitle: "Test",
        clipUrl: "https://example.test/clips/clip-1",
        reason: "misleading",
        details: null,
        submittedAt: new Date().toISOString(),
      });

      assert.ok(updateCalls.length > 0, "should update report status on missing email config");
      assert.equal(updateCalls[0].notification_status, "failed");

      process.env.MAILJET_ADMIN_EMAIL = origAdmin;
      process.env.MAILJET_SENDER_EMAIL = origSender;
      console.log("  notifyAdmin missing email config: passed");
    }

    // --- Test: notifyAdmin — email send failure ---
    {
      resetState();
      process.env.MAILJET_ADMIN_EMAIL = "admin@example.test";
      emailSendResult = { success: false, error: "Mailjet error" };

      await notifyAdminOfPublicClipReport({
        reportId: "report-2",
        clipId: "clip-1",
        clipTitle: "Test",
        clipUrl: "https://example.test/clips/clip-1",
        reason: "misleading",
        details: null,
        submittedAt: new Date().toISOString(),
      });

      assert.ok(updateCalls.length > 0, "should update report status on send failure");
      assert.equal(updateCalls[0].notification_status, "failed");
      console.log("  notifyAdmin email failure: passed");
    }

    // --- Test: notifyAdmin — successful send ---
    {
      resetState();
      process.env.MAILJET_ADMIN_EMAIL = "admin@example.test";
      emailSendResult = { success: true };

      await notifyAdminOfPublicClipReport({
        reportId: "report-3",
        clipId: "clip-1",
        clipTitle: "Test",
        clipUrl: "https://example.test/clips/clip-1",
        reason: "misleading",
        details: null,
        submittedAt: new Date().toISOString(),
      });

      assert.ok(updateCalls.length > 0, "should update report status on success");
      assert.equal(updateCalls[0].notification_status, "sent");
      console.log("  notifyAdmin successful send: passed");
    }

    console.log("reporting tests passed");
  } finally {
    moduleWithLoad._load = originalLoad;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
