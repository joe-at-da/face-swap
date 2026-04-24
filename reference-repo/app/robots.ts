import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const baseUrl =
    process.env.NEXT_PUBLIC_FRONTEND_URL || "https://parliamentconnect.com";

  // Normalize baseUrl for comparison (remove trailing slash)
  const normalizedBaseUrl = baseUrl.replace(/\/$/, "");

  // Check if we're on localhost or staging server
  const isLocalhost =
    normalizedBaseUrl.includes("localhost") ||
    normalizedBaseUrl.includes("127.0.0.1") ||
    normalizedBaseUrl.startsWith("http://localhost") ||
    normalizedBaseUrl.startsWith("http://127.0.0.1");
  const isStaging =
    normalizedBaseUrl.includes("themp.veedoo.dev") ||
    normalizedBaseUrl === "https://themp.veedoo.dev";

  // Disallow all crawlers for localhost and staging
  if (isLocalhost || isStaging) {
    return {
      rules: {
        userAgent: "*",
        disallow: "/",
      },
    };
  }

  // Production rules - allow crawlers with restrictions
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/dashboard",
          "/dashboard/*",
          "/setup",
          "/setup/*",
          "/mp-setup",
          "/mp-setup/*",
          "/team-setup",
          "/team-setup/*",
          "/no-team-access",
          "/no-team-access/*",
          "/api",
          "/api/*",
          "/auth",
          "/auth/*",
          "/signin",
          "/signin/*",
          "/signup",
          "/signup/*",
          "/teams/invite/*",
        ],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
