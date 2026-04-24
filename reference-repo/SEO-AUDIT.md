# SEO Audit Report - Parliament Connect (Public Pages)

**Date:** 2026-02-26
**Site:** parliamentconnect.com
**Type:** SaaS Platform (AI-powered parliamentary clip management)
**Framework:** Next.js 15 (App Router) + Supabase
**Scope:** Public pages only (crawlable by search engines)
**Overall Score: 6.4/10**

> **Note on private pages:** Pages behind authentication (`/dashboard/*`, `/setup/*`, etc.) are correctly blocked by `robots.txt` and not audited here. SEO doesn't matter for them since crawlers can't access them. The only edge case would be OG tags for link previews when someone shares a dashboard URL in Slack/email - but that's a UX concern, not SEO.

---

## Executive Summary

Parliament Connect has **strong technical SEO foundations** - robots.txt, sitemap, security headers, and cache headers are all excellent. The `/clips/[clipId]` page is a gold standard example of dynamic metadata with OG video tags and Twitter cards.

However, the **majority of public pages lack page-specific metadata** and rely entirely on root layout defaults. There is **zero structured data (JSON-LD)** across the entire site, and **no default OG image** for social sharing. The pricing page has a **duplicate H1 tag**.

### Top 5 Priority Fixes

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 1 | Add page-specific metadata to pricing, contact, homepage | High | Low |
| 2 | Add `metadataBase` to root layout (enables canonical URLs) | High | 1 line |
| 3 | Fix duplicate H1 on pricing page | High | 1 line |
| 4 | Add default OG image for social sharing | High | Low |
| 5 | Add JSON-LD structured data (VideoObject on clips) | High | Medium |

---

## Public Pages Inventory

### Crawlable & Indexed Pages

| Route | Purpose | In Sitemap | Has Custom Metadata |
|-------|---------|-----------|-------------------|
| `/` | Homepage / landing | Yes (priority 1.0) | NO - inherits root |
| `/plan-and-pricing` | Pricing tiers | **NO - missing** | NO - inherits root |
| `/contact` | Contact form (Fibery iframe) | Yes (priority 0.8) | NO - inherits root |
| `/clips/[clipId]` | Public clip viewer | Yes (dynamic, priority 0.7) | **YES - excellent** |

### Crawlable but Blocked by robots.txt (correct)

| Route | Purpose | Blocked |
|-------|---------|---------|
| `/signin` | Auth page | Yes |
| `/signup` | Auth page | Yes |
| `/teams/invite/[token]` | Team invitations | Yes |

### Other Public Pages

| Route | Purpose | Issue |
|-------|---------|-------|
| `/embed/clip/[clipId]` | Embeddable clip player | Has `noindex, nofollow` - correct |
| `/test-posthog` | Dev/test page | **NOT blocked by robots.txt - should be** |

---

## 1. Crawlability & Indexation

### robots.txt - EXCELLENT (9/10)

**File:** `app/robots.ts`

- Environment-aware: blocks all crawling on localhost and staging (`themp.veedoo.dev`)
- Production correctly allows `/` while blocking private routes
- Sitemap reference included
- All private routes properly blocked: `/dashboard/*`, `/setup/*`, `/mp-setup/*`, `/team-setup/*`, `/api/*`, `/auth/*`, `/signin/*`, `/signup/*`, `/teams/invite/*`

**Issue found:**
| Issue | Impact | Fix |
|-------|--------|-----|
| `/test-posthog` not blocked | Low | Add `/test-posthog` to disallow list |

### XML Sitemap - GOOD (8/10)

**File:** `app/sitemap.ts`

- Dynamic clip URLs from database with pagination (1000 per page)
- Proper `lastModified` timestamps from `updated_at`
- Environment-aware (production only)
- Good priority levels: Home (1.0), Contact (0.8), Clips (0.7)

**Issue found:**
| Issue | Impact | Fix |
|-------|--------|-----|
| `/plan-and-pricing` missing from sitemap | Medium | Add as static entry with priority 0.8 |

---

## 2. Technical Foundations

### Security Headers - EXCELLENT (10/10)

All in `next.config.ts`:

