/**
 * Mailpit email testing helper.
 * Docker Compose dev environment captures all GoTrue auth emails via Mailpit.
 * API docs: https://mailpit.axllent.org/docs/api-v1/
 *
 * Port is set by setup-worktree.sh via MAILPIT_HTTP_PORT in .env.
 */

const MAILPIT_URL =
  process.env.MAILPIT_URL ||
  `http://127.0.0.1:${process.env.MAILPIT_HTTP_PORT || "8025"}`;

interface MailpitMessage {
  ID: string;
  MessageID: string;
  From: { Name: string; Address: string };
  To: { Name: string; Address: string }[];
  Subject: string;
  Created: string;
  Size: number;
  Snippet: string;
}

interface MailpitMessageDetail {
  ID: string;
  MessageID: string;
  From: { Name: string; Address: string };
  To: { Name: string; Address: string }[];
  Subject: string;
  Created: string;
  Text: string;
  HTML: string;
}

/**
 * Fetch the latest email for a given address with polling.
 * Uses exponential backoff: starts at 200ms, caps at 2s (faster for common case).
 */
export async function getLatestEmail(
  email: string,
  { maxAttempts = 15, initialDelayMs = 200 } = {}
): Promise<MailpitMessageDetail | null> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const res = await fetch(
      `${MAILPIT_URL}/api/v1/search?query=to:${encodeURIComponent(email)}&limit=1`
    );
    const data = await res.json();
    const messages: MailpitMessage[] = data.messages || [];

    if (messages.length > 0) {
      const latest = messages[0];
      const msgRes = await fetch(
        `${MAILPIT_URL}/api/v1/message/${latest.ID}`
      );
      return await msgRes.json();
    }

    const delay = Math.min(initialDelayMs * Math.pow(1.5, attempt), 2000);
    await new Promise((r) => setTimeout(r, delay));
  }

  return null;
}

/**
 * Extract the 6-digit OTP from a Mailpit email.
 * The Supabase email template puts the token as the first thing in the subject:
 * "{{ .Token }} is your verification code for Parliament Connect"
 */
export function extractOtpFromEmail(
  message: MailpitMessageDetail
): string | null {
  // Try subject first (most reliable)
  const subjectMatch = message.Subject.match(/^(\d{6})/);
  if (subjectMatch) return subjectMatch[1];

  // Fallback: search body text for a 6-digit code
  const bodyText = message.Text || message.HTML || "";
  const bodyMatch = bodyText.match(/\b(\d{6})\b/);
  return bodyMatch ? bodyMatch[1] : null;
}

/**
 * Extract the magic link URL from a Mailpit email body.
 * The magic link contains /auth/callback or /auth/v1/verify in the URL.
 */
export function extractMagicLinkFromEmail(
  message: MailpitMessageDetail
): string | null {
  // Prefer text body — URLs have clean & characters (no HTML entities)
  if (message.Text) {
    const textMatch = message.Text.match(
      /(https?:\/\/[^\s)]*(?:\/auth\/callback|\/auth\/v1\/verify)[^\s)]*)/
    );
    if (textMatch) return textMatch[1];
  }

  // Fallback: extract from HTML href (must decode &amp; → &)
  if (message.HTML) {
    const htmlMatch = message.HTML.match(
      /href="([^"]*(?:\/auth\/callback|\/auth\/v1\/verify)[^"]*)"/
    );
    if (htmlMatch) return htmlMatch[1].replace(/&amp;/g, "&");
  }

  return null;
}

/**
 * Clear all emails matching a specific address (or all emails if no address).
 */
export async function clearMailbox(email: string): Promise<void> {
  // Search for messages to this address
  const res = await fetch(
    `${MAILPIT_URL}/api/v1/search?query=to:${encodeURIComponent(email)}`
  );
  const data = await res.json();
  const messages: MailpitMessage[] = data.messages || [];

  if (messages.length > 0) {
    // Delete each message individually
    const ids = messages.map((m) => m.ID);
    await fetch(`${MAILPIT_URL}/api/v1/messages`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ IDs: ids }),
    });
  }
}
