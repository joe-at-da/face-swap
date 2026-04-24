import assert from "node:assert/strict";
import Module from "node:module";
import { NextRequest } from "next/server";

type ModuleLoad = (
  request: string,
  parent: NodeModule | null | undefined,
  isMain: boolean,
) => unknown;

const moduleWithLoad = Module as typeof Module & { _load: ModuleLoad };

async function main() {
  process.env.FIBERY_TERMS_DOCUMENT_SECRET = "terms-secret";
  process.env.FIBERY_API_KEY = "test-api-key";

  const originalFetch = globalThis.fetch;
  const originalLoad = moduleWithLoad._load;
  const fetchCalls: string[] = [];

  moduleWithLoad._load = function patchedLoad(
    request: string,
    parent: NodeModule | null | undefined,
    isMain: boolean,
  ) {
    if (request === "server-only") {
      return {};
    }

    return originalLoad(request, parent, isMain);
  };

  globalThis.fetch = (async (input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    fetchCalls.push(url);

    if (url.includes("/api/documents/terms-secret")) {
      return new Response(
        JSON.stringify({
          content:
            '<p><img src="/api/files/legal/terms-banner.png" alt="Terms banner" /></p>',
        }),
        {
          status: 200,
          headers: {
            "content-type": "application/json",
          },
        },
      );
    }

    if (url.includes("/api/files/legal/terms-banner.png")) {
      return new Response("banner-bytes", {
        status: 200,
        headers: {
          "cache-control": "public, max-age=3600",
          "content-type": "image/png",
        },
      });
    }

    throw new Error(`Unexpected fetch: ${url}`);
  }) as typeof fetch;

  try {
    const { getTermsHtml } = await import("@/lib/legal/fibery-documents");
    const { GET } = await import("@/app/api/legal/fibery-file/route");

    const htmlResult = await getTermsHtml();
    assert.equal(htmlResult.ok, true);
    if (htmlResult.ok) {
      assert.match(
        htmlResult.html,
        /\/api\/legal\/fibery-file\?doc=terms&amp;path=%2Fapi%2Ffiles%2Flegal%2Fterms-banner\.png/,
      );
    }

    fetchCalls.length = 0;

    const allowedUrl = new URL("https://example.com/api/legal/fibery-file");
    allowedUrl.searchParams.set("doc", "terms");
    allowedUrl.searchParams.set("path", "/api/files/legal/terms-banner.png");

    const allowedResponse = await GET(new NextRequest(allowedUrl.toString()));
    assert.equal(allowedResponse.status, 200);
    assert.equal(fetchCalls.length, 1);
    assert.equal(
      fetchCalls[0],
      "https://parliament-connect.fibery.io/api/files/legal/terms-banner.png",
    );
    assert.equal(allowedResponse.headers.get("content-type"), "image/png");

    fetchCalls.length = 0;

    const blockedUrl = new URL("https://example.com/api/legal/fibery-file");
    blockedUrl.searchParams.set("doc", "terms");
    blockedUrl.searchParams.set("path", "/api/files/admin/secret.pdf");

    const blockedResponse = await GET(new NextRequest(blockedUrl.toString()));
    assert.equal(blockedResponse.status, 403);
    assert.equal(fetchCalls.length, 0);

    // --- Step 13: double-encoded path traversal ---
    fetchCalls.length = 0;

    const doubleEncodedUrl = new URL("https://example.com/api/legal/fibery-file");
    doubleEncodedUrl.searchParams.set("doc", "terms");
    doubleEncodedUrl.searchParams.set("path", "/api/files/legal/%252e%252e/admin/secret.pdf");

    const doubleEncodedResponse = await GET(new NextRequest(doubleEncodedUrl.toString()));
    assert.ok(
      doubleEncodedResponse.status === 400 || doubleEncodedResponse.status === 403,
      `double-encoded traversal not blocked: ${doubleEncodedResponse.status}`,
    );
    assert.equal(fetchCalls.length, 0, "double-encoded traversal should not trigger upstream fetch");

    fetchCalls.length = 0;

    const singleEncodedUrl = new URL("https://example.com/api/legal/fibery-file");
    singleEncodedUrl.searchParams.set("doc", "terms");
    singleEncodedUrl.searchParams.set("path", "/api/files/legal/%2e%2e/admin/secret.pdf");

    const singleEncodedResponse = await GET(new NextRequest(singleEncodedUrl.toString()));
    assert.ok(
      singleEncodedResponse.status === 400 || singleEncodedResponse.status === 403,
      `single-encoded traversal not blocked: ${singleEncodedResponse.status}`,
    );
    assert.equal(fetchCalls.length, 0, "single-encoded traversal should not trigger upstream fetch");

    // --- SVG content-type denylist test ---
    // SVG can embed JavaScript and execute in the app's origin — must be forced to download.
    fetchCalls.length = 0;

    globalThis.fetch = (async (input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      fetchCalls.push(url);

      if (url.includes("/api/files/legal/terms-banner.png")) {
        return new Response("<svg>malicious</svg>", {
          status: 200,
          headers: {
            "cache-control": "public, max-age=3600",
            "content-type": "image/svg+xml",
          },
        });
      }

      throw new Error(`Unexpected fetch: ${url}`);
    }) as typeof fetch;

    const svgUrl = new URL("https://example.com/api/legal/fibery-file");
    svgUrl.searchParams.set("doc", "terms");
    svgUrl.searchParams.set("path", "/api/files/legal/terms-banner.png");

    const svgResponse = await GET(new NextRequest(svgUrl.toString()));
    assert.equal(svgResponse.status, 200);
    assert.equal(
      svgResponse.headers.get("content-type"),
      "application/octet-stream",
      "SVG should be forced to octet-stream",
    );
    assert.equal(
      svgResponse.headers.get("content-disposition"),
      "attachment",
      "SVG should be forced to download",
    );
    console.log("SVG content-type denylist: passed");
  } finally {
    globalThis.fetch = originalFetch;
    moduleWithLoad._load = originalLoad;
  }

  console.log("legal fibery file route allowlist checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
