"use server";

import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import {
  signInWithInviteSchema,
  signupSchema,
  otpVerificationSchema,
  appReviewPasswordSchema,
} from "@/schemas/authSchema";
import { redirect } from "next/navigation";
import { z } from "zod";
import { isMPEmail, getMPDomainsForDisplay } from "@/lib/domains";
import { isActualMPByEmail } from "@/lib/user-helpers";
import { ErrorLogger } from "@/lib/errorLogger";
import { buildPendingTermsMetadata, isMetadataTermsSurface, recordTermsAcceptance, TERMS_METADATA_KEYS } from "@/lib/legal/terms";
import { CALLBACK_ERROR_MESSAGES } from "@/lib/auth/callback-errors";
import { finalizePostAuth } from "@/lib/auth/post-auth-finalization";

/** Expected Supabase error patterns — skip Glitchtip logging for these */
const RATE_LIMIT_ERROR = /security purposes.*request this after/i;
const TOKEN_EXPIRED_ERROR = /Token has expired or is invalid/i;
const ALREADY_REGISTERED_ERROR = /already registered/i;
const TERMS_REQUIRED_ERROR = "You must agree to the Terms & Conditions";
const TERMS_RETRY_ERROR = CALLBACK_ERROR_MESSAGES.terms_acceptance_required;
const TERMS_SAVE_ERROR = CALLBACK_ERROR_MESSAGES.terms_acceptance_failed;

function withTimeout<T>(
  promise: Promise<T>,
  ms = 30_000,
  label = "operation",
): Promise<T> {
  let timer: ReturnType<typeof setTimeout>;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} timed out`)), ms);
  });
  promise.finally(() => clearTimeout(timer)).catch(() => {});
  return Promise.race([promise, timeoutPromise]);
}

function getSignupValidationError(error: z.ZodError<z.infer<typeof signupSchema>>) {
  const fieldErrors = error.flatten().fieldErrors;
  return fieldErrors.acceptedTerms?.[0] || fieldErrors.email?.[0] || "Invalid email address";
}

async function validateInvitation(email: string, token: string) {
  return supabaseAdminClient
    .from("team_invitations")
    .select("*, teams(name, owner_id)")
    .eq("token", token)
    .eq("email", email)
    .is("accepted_at", null)
    .gt("expires_at", new Date().toISOString())
    .single();
}

async function canUserSignUp(
  email: string,
  invitationToken?: string,
): Promise<{ allowed: boolean; isActualMP?: boolean; error?: string }> {
  // Check if it's an MP email - always allowed for actual MPs
  if (isMPEmail(email)) {
    if (!email.endsWith("@veedoo.io")) {
      const isMP = await isActualMPByEmail(email, supabaseAdminClient);
      if (!isMP) {
        // Not found in parliament_member_contacts — this is parliament staff, not an MP
        // Allow signup if they have a valid invitation token
        if (invitationToken) {
          const { data: invitation, error: inviteError } =
            await validateInvitation(email, invitationToken);
          if (!inviteError && invitation) {
            return { allowed: true, isActualMP: false };
          }
          return {
            allowed: false,
            error:
              "Invalid or expired invitation. Please contact the MP who invited you for a new invitation link.",
          };
        }
        return {
          allowed: false,
          error:
            "We are unable to automate your account creation at this time. Please contact us for assistance.",
        };
      }
      return { allowed: true, isActualMP: true };
    }

    // @veedoo.io emails are always treated as MPs
    return { allowed: true, isActualMP: true };
  }

  // Non-MP emails need a valid invitation
  if (!invitationToken) {
    return {
      allowed: false,
      error: `Sign up is currently limited to MPs with ${getMPDomainsForDisplay()} email addresses. If you've been invited by an MP, please use the invitation link sent to your email.`,
    };
  }

  // Validate invitation token
  const { data: invitation, error: inviteError } =
    await validateInvitation(email, invitationToken);

  if (inviteError || !invitation) {
    return {
      allowed: false,
      error:
        "Invalid or expired invitation. Please contact the MP who invited you for a new invitation link.",
    };
  }

  return { allowed: true, isActualMP: false };
}

