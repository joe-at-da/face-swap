import "server-only";

import type { z } from "zod";
import { AnalyticsServiceError } from "./errors";
import { postizAnalyticsResponseSchema } from "./schemas";
import type {
  AnalyticsDateRange,
  PostizSessionContext,
} from "./types";

const POSTIZ_LOGIN_TIMEOUT_MS = 10000;
const POSTIZ_ANALYTICS_TIMEOUT_MS = 10000;

function getPostizApiUrl(): string {
  const url = process.env.POSTIZ_API_URL;
  if (!url) {
    throw new Error(
      "POSTIZ_API_URL is not defined — required for live Postiz API calls"
    );
  }
  return url;
}

type LoginResult = {
  cookieHeader: string;
};

function getAbortSignal(timeoutMs: number): AbortSignal {
  if (typeof AbortSignal.timeout === "function") {
    return AbortSignal.timeout(timeoutMs);
  }

  const controller = new AbortController();
  setTimeout(() => controller.abort(), timeoutMs);
  return controller.signal;
}

function extractCookieHeader(response: Response): string | null {
  const setCookies =
    "getSetCookie" in response.headers &&
    typeof response.headers.getSetCookie === "function"
      ? response.headers.getSetCookie()
      : [response.headers.get("set-cookie")].filter(
          (value): value is string => !!value
        );

  for (const header of setCookies) {
    for (const segment of header.split(",")) {
      const [cookiePair] = segment.split(";");
      if (cookiePair?.trim().startsWith("auth=")) {
        return cookiePair.trim();
      }
    }
  }

  return null;
}

export async function loginToPostiz(
  email: string,
  password: string
): Promise<LoginResult> {
  const response = await fetch(`${getPostizApiUrl()}auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password,
      provider: "LOCAL",
      providerToken: "",
    }),
    cache: "no-store",
    redirect: "error",
    signal: getAbortSignal(POSTIZ_LOGIN_TIMEOUT_MS),
  });

  if (!response.ok) {
    throw new AnalyticsServiceError(
      "upstream_unavailable",
      `Postiz login failed with status ${response.status}`
    );
  }

  const cookieHeader = extractCookieHeader(response);
  if (!cookieHeader) {
    throw new AnalyticsServiceError(
      "upstream_unavailable",
      "Postiz login did not return a session cookie"
    );
  }

  return { cookieHeader };
}

export async function fetchPostizAnalytics(
  session: PostizSessionContext,
  integrationId: string,
  range: AnalyticsDateRange
): Promise<z.infer<typeof postizAnalyticsResponseSchema>> {
  const response = await fetch(
    `${getPostizApiUrl()}analytics/${encodeURIComponent(integrationId)}?date=${range}`,
    {
      method: "GET",
      headers: {
        Cookie: session.cookieHeader,
      },
      cache: "no-store",
      redirect: "error",
      signal: getAbortSignal(POSTIZ_ANALYTICS_TIMEOUT_MS),
    }
  );

  if (response.status === 401 || response.status === 403) {
    throw new AnalyticsServiceError(
      "upstream_unavailable",
      `Postiz analytics authentication failed with status ${response.status}`
    );
  }

  if (!response.ok) {
    throw new AnalyticsServiceError(
      "upstream_unavailable",
      `Postiz analytics failed with status ${response.status}`
    );
  }

  const json: unknown = await response.json();
  return postizAnalyticsResponseSchema.parse(json);
}
