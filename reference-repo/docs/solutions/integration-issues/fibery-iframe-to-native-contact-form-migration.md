---
title: "Replace Fibery iframe contact form with native Next.js form"
category: integration-issues
date: 2026-03-12
tags:
  - contact-form
  - iframe-replacement
  - server-actions
  - fibery-api
  - zod-validation
  - layout-fix
  - e2e-testing
  - rsc-mocking
affected_components:
  - app/(publicPages)/contact/
  - app/(publicPages)/layout.tsx
  - app/actions/contact.ts
  - schemas/contactSchema.ts
  - tests/e2e/contact/
problem_type: iframe-dependency-and-layout-regression
severity: medium
---

# Replace Fibery Iframe Contact Form with Native Next.js Form

## Problem

The contact page embedded a third-party Fibery form via a raw `<iframe>` with a hardcoded 1200px height. This created several issues:
- Unstyled relative to the rest of the site
- Could not be validated or tested with Playwright
- Lacked accessibility/keyboard support
- Exposed the Fibery dependency directly to the client
- The old `components/contact-form.tsx` was a broken placeholder with `console.log` debugging and `alert("Message sent successfully!")` as submission logic

Additionally, the public pages layout used a bare fragment (`<>...</>`) instead of a flex column container, causing the footer to float up on short-content pages.

## Root Cause

1. **External iframe dependency** -- no control over styling, validation, accessibility, or testability
2. **Missing layout structure** -- React fragments produce no DOM node, so flexbox cannot push the footer down

## Solution

### 1. Native Contact Form (commit `4dd588e`)

Three layers replacing the iframe:

**Zod schema** (`schemas/contactSchema.ts`):
- `contactName` (required, trimmed, max 200)
- `contactEmail` (required, valid email, lowercased, max 254)
- `phoneNumber` (optional, regex `^[0-9+\-() ]*$`, max 20)
- `message` (required, trimmed, max 5000)

**Server Action** (`app/actions/contact.ts`):
- `"use server"` + `import "server-only"`
- Re-validates with `contactSchema.safeParse()` server-side
- Calls Fibery API (`fibery.entity/create`) to create "Website Enquiries/Enquiry" entity
- Uses `AbortSignal.timeout(10_000)` for request timeout
- Returns discriminated union: `{ success: true } | { success: false; error: string }`
- Logs errors to Glitchtip via `ErrorLogger`

```ts
body: JSON.stringify([{
  command: "fibery.entity/create",
  args: {
    type: "Website Enquiries/Enquiry",
    entity: {
      "Website Enquiries/Name": parsed.data.contactName,
      "Website Enquiries/Contact Name": parsed.data.contactName,
      "Website Enquiries/Contact Email": parsed.data.contactEmail,
      "Website Enquiries/Phone number": parsed.data.phoneNumber || "",
      "Website Enquiries/Message": parsed.data.message,
      "Website Enquiries/Status": { "fibery/id": FIBERY_STATUS_NEW_ID },
    },
  },
}]),
```

**Client component** (`app/(publicPages)/contact/components/contact-form.tsx`):
- React Hook Form + `zodResolver(contactSchema)` with `mode: "onBlur"`
- Calls server action directly (Next.js handles the RPC)
- Success state swaps form for a thank-you screen
- Disables all inputs during submission to prevent double-submit
- Uses only Shadcn/ui Form components

### 2. Footer Layout Fix (commit `19371cd`)

```diff
- <>
+ <div className="flex min-h-screen flex-col">
      <AuthNavHeader />
-     <main id="main-content">
+     <main id="main-content" className="flex flex-1 flex-col">
          {children}
      </main>
      <FooterSection />
- </>
+ </div>
```

### 3. E2E Tests with RSC Server Action Mocking (commit `aa573cd`)

The key insight: Next.js server actions are POST requests to the page URL with a `next-action` header. The response uses `text/x-component` content type with a specific wire format:

```ts
function buildRscBody(result: object): string {
  const ts = Date.now();
  return `:N${ts}\n0:{"a":"$@1","f":"","b":"development"}\n1:D{"time":0.1}\n1:${JSON.stringify(result)}\n`;
}

const RSC_HEADERS = {
  "x-action-revalidated": "[[],0,0]",
  vary: "rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch",
  cache-control: "no-store, must-revalidate",
};
```

Route interception checks both method and header:
```ts
await page.route("**/contact", async (route) => {
  const req = route.request();
  if (req.method() === "POST" && req.headers()["next-action"]) {
    await route.fulfill({ status: 200, contentType: "text/x-component", headers: RSC_HEADERS, body: buildRscBody(result) });
  } else {
    await route.continue();
  }
});
```

**19 tests** across 3 categories: Expected Pass (6), Expected Fail (7), Edge Cases (6).

## Gotchas

1. **RSC wire format is fragile** -- captured from real Next.js 15/Turbopack responses. May break on Next.js upgrades. Re-capture from real response if tests fail after upgrade.

2. **`x-action-revalidated` header is required** -- without it, Next.js may not process the server action response correctly.

3. **Shadcn FormControl + Radix Slot breaks `getByLabel()`** -- use attribute selectors instead: `input[autocomplete="name"]`, `input[type="email"]`, `input[type="tel"]`, `textarea`.

4. **Use `data-slot` selectors for Shadcn alert components** -- `[data-slot='alert']` is more stable than class-based selectors.

5. **`page.unroute()` before re-mocking** for retry flows (error then success).

6. **`.trim().min(1)` catches whitespace-only input** -- critical for required string fields.

## Prevention Strategies

- **Always keep external API calls server-side** via server actions with `"use server"` + `"server-only"`. Never expose API keys to the client.
- **Dual-validate** with the same Zod schema on client and server.
- **Use discriminated union return types** for server actions instead of throwing errors.
- **Timeout external API calls** with `AbortSignal.timeout()`.
- **Every layout with a footer must use** `flex min-h-screen flex-col` + `flex-1` on main. Never use fragments as layout wrappers.
- **Extract RSC mocking helpers** into shared test utils when more server actions need E2E tests.
- **Use `mode: "onBlur"` validation** for forms -- immediate feedback without being intrusive.

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `schemas/contactSchema.ts` | Created | Zod validation schema |
| `app/actions/contact.ts` | Created | Server action calling Fibery API |
| `app/(publicPages)/contact/components/contact-form.tsx` | Created | Native form client component |
| `app/(publicPages)/contact/page.tsx` | Modified | Server component page |
| `app/(publicPages)/contact/loading.tsx` | Modified | Skeleton matching new layout |
| `app/(publicPages)/layout.tsx` | Modified | Flex column layout for footer |
| `components/contact-form.tsx` | Deleted | Old broken placeholder |
| `docker-compose.development.yml` | Modified | Added FIBERY_API_KEY env var |
| `tests/e2e/contact/contact-form.spec.ts` | Created | 19 E2E tests with RSC mocking |
| `tests/e2e/pages/contact.page.ts` | Created | Page Object Model |

## Related

- Brainstorm: `docs/brainstorms/2026-03-11-native-contact-form-brainstorm.md`
- E2E conventions: `tests/e2e/CLAUDE.md`
- Other server actions: `app/actions/auth.ts`, `app/actions/user.ts` (same pattern)
- Other Zod schemas: `schemas/authSchema.ts`, `schemas/settingsSchema.ts`