| Header | Value |
|--------|-------|
| X-Content-Type-Options | `nosniff` |
| Referrer-Policy | `strict-origin-when-cross-origin` |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` |
| X-Frame-Options | `DENY` (except `/embed` routes) |

### Cache Headers - EXCELLENT (10/10)

| Resource | Cache-Control |
|----------|--------------|
| Static assets | `public, max-age=604800, stale-while-revalidate=86400` |
| `_next/static` (hashed) | `public, max-age=31536000, immutable` |
| Optimized images | `public, max-age=86400` |

### Font Loading - GOOD (8/10)

- Uses `next/font/google` (self-hosted, no external CDN calls)
- Three fonts: Inter, Playfair Display, Fira Code
- Latin subset only (optimized)
- CSS variables approach (zero CLS from fonts)

### Image Optimization - GOOD (7/10)

- `next/image` configured with 6 remote patterns (Supabase, DigitalOcean CDN, Parliament.uk)
- 1-day minimum cache TTL
- Hero uses native `<video>` with `preload="metadata"` and poster image

| Issue | Impact | Fix |
|-------|--------|-----|
| Logo alt text is generic (`"Logo"`) | Low | Change to `"Parliament Connect"` |
| Logo missing `priority` prop | Low | Add `priority={true}` (above-fold image) |

### Error Pages - EXCELLENT (10/10)

- Custom 404 (`not-found.tsx`): recovery links, popular pages, contact support
- Custom error (`error.tsx`): Glitchtip logging, retry button, error ID
- Global error (`global-error.tsx`): root-level fallback with critical severity logging

### Third-Party Scripts - GOOD (9/10)

| Service | Loading | Impact |
|---------|---------|--------|
| PostHog | Client-side, production only, proxied through same domain | Non-blocking |
| Glitchtip/Sentry | Server instrumentation + client config | Non-blocking |

### Missing Technical Elements

| Element | Status | Priority |
|---------|--------|----------|
| `metadataBase` in root layout | Missing | **High** - needed for canonical URLs |
| `viewport` export in root layout | Missing (relies on Next.js default) | Low |
| `app/manifest.ts` | Missing | Medium - PWA/icon config |
| Default `opengraph-image.png` | Missing | **High** - social sharing fallback |
| Skip-to-content link | Missing | Medium - accessibility |

---

## 3. Page-by-Page On-Page SEO Audit

### Homepage `/`

**Metadata:** Inherits root layout only (no custom export)

**Root layout metadata:**
```
Title: "Parliament Connect - Transform Your Parliamentary Voice Into Social Impact" (73 chars - slightly long)
Description: "AI-powered platform for UK MPs and staff to create, search, and share video clips..." (157 chars - good)
Keywords: "parliament, MP, AI, video clips, social media, UK politics, parliament sessions, content creation"
OG Title: Same as title
OG Description: "Transform parliament sessions into powerful social media content with AI-powered tools."
OG Type: "website"
OG Image: MISSING
Twitter Card: MISSING
```

**Heading Structure:**
```
H1: "Transform Your Parliamentary Voice Into Social Impact"
  H2: "Powerful Features Built for MPs"
    H3: "Automated Speech Discovery"
    H3: "AI-Powered Transcription"
    H3: "Intelligent Video Editing"
    H3: "Multi-Platform Publishing"
  H2: "How It Works" (via aria-labelledby)
    H3: "Complete Workflow Timeline"
  H4: "Ready to See It in Action?"                  <- hierarchy skip (H2 would be better)
```

**Content Quality:** Strong - clear value prop, feature bullets, 5-step workflow, social proof (150+ MPs), CTA

**Semantic HTML:** Excellent - `<section>` with `aria-labelledby`, `<main id="main-content">`, `<nav role="navigation">`, `<footer role="contentinfo">`

**Issues:**
| Issue | Impact | Fix |
|-------|--------|-----|
| No OG image | High | Add default OG image |
| No Twitter card | Medium | Add Twitter metadata to root |
| CTA uses H4 (skips H3) | Low | Change to H2 |

---

### Pricing Page `/plan-and-pricing`

**Metadata:** NO custom export - inherits root layout

**Heading Structure:**
```
H1: "Choose Your Licence"                    <- DUPLICATE!
H1: "Choose Your Licence"                    <- DUPLICATE!
  H2: "The Parliament Connect Promise"
  H3: "Foundation" (£99/month)
  H3: "Professional" (£199/month)
  H3: "Premium" (£399/month - Coming Soon)
  H2: "Enterprise"
  H2: "Frequently Asked Questions"
