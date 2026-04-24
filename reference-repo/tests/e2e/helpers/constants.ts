/**
 * Shared E2E test constants.
 * All test data uses these sentinels for identification and cleanup.
 */

/** E2E test parliament member IDs start at 90,000 to avoid collisions with real MP data (< 5000) */
export const E2E_MEMBER_ID_START = 90_000;
export const MP_ALPHA_ID = 90_001;
export const MP_BETA_ID = 90_002;
export const MP_GAMMA_ID = 90_003;
export const MP_LD_DELTA_ID = 90_004;

/** Prefix for all test emails — cleanup guards refuse to delete non-matching emails */
export const E2E_EMAIL_PREFIX = "e2e-";

/** Allowed test email domains */
export const E2E_TEST_DOMAINS = ["test.local", "veedoo.io"] as const;

/** Minimal 1x1 PNG for avatar upload tests */
export const TEST_AVATAR_BUFFER = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "base64"
);