async function checkUserExists(email: string): Promise<string | null> {
  const { data, error } = await supabaseAdminClient
    .from("user_roles")
    .select("user_id")
    .eq("email", email)
    .maybeSingle();

  if (error) {
    ErrorLogger.logDatabaseError(error, "checkUserExists", "user_roles");
    return null;
  }

  return data?.user_id ?? null;
}


export async function checkUserExistsByEmail(
  email: string,
): Promise<{ exists: boolean; error?: string }> {
  try {
    const userId = await checkUserExists(email);
    return { exists: userId !== null };
  } catch (error) {
    ErrorLogger.logError(
      error instanceof Error ? error : new Error(String(error)),
      { action: "checkUserExistsByEmail", feature: "auth" },
    );
    return { exists: false, error: "Failed to check user existence" };
  }
}

export async function signInWithOtp(
  data: z.infer<typeof signInWithInviteSchema>,
) {
  const supabase = await createSupabaseServerClient();

  const validated = signInWithInviteSchema.safeParse(data);
  if (!validated.success) {
    return { error: "Invalid email address" };
  }

  if (validated.data.invitationToken && validated.data.acceptedTerms !== true) {
    return { error: TERMS_REQUIRED_ERROR };
  }

  // Check if user exists (returns user_id or null)
  const existingUserId = await checkUserExists(validated.data.email);

  if (!existingUserId) {
    // User doesn't have an account - direct them to sign up
    return {
      error: "ACCOUNT_NOT_FOUND",
      message: "You don't have an account. Please sign up to create one.",
    };
  }

  const signInPromise = supabase.auth.signInWithOtp({
    email: validated.data.email,
    options: {
      shouldCreateUser: false,
      emailRedirectTo: `${process.env.NEXT_PUBLIC_FRONTEND_URL}/auth/callback`,
      data: validated.data.invitationToken
        ? {
            invitation_token: validated.data.invitationToken,
            ...buildPendingTermsMetadata("invite_signin", validated.data.invitationToken),
          }
        : { invitation_token: null },
    },
  });

  try {
    const { error } = await withTimeout(signInPromise, 30_000, "Sign-in request");

    if (error) {
      if (RATE_LIMIT_ERROR.test(error.message)) {
        ErrorLogger.logEvent("auth_rate_limited", { action: "signInWithOtp", feature: "auth" });
      } else {
        ErrorLogger.logAuthError(error, "signInWithOtp", undefined, "auth");
      }
      return { error: error.message };
    }

    // For invitation sign-in, explicitly set metadata via admin API.
    // signInWithOtp uses shouldCreateUser: false, so the user always exists
    // and the data parameter may be silently ignored by Supabase.
    if (validated.data.invitationToken) {
      try {
        if (existingUserId) {
          const { error: updateError } = await supabaseAdminClient.auth.admin.updateUserById(
            existingUserId,
            {
              user_metadata: {
                invitation_token: validated.data.invitationToken,
                ...buildPendingTermsMetadata("invite_signin", validated.data.invitationToken),
              },
            },
          );
          if (updateError) {
            ErrorLogger.logError(new Error(updateError.message),
              { action: "signInWithOtp:ensureInviteMetadata", feature: "auth" });
          }
        }
      } catch (metadataErr) {
        ErrorLogger.logError(
          metadataErr instanceof Error ? metadataErr : new Error(String(metadataErr)),
          { action: "signInWithOtp:ensureInviteMetadata", feature: "auth" },
        );
      }
    }

    return { success: true, requiresOtp: true };
  } catch (err) {
    ErrorLogger.logAuthError(
      err instanceof Error ? err : new Error(String(err)),
      "signInWithOtp",
      undefined,
      "auth",
    );
    return { error: err instanceof Error ? err.message : "Sign-in failed" };
  }
}

