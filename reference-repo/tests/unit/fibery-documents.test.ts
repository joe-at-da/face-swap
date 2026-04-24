import assert from "node:assert/strict";
import Module from "node:module";

type ModuleLoad = (
  request: string,
  parent: NodeModule | null | undefined,
  isMain: boolean,
) => unknown;

const moduleWithLoad = Module as typeof Module & { _load: ModuleLoad };

async function main() {
  process.env.FIBERY_TERMS_DOCUMENT_SECRET = "terms-secret";
  process.env.FIBERY_PRIVACY_DOCUMENT_SECRET = "privacy-secret";
  process.env.FIBERY_API_KEY = "test-api-key";

  const originalFetch = globalThis.fetch;
  const originalLoad = moduleWithLoad._load;
  const fetchCalls: Array<string> = [];

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

    if (url.includes("/api/documents/privacy-secret")) {
      return new Response(
        JSON.stringify({
          content: [
            '<p>Safe paragraph</p>',
            '<script>alert(1)</script>',
            '<img onerror="alert(1)" src="x">',
            '<a href="javascript:void(0)">click</a>',
            '<svg onload="alert(1)"><circle/></svg>',
          ].join(""),
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }

    return {
      ok: true,
      async json() {
        return {
          content:
            '<p>Read the <a href="/internal/legal">internal legal page</a>.</p>',
        };
      },
    } as Response;
  }) as typeof fetch;

  try {
    const { getTermsHtml, getPrivacyPolicyHtml } = await import("@/lib/legal/fibery-documents");
    const result = await getTermsHtml();

    assert.equal(result.ok, true);
    if (result.ok) {
      assert.equal(result.html, "<p>Read the internal legal page.</p>");
    }
    assert.equal(fetchCalls.length, 1);

    // --- Step 12: XSS sanitizer edge cases ---
    fetchCalls.length = 0;
    const xssResult = await getPrivacyPolicyHtml();
    assert.equal(xssResult.ok, true);
    if (xssResult.ok) {
      // <script> tags must be stripped entirely
      assert.equal(xssResult.html.includes("<script"), false, "script tag not stripped");
      assert.equal(xssResult.html.includes("alert(1)"), false, "alert payload not stripped");
      // onerror event handler must be stripped
      assert.equal(xssResult.html.includes("onerror"), false, "onerror attribute not stripped");
      // javascript: URI must be stripped (link removed or href dropped)
      assert.equal(xssResult.html.includes("javascript:"), false, "javascript: URI not stripped");
      // <svg> must be stripped (not in allowedTags)
      assert.equal(xssResult.html.includes("<svg"), false, "svg tag not stripped");
      assert.equal(xssResult.html.includes("onload"), false, "onload attribute not stripped");
      // Safe content must survive
      assert.equal(xssResult.html.includes("Safe paragraph"), true, "safe content was lost");
    }
  } finally {
    globalThis.fetch = originalFetch;
    moduleWithLoad._load = originalLoad;
  }

  console.log("fibery document sanitizer checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