```

**Content Quality:** Good - three pricing tiers with feature lists, 14-day money-back guarantee, 4 FAQ items, enterprise contact

**Issues:**
| Issue | Impact | Fix |
|-------|--------|-----|
| **DUPLICATE H1** - appears twice | **High** | Convert second H1 to H2 |
| No page-specific metadata | High | Add title + description |
| Not in sitemap | Medium | Add to sitemap.ts |
| No FAQ schema (has FAQ content already) | Medium | Add FAQPage JSON-LD |
| No pricing schema | Medium | Add SoftwareApplication/Offer JSON-LD |

---

### Contact Page `/contact`

**Metadata:** NO custom export - inherits root layout

**Heading Structure:**
```
H1: "Get in touch"
(Fibery iframe form - NOT crawlable)
```

**Content Quality:** Weak - H1 + external iframe only. Zero crawlable text content.

**Issues:**
| Issue | Impact | Fix |
|-------|--------|-----|
| No page-specific metadata | High | Add title: "Contact Us \| Parliament Connect" |
| **Main content is iframe** - not crawlable | High | Add contact info text above/below iframe |
| Iframe missing `title` attribute | Medium | Add `title="Contact Form"` for accessibility |
| Email only in footer, not on page | Medium | Add email + context to page HTML |

---

### Public Clip Page `/clips/[clipId]` - BEST IMPLEMENTATION

**Metadata:** `generateMetadata` - **excellent**

```
Title: "{Clip Title} | Parliament Connect"
Description: Truncated to 160 chars from clip description/transcript
OG Title: Dynamic
OG Description: Dynamic (160 chars)
OG URL: Full canonical URL
OG siteName: "Parliament Connect"
OG Type: "video.other"
OG Image: Thumbnail (1280x720) with alt text
OG Video: MP4 URL (1280x720)
Twitter Card: "summary_large_image" with image
```

**Content Quality:** Strong - dynamic title, full transcript text (indexable), MP info, session metadata

**Issues:**
| Issue | Impact | Fix |
|-------|--------|-----|
| No JSON-LD VideoObject schema | High | Add structured data for video rich results |
| Missing `<article>` wrapper | Low | Wrap clip content in `<article>` |

---

## 4. Structured Data (JSON-LD)

### Status: NOT IMPLEMENTED (0/10)

Zero structured data found across the entire codebase.

### Recommended Schemas (by priority)

**1. VideoObject** - `/clips/[clipId]` (highest value - enables video rich results)
```json
{
  "@context": "https://schema.org",
  "@type": "VideoObject",
  "name": "Clip Title",
  "description": "...",
  "thumbnailUrl": "https://...",
  "uploadDate": "2026-01-15T00:00:00Z",
  "duration": "PT2M30S",
  "contentUrl": "https://...",
  "embedUrl": "https://parliamentconnect.com/embed/clip/...",
  "actor": { "@type": "Person", "name": "MP Name", "jobTitle": "Member of Parliament" }
}
```

**2. Organization** - root layout or homepage
```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Parliament Connect",
  "url": "https://parliamentconnect.com",
  "logo": "https://parliamentconnect.com/icon.svg",
  "email": "info@parliamentconnect.com"
}
```

**3. FAQPage** - `/plan-and-pricing` (already has 4 FAQ items)
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    { "@type": "Question", "name": "Does this comply with ParliamentLive.tv rules?", "acceptedAnswer": { "@type": "Answer", "text": "..." } }
  ]
}
```

**4. SoftwareApplication + Offer** - `/plan-and-pricing`
```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Parliament Connect",
  "applicationCategory": "BusinessApplication",
  "offers": [
    { "@type": "Offer", "name": "Foundation", "price": "99", "priceCurrency": "GBP" }
  ]
}
```

---

## 5. Open Graph & Social Sharing

| Page | OG Title | OG Desc | OG Image | OG Video | Twitter Card |
|------|----------|---------|----------|----------|-------------|
| Root (inherited by all) | Yes | Yes | **NO** | N/A | **NO** |
| `/clips/[clipId]` | Yes (dynamic) | Yes (dynamic) | Yes (thumbnail) | Yes (MP4) | Yes |
| All other public pages | Inherit root | Inherit root | **NO** | N/A | **NO** |

**Issues:**
| Issue | Impact | Fix |
|-------|--------|-----|
| No default OG image | **High** | Create `app/opengraph-image.png` (1200x630) |
| No Twitter card in root | **High** | Add `twitter: { card: "summary_large_image" }` |
| No `metadataBase` | **High** | Add `metadataBase: new URL('https://parliamentconnect.com')` |
| No `siteName` in root OG | Low | Add `siteName: "Parliament Connect"` |

---

## 6. Accessibility (SEO-relevant)

### Strengths
- `<main id="main-content">` in public layout
- `<nav role="navigation" aria-label="Main navigation">`
- `<footer role="contentinfo">`
- `<section>` elements with `aria-labelledby` linked to heading IDs
- Hero video has descriptive `aria-label`
- Form fields have labels and descriptions

### Issues
| Issue | Impact | Fix |
|-------|--------|-----|
| No skip-to-content link | Medium | Add as first element in public layout |
| Contact iframe missing `title` | Medium | Add `title="Contact Form"` |
| Clip page missing `<article>` wrapper | Low | Wrap content in `<article>` |

---

## 7. Internal Linking