export async function verifyOtp(
  data: z.infer<typeof otpVerificationSchema>,
) {
  const supabase = await createSupabaseServerClient();

  const validated = otpVerificationSchema.safeParse(data);
  if (!validated.success) {
    return { error: "Invalid verification code" };
  }

  const { data: authData, error } = await supabase.auth.verifyOtp({
    email: validated.data.email,
    token: validated.data.token,
    type: "email",
  });

  if (error) {
    if (TOKEN_EXPIRED_ERROR.test(error.message)) {
      ErrorLogger.logEvent("auth_token_expired", { action: "verifyOtp", feature: "auth" });
    } else {
      ErrorLogger.logAuthError(error, "verifyOtp", undefined, "auth");
    }
    return { error: error.message };
  }

  if (!authData.user) {
    return { error: "Verification failed" };
  }

  // invitation_token is set in user_metadata during signInWithOtp/signUp and
  // persists through OTP verification. Do NOT graft client-supplied tokens —
  // that would let an attacker inject an arbitrary invitation_token.
  const result = await finalizePostAuth(authData.user, supabase);

  if (!result.ok) {
    return {
      error: result.errorCode === "terms_acceptance_required"
        ? TERMS_RETRY_ERROR
        : TERMS_SAVE_ERROR,
      redirectPath: `${result.redirectPath}?error=${result.errorCode}`,
    };
  }

  return { success: true, redirectTo: result.redirectTo };
}

export async function signUp(
  data: z.infer<typeof signupSchema>,
) {
  const supabase = await createSupabaseServerClient();

  const validated = signupSchema.safeParse(data);
  if (!validated.success) {
    return { error: getSignupValidationError(validated.error) };
  }

  const invitationToken = validated.data.invitationToken ?? null;

  // Check if user is allowed to sign up (also returns MP status to avoid duplicate query)
  const { allowed, isActualMP: isActualMPUser = false, error: validationError } = await canUserSignUp(
    validated.data.email,
    invitationToken ?? undefined,
  );
  if (!allowed) {
    return {
      error: validationError || "You are not authorized to create an account.",
    };
  }

  try {
    // Add timeout to the Supabase call
    const signupPromise = supabase.auth.signInWithOtp({
      email: validated.data.email,
      options: {
        data: {
          is_first_login: true,
          is_parliament_member: isActualMPUser,
          invitation_token: invitationToken,
          ...buildPendingTermsMetadata(
            invitationToken ? "invite_signup" : "signup",
            invitationToken,
          ),
        },
        shouldCreateUser: true,
        emailRedirectTo: `${process.env.NEXT_PUBLIC_FRONTEND_URL}/auth/callback`,
      },
    });

    const { error } = await withTimeout(signupPromise, 30_000, "Signup request");

    if (error) {
      if (RATE_LIMIT_ERROR.test(error.message)) {
        ErrorLogger.logEvent("auth_rate_limited", { action: "signUp", feature: "auth" });
      } else if (ALREADY_REGISTERED_ERROR.test(error.message)) {
        ErrorLogger.logEvent("auth_already_registered", { action: "signUp", feature: "auth" });
      } else {
        ErrorLogger.logAuthError(error, "signUp", undefined, "auth");
      }
      return { error: error.message };
    }

    // Defense-in-depth: explicitly set terms metadata via admin API.
    // signInWithOtp's `data` parameter only reliably writes metadata when
    // creating a new auth.users row. For pre-existing users (e.g. previous
    // failed signup, expired OTP) it silently ignores the data field.
    try {
      const existingUserId = await checkUserExists(validated.data.email);

      if (existingUserId) {
        const { error: updateError } = await supabaseAdminClient.auth.admin.updateUserById(
          existingUserId,
          {
            user_metadata: {
              invitation_token: invitationToken,
              ...buildPendingTermsMetadata(
                invitationToken ? "invite_signup" : "signup",
                invitationToken,
              ),
            },
          },
        );
        if (updateError) {
          ErrorLogger.logError(new Error(updateError.message),
            { action: "signUp:ensureTermsMetadata", feature: "auth" });
        }
      }
    } catch (metadataErr) {
      ErrorLogger.logError(
        metadataErr instanceof Error ? metadataErr : new Error(String(metadataErr)),
        { action: "signUp:ensureTermsMetadata", feature: "auth" },
      );
    }

    return {
      success: true,
      requiresOtp: true,
      isParliamentMember: isActualMPUser,
      hasInvitation: !!invitationToken,
    };
  } catch (err) {
    ErrorLogger.logAuthError(
      err instanceof Error ? err : new Error(String(err)),
      "signUp",
      undefined,
      "auth",
    );
    return { error: err instanceof Error ? err.message : "Signup failed" };
  }
}

