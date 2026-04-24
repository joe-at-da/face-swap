# Native Contact Form — Replace Fibery Iframe

**Date**: 2026-03-11
**Status**: Ready for planning

## What We're Building

Replace the Fibery iframe on the `/contact` page with a native, mobile-friendly contact form that submits data to the same Fibery database (`Website Enquiries/Enquiry`) via the Fibery API.

### Form Fields

| Field | Type | Required | Fibery Field Name |
|-------|------|----------|-------------------|
| Contact Name | text | yes | `Website Enquiries/Contact Name` |
| Contact Email | email | yes | `Website Enquiries/Contact Email` |
| Phone number | tel | no | `Website Enquiries/Phone number` |
| Message | textarea | yes | `Website Enquiries/Message` |

On submission, set `Website Enquiries/Status` to "New" via the enum name.

### Post-Submission UX

On success, replace the form with an inline thank-you message (e.g., "Thanks for reaching out! We'll be in touch shortly."). On error, show an inline error message and keep the form populated so the user can retry.

### Fibery API Details

- **Workspace**: `parliament-connect.fibery.io`
- **Entity type**: `Website Enquiries/Enquiry`
- **API endpoint**: `POST https://parliament-connect.fibery.io/api/commands`
- **Auth**: `Authorization: Token <FIBERY_API_KEY>`
- **Command**: `fibery.entity/create` with the entity type and field values
- **Also set**: `Website Enquiries/Name` (the entity title field) — use Contact Name value

## Why This Approach

- **SEO**: Iframe content is not crawlable; native form improves content quality (flagged in SEO audit)
- **Design control**: Native form follows the project's design system, theme colors, and mobile-first approach
- **Performance**: No external iframe load, faster page render
- **Consistency**: Uses same patterns as all other forms in the project (Shadcn Form + React Hook Form + Zod)
- **Security**: Fibery API key stays server-side via Next.js server action

## Key Decisions

1. **Clean build, not refactor** — The existing unused `components/contact-form.tsx` doesn't follow project conventions and will be deleted
2. **Server action for submission** — Form submits via Next.js server action, not an API route. Follows existing project patterns (e.g., `app/actions/auth.ts`)
3. **4 fields only** — Match the current Fibery form exactly: name, email, phone (optional), message. No extras
4. **Default status "New"** — Set status enum to "New" on creation
5. **Environment variable** — `FIBERY_API_KEY` stored as server-side env var (not `NEXT_PUBLIC_`)
6. **Zod schema** — New `schemas/contactSchema.ts` for validation
7. **Component placement** — Form component in `app/(publicPages)/contact/components/` (page-specific)
8. **Delete old component** — Remove unused `components/contact-form.tsx`

## Resolved Questions

- **Which Fibery fields?** — Contact Name, Contact Email, Phone number, Message (confirmed via API)
- **Default status?** — "New"
- **Architecture?** — Server action (not API route)
- **Spam protection?** — Not needed for now, keep it simple
- **Post-submission UX?** — Inline success message replacing the form; inline error with form preserved on failure
- **`Website Enquiries/Name` field?** — Set to Contact Name value (it's the entity title field in Fibery)
