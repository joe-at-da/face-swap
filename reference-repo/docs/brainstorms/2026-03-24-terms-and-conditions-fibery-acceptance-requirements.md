---
date: 2026-03-24
topic: terms-and-conditions-fibery-acceptance
---

# Terms & Conditions Page and Acceptance

## Problem Frame
Parliament Connect needs a first-party Terms & Conditions page instead of sending users to an external legal document. The content should be managed by non-developers in Fibery and update on the website when the Fibery rich text document changes. Users must explicitly agree to the Terms & Conditions before creating an account or accepting a team invitation, and that acceptance must be recorded in Supabase.

## Requirements
- R1. The product must provide a new public Terms & Conditions page on the Parliament Connect domain. This page is separate from the existing Privacy Policy and does not replace or modify the Privacy Policy in this branch.
- R2. The Terms & Conditions page must fetch its source content from the Fibery document at `Documentation/Terms-Conditions-146` using the existing Fibery API key rather than embedding static copy or linking users to the Fibery-hosted page.
- R3. The Terms & Conditions page must render Fibery rich text content in a way that preserves normal legal-document formatting and embedded media, including images and other rich content users may place in the Fibery document.
- R4. The Terms & Conditions page should show the most recently successful content fetch if Fibery is temporarily unavailable, so the page remains usable even during Fibery outages.
- R4a. If Fibery is unavailable and no cached Terms & Conditions content exists yet, the Terms & Conditions page must show a clear unavailable state on the app domain rather than redirecting users to Fibery.
- R5. The signup flow must include a required checkbox stating that the user agrees to the Terms & Conditions, with an inline link to the new Terms & Conditions page.
- R6. Users must not be able to start signup unless the Terms & Conditions checkbox is checked.
- R7. The team invitation flow must include the same required Terms & Conditions checkbox with a link to the new Terms & Conditions page.
- R8. Users must not be able to accept a team invitation through any path unless the Terms & Conditions checkbox is checked. This includes direct acceptance by an already signed-in invited user, sign-in-to-accept flows, and sign-up-from-invite flows.
- R8a. The requirement to accept Terms & Conditions must be enforced server-side during successful signup and invitation acceptance so it cannot be bypassed through client-side manipulation.
- R9. When a user successfully completes signup after checking the checkbox, the system must persist Terms & Conditions acceptance in Supabase.
- R10. When a user successfully accepts a team invitation after checking the checkbox, the system must persist Terms & Conditions acceptance in Supabase.
- R11. The stored acceptance record must include at least the user identity and acceptance timestamp. This branch does not require content-hash versioning or a manual legal version label.
- R12. Failure to load the Terms & Conditions page itself must not block signup or invitation acceptance as long as the user can still check the checkbox in the relevant flow.

## Success Criteria
- Visitors can open a first-party Terms & Conditions page on the site and see Fibery-managed content, including rich text and images.
- Visitors see a clear unavailable state on the Terms & Conditions page if Fibery content has never been fetched successfully and no cached copy exists.
- Legal/content teams can update the Fibery source document and have the site reflect those changes without a code deployment.
- Users cannot create an account or accept any invitation path without affirmatively checking the Terms & Conditions checkbox.
- Users cannot bypass the acceptance requirement by manipulating the client.
- The product stores a durable Supabase record showing that a user accepted the Terms & Conditions and when they accepted them.
- Temporary Fibery outages do not take down the Terms & Conditions page if cached content exists and do not prevent signup or invitation acceptance.

## Scope Boundaries
- This branch does not migrate the Privacy Policy to the same pattern.
- This branch does not require prompting existing already-registered users to re-accept Terms & Conditions.
- This branch does not require storing a legal version, rendered content hash, IP address, or user agent with acceptance.
- This branch does not require users to successfully open or read the Terms & Conditions page before proceeding; only explicit checkbox consent is required.

## Key Decisions
- Acceptance must be persisted in Supabase: Legal acceptance needs a durable backend record rather than only client-side validation.
- The Terms page must live on the app domain: The legal experience should be first-party and controlled by the app rather than redirecting users to Fibery.
- Cached fallback content should be shown when Fibery is unavailable: This keeps the page usable without turning Fibery availability into a signup blocker.
- Acceptance applies to every invite-accept path: Existing users joining by invitation must also explicitly agree before continuing.
- Acceptance storage is timestamp-only for now: This keeps the initial scope smaller and avoids introducing version-management workflow in this branch.

## Dependencies / Assumptions
- A working Fibery API key is available to the app in this environment.
- The referenced Fibery document remains the source of truth for Terms & Conditions content.
- Supabase is the system of record for user acceptance data.

## Outstanding Questions

### Deferred to Planning
- [Affects R2, R3, R4][Needs research] The planner should inspect the actual Fibery Terms & Conditions document and Fibery API response shape to determine how the rich text content and referenced media can be rendered faithfully on the app page.
- [Affects R4][Technical] Where should the cached last-successful Terms content live and what invalidation or refresh strategy best fits the current Next.js architecture?
- [Affects R9, R10, R11][Technical] Should acceptance be stored as fields on the user/profile record, as a dedicated acceptance table, or both?
- [Affects R7, R8, R10][Technical] At which exact step in each invitation path should acceptance be validated and written so the record is durable and not bypassable?

## Next Steps
→ /prompts:ce-plan for structured implementation planning