export async function resendOtp(data: { email: string }) {
  const supabase = await createSupabaseServerClient();

  // Best-effort: refresh pending terms timestamp so it doesn't expire before
  // the new OTP is used. Failures here must not block the core OTP resend —
  // finalizePostAuth has an expired-consent fallback that still records terms.
  let termsMetadata: Record<string, unknown> | undefined;
  try {
    const { data: userData } = await supabaseAdminClient
      .from("user_roles")
      .select("user_id")
      .eq("email", data.email)
      .maybeSingle();

    if (userData?.user_id) {
      const { data: { user } } = await supabaseAdminClient.auth.admin.getUserById(userData.user_id);
      if (user?.user_metadata?.[TERMS_METADATA_KEYS.pending] === true) {
        const surface = user.user_metadata[TERMS_METADATA_KEYS.surface];
        const invToken = user.user_metadata[TERMS_METADATA_KEYS.invitationToken];
        if (isMetadataTermsSurface(surface)) {
          termsMetadata = buildPendingTermsMetadata(
            surface,
            typeof invToken === "string" ? invToken : undefined,
          );
        }
      }
    }
  } catch (err) {
    // Non-critical — proceed without refreshing terms metadata
    ErrorLogger.logError(
      err instanceof Error ? err : new Error(String(err)),
      { action: "resendOtp:refreshTermsMetadata", feature: "auth" },
    );
  }

  const otpPromise = supabase.auth.signInWithOtp({
    email: data.email,
    options: {
      shouldCreateUser: false,
      emailRedirectTo: `${process.env.NEXT_PUBLIC_FRONTEND_URL}/auth/callback`,
      data: termsMetadata,
    },
  });

  try {
    const { error } = await withTimeout(otpPromise, 30_000, "OTP resend request");

    if (error) {
      return { error: error.message };
    }

    return { success: true };
  } catch (err) {
    ErrorLogger.logAuthError(
      err instanceof Error ? err : new Error(String(err)),
      "resendOtp",
      undefined,
      "auth",
    );
    return { error: err instanceof Error ? err.message : "OTP resend failed" };
  }
}

// ─── In-memory rate limiter for app review password (5 attempts / 15 min) ────
const APP_REVIEW_RATE_LIMIT_MAX = 5;
const APP_REVIEW_RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000;
const appReviewRateLimitMap = new Map<string, { count: number; resetAt: number }>();

function checkAppReviewRateLimit(email: string): boolean {
  const now = Date.now();
  const entry = appReviewRateLimitMap.get(email);
  if (!entry || now >= entry.resetAt) {
    appReviewRateLimitMap.set(email, { count: 1, resetAt: now + APP_REVIEW_RATE_LIMIT_WINDOW_MS });
    return true;
  }
  if (entry.count >= APP_REVIEW_RATE_LIMIT_MAX) return false;
  entry.count++;
  return true;
}