```
Header:   /#features | /#how-it-works | /plan-and-pricing | /contact | /signin
Footer:   / (logo) | Privacy Policy (external Fibery) | mailto:info@parliamentconnect.com
Hero CTA: /contact (Request Demo)
Pricing:  /signup (x3 plan CTAs) | /contact (enterprise)
Clips:    / (logo) | Twitter/Facebook/LinkedIn share intents
404:      / | /dashboard | /signin | /signup | /contact
```

- No broken links found
- No `href="#"` dead links on public pages
- Social share buttons use proper intent URLs
- Privacy policy hosted externally (Fibery) - minor link equity loss

---

## 8. Content & E-E-A-T Gaps

| Gap | Impact | Recommendation |
|-----|--------|---------------|
| No blog/resources section | High | Create `/blog` for organic keyword targeting |
| No About/Team page | Medium | Build trust with team credentials |
| No Terms of Service page | Medium | Legal requirement + trust signal |
| Contact page has no text content (iframe only) | Medium | Add contact info in HTML |
| Missing keywords: "Westminster", "House of Commons", "Hansard" | Medium | Incorporate into meta descriptions |
| No case studies or testimonials | Low | Strengthen social proof |

---

## Scoring Breakdown

| Category | Score | Weight | Weighted |
|----------|-------|--------|----------|
| Crawlability & Indexation (robots, sitemap) | 9/10 | 20% | 1.80 |
| Technical Foundations (headers, speed, errors) | 9/10 | 15% | 1.35 |
| Page Titles & Meta Descriptions | 4/10 | 15% | 0.60 |
| Structured Data (JSON-LD) | 0/10 | 10% | 0.00 |
| Open Graph & Social Sharing | 4/10 | 10% | 0.40 |
| Content Quality & E-E-A-T | 5/10 | 10% | 0.50 |
| Heading Structure | 6/10 | 5% | 0.30 |
| Internal Linking | 8/10 | 5% | 0.40 |
| Accessibility (SEO-relevant) | 7/10 | 5% | 0.35 |
| Image Optimization | 7/10 | 5% | 0.35 |
| **TOTAL** | | **100%** | **6.05/10** |

---

## Prioritized Action Plan

### Week 1 - Critical Fixes (~2-3 hours)

- [ ] Add `metadataBase: new URL('https://parliamentconnect.com')` to root layout
- [ ] Add default OG image (`app/opengraph-image.png` - 1200x630)
- [ ] Add Twitter card metadata to root layout
- [ ] Add page-specific metadata to `/plan-and-pricing` (title + description)
- [ ] Add page-specific metadata to `/contact` (title + description)
- [ ] Fix **duplicate H1** on pricing page
- [ ] Add `/plan-and-pricing` to sitemap.ts
- [ ] Add `/test-posthog` to robots.txt disallow

### Week 2 - High-Impact Improvements (~4-6 hours)

- [ ] Add JSON-LD `VideoObject` schema to `/clips/[clipId]`
- [ ] Add JSON-LD `Organization` schema to root layout
- [ ] Add JSON-LD `FAQPage` schema to pricing page
- [ ] Add contact info text to contact page (above/below iframe)
- [ ] Add `title="Contact Form"` to contact page iframe
- [ ] Add skip-to-content link to public layout
- [ ] Change logo alt text to `"Parliament Connect"`
- [ ] Add `viewport` export to root layout

### Week 3 - Polish (~2-3 hours)

- [ ] Create `app/manifest.ts`
- [ ] Add `priority={true}` to logo Image component
- [ ] Add `<article>` wrapper on clip page content
- [ ] Fix CTA heading hierarchy (H4 -> H2)
- [ ] Add `siteName` to root OG metadata
- [ ] Add JSON-LD `SoftwareApplication` to pricing page

### Long-Term

- [ ] Create `/blog` or `/resources` for content marketing
- [ ] Create About/Team page
- [ ] Create Terms of Service page
- [ ] Host privacy policy on domain
- [ ] Add breadcrumb navigation with schema
- [ ] Expand keyword targeting ("Westminster", "House of Commons", "Hansard")
- [ ] Replace contact iframe with native form

---

## File Reference

| File | SEO Purpose |
|------|-------------|
| `app/layout.tsx` | Root metadata, fonts, OG tags |
| `app/robots.ts` | Crawler rules |
| `app/sitemap.ts` | Sitemap generation |
| `app/clips/[clipId]/page.tsx` | Best metadata example (use as template) |
| `app/(publicPages)/(homePage)/page.tsx` | Homepage content |
| `app/(publicPages)/plan-and-pricing/page.tsx` | Pricing page (duplicate H1) |
| `app/(publicPages)/contact/page.tsx` | Contact page (iframe issue) |
| `app/(publicPages)/layout.tsx` | Public pages layout wrapper |
| `next.config.ts` | Security/cache headers, image config |
| `components/logo.tsx` | Logo component (alt text issue) |
