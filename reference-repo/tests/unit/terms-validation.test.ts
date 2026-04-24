import assert from "node:assert/strict";
import Module from "node:module";
import type { User } from "@supabase/supabase-js";

type ModuleLoad = (
  request: string,
  parent: NodeModule | null | undefined,
  isMain: boolean,
) => unknown;

const moduleWithLoad = Module as typeof Module & { _load: ModuleLoad };

async function main() {
  const originalLoad = moduleWithLoad._load;

  moduleWithLoad._load = function patchedLoad(
    request: string,
    parent: NodeModule | null | undefined,
    isMain: boolean,
  ) {
    if (request === "server-only") {
      return {};
    }

    if (request === "@/supabase/supabaseAdmin" || request.endsWith("/supabase/supabaseAdmin")) {
      return { supabaseAdminClient: {} };
    }

    if (request === "@/lib/errorLogger" || request.endsWith("/lib/errorLogger")) {
      return { ErrorLogger: { logError() {}, logDatabaseError() {}, logAuthError() {} } };
    }

    return originalLoad(request, parent, isMain);
  };

  try {
    const {
      getPendingTermsAcceptance,
      TERMS_METADATA_KEYS,
      TERMS_PENDING_WINDOW_MS,
    } = await import("@/lib/legal/terms");

    const baseUser = {
      id: "user-123",
      email: "test@example.com",
      created_at: new Date().toISOString(),
      aud: "authenticated",
      app_metadata: {},
      user_metadata: {},
    } as User;

    // 1. pending !== true → null
    {
      const user = { ...baseUser, user_metadata: {} };
      assert.equal(getPendingTermsAcceptance(user), null, "missing pending flag → null");
    }

    {
      const user = {
        ...baseUser,
        user_metadata: { [TERMS_METADATA_KEYS.pending]: false },
      };
      assert.equal(getPendingTermsAcceptance(user), null, "pending = false → null");
    }

    {
      const user = {
        ...baseUser,
        user_metadata: { [TERMS_METADATA_KEYS.pending]: "true" },
      };
      assert.equal(getPendingTermsAcceptance(user), null, "pending = string 'true' → null");
    }

    // 2. invalid surface → null
    {
      const user = {
        ...baseUser,
        user_metadata: {
          [TERMS_METADATA_KEYS.pending]: true,
          [TERMS_METADATA_KEYS.surface]: "invalid_surface",
          [TERMS_METADATA_KEYS.requestedAt]: new Date().toISOString(),
        },
      };
      assert.equal(getPendingTermsAcceptance(user), null, "invalid surface → null");
    }

    // invite_direct is excluded from metadata surfaces
    {
      const user = {
        ...baseUser,
        user_metadata: {
          [TERMS_METADATA_KEYS.pending]: true,
          [TERMS_METADATA_KEYS.surface]: "invite_direct",
          [TERMS_METADATA_KEYS.requestedAt]: new Date().toISOString(),
        },
      };
      assert.equal(getPendingTermsAcceptance(user), null, "invite_direct surface → null");
    }

    // 3. non-string requestedAt → null
    {
      const user = {
        ...baseUser,
        user_metadata: {
          [TERMS_METADATA_KEYS.pending]: true,
          [TERMS_METADATA_KEYS.surface]: "signup",
          [TERMS_METADATA_KEYS.requestedAt]: 12345,
        },
      };
      assert.equal(getPendingTermsAcceptance(user), null, "numeric requestedAt → null");
    }

    {
      const user = {
        ...baseUser,
        user_metadata: {
          [TERMS_METADATA_KEYS.pending]: true,
          [TERMS_METADATA_KEYS.surface]: "signup",
          [TERMS_METADATA_KEYS.requestedAt]: "not-a-date",
        },
      };
      assert.equal(getPendingTermsAcceptance(user), null, "unparseable requestedAt → null");
    }

    // 4. expired window → null
    {
      const expired = new Date(Date.now() - TERMS_PENDING_WINDOW_MS - 1000).toISOString();
      const user = {
        ...baseUser,
        user_metadata: {
          [TERMS_METADATA_KEYS.pending]: true,
          [TERMS_METADATA_KEYS.surface]: "signup",
          [TERMS_METADATA_KEYS.requestedAt]: expired,
        },
      };
      assert.equal(getPendingTermsAcceptance(user), null, "expired window → null");
    }

    // 5. valid case → correct structure
    {
      const now = new Date().toISOString();
      const user = {
        ...baseUser,
        user_metadata: {
          [TERMS_METADATA_KEYS.pending]: true,
          [TERMS_METADATA_KEYS.surface]: "signup",
          [TERMS_METADATA_KEYS.requestedAt]: now,
          [TERMS_METADATA_KEYS.invitationToken]: null,
        },
      };
      const result = getPendingTermsAcceptance(user);
      assert.notEqual(result, null, "valid case should return non-null");
      assert.equal(result!.surface, "signup");
      assert.equal(result!.requestedAt, now);
      assert.equal(result!.invitationToken, null);
    }

    // 6. valid case with invitation token
    {
      const now = new Date().toISOString();
      const user = {
        ...baseUser,
        user_metadata: {
          [TERMS_METADATA_KEYS.pending]: true,
          [TERMS_METADATA_KEYS.surface]: "invite_signin",
          [TERMS_METADATA_KEYS.requestedAt]: now,
          [TERMS_METADATA_KEYS.invitationToken]: "token-abc",
        },
      };
      const result = getPendingTermsAcceptance(user);
      assert.notEqual(result, null, "valid invite case should return non-null");
      assert.equal(result!.surface, "invite_signin");
      assert.equal(result!.invitationToken, "token-abc");
    }

    // 7. empty string invitationToken → null
    {
      const now = new Date().toISOString();
      const user = {
        ...baseUser,
        user_metadata: {
          [TERMS_METADATA_KEYS.pending]: true,
          [TERMS_METADATA_KEYS.surface]: "invite_signup",
          [TERMS_METADATA_KEYS.requestedAt]: now,
          [TERMS_METADATA_KEYS.invitationToken]: "",
        },
      };
      const result = getPendingTermsAcceptance(user);
      assert.notEqual(result, null);
      assert.equal(result!.invitationToken, null, "empty token → null");
    }

    console.log("terms-validation checks passed");
  } finally {
    moduleWithLoad._load = originalLoad;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