export async function signInWithAppReviewPassword(
  data: z.infer<typeof appReviewPasswordSchema>,
) {
  const validated = appReviewPasswordSchema.safeParse(data);
  if (!validated.success) {
    return { error: "Invalid credentials" };
  }

  // Check feature flag and email match before rate limiting
  // to avoid leaking information when the feature is disabled
  if (process.env.NEXT_PUBLIC_APP_REVIEW_AUTH_ENABLED !== "true") {
    return { error: "Invalid credentials" };
  }

  if (validated.data.email !== process.env.NEXT_PUBLIC_APP_REVIEW_EMAIL) {
    return { error: "Invalid credentials" };
  }

  // Rate limit only applies to valid email + enabled feature
  if (!checkAppReviewRateLimit(validated.data.email)) {
    return { error: "Invalid credentials" };
  }

  // Check password matches (server-only env var)
  if (validated.data.password !== process.env.APP_REVIEW_PASSWORD) {
    return { error: "Invalid credentials" };
  }

  try {
    const existingAppReviewUserId = await checkUserExists(validated.data.email);

    if (!existingAppReviewUserId) {
      // Create the user via admin API
      const { error: createError } =
        await supabaseAdminClient.auth.admin.createUser({
          email: validated.data.email,
          email_confirm: true,
          user_metadata: {
            is_first_login: false,
            is_parliament_member: true,
          },
        });

      if (createError) {
        ErrorLogger.logAuthError(
          createError,
          "signInWithAppReviewPassword:createUser",
          undefined,
          "auth",
        );
        return { error: "Invalid credentials" };
      }
    } else {
      // Ensure metadata is correct for existing user
      await supabaseAdminClient.auth.admin.updateUserById(
        existingAppReviewUserId,
        { user_metadata: { is_first_login: false } },
      );
    }

    // Generate session via generateLink + verifyOtp
    const { data: linkData, error: linkError } =
      await supabaseAdminClient.auth.admin.generateLink({
        type: "magiclink",
        email: validated.data.email,
      });

    if (linkError || !linkData.properties?.hashed_token) {
      ErrorLogger.logAuthError(
        linkError || new Error("No hashed_token returned"),
        "signInWithAppReviewPassword:generateLink",
        undefined,
        "auth",
      );
      return { error: "Invalid credentials" };
    }

    // Create session via server client (auto-sets cookies)
    const supabase = await createSupabaseServerClient();
    const { error: verifyError } = await supabase.auth.verifyOtp({
      token_hash: linkData.properties.hashed_token,
      type: "magiclink",
    });

    if (verifyError) {
      ErrorLogger.logAuthError(
        verifyError,
        "signInWithAppReviewPassword:verifyOtp",
        undefined,
        "auth",
      );
      return { error: "Invalid credentials" };
    }

    // Record terms acceptance for app review accounts — they bypass the
    // consent UI but still need a terms_acceptances row for consistency.
    const { data: { user: sessionUser } } = await supabase.auth.getUser();
    if (!sessionUser) {
      ErrorLogger.logError(
        new Error("Session user not found after successful OTP verification"),
        { action: "signInWithAppReviewPassword", feature: "terms" },
      );
      await supabase.auth.signOut().catch(() => {});
      return { error: "Sign-in failed. Please try again." };
    }

    const recorded = await recordTermsAcceptance(sessionUser.id, "signup");
    if (!recorded) {
      ErrorLogger.logError(
        new Error("Failed to record terms acceptance for app review account"),
        { action: "signInWithAppReviewPassword", feature: "terms", additionalContext: { userId: sessionUser.id } },
      );
      await supabase.auth.signOut().catch(() => {});
      return { error: "Sign-in failed. Please try again." };
    }

    return { success: true, redirectTo: "/dashboard" };
  } catch (err) {
    ErrorLogger.logAuthError(
      err instanceof Error ? err : new Error(String(err)),
      "signInWithAppReviewPassword",
      undefined,
      "auth",
    );
    return { error: "Invalid credentials" };
  }
}

export async function signOut() {
  const supabase = await createSupabaseServerClient();

  const { error } = await supabase.auth.signOut();

  if (error) {
    ErrorLogger.logAuthError(error, "signOut", undefined, "auth");
  }

  redirect("/");
}
