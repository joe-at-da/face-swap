---
date: 2026-02-04
topic: facebook-page-selection
---

# Facebook Page Selection During Connection

## What We're Building

When users connect their Facebook account, they need to select which Facebook Page to post to. Currently, the OAuth flow completes but leaves the integration in an `inBetweenSteps=true` state because no page is selected, causing all posts to fail with "No permission to publish the video" error.

We're adding a page selection step that appears **in the same popup window** immediately after Facebook OAuth completes. Users will see a dropdown of their authorized Pages and select one. Only then will the integration be marked as complete.

## Why This Approach

**Approaches Considered:**

1. **Page selection during connection** (Chosen) - Clean, one-time setup, no friction when posting
2. **Page selection at post time** - More flexible but adds dropdown to every share action
3. **Multiple integrations per page** - Complex, clutters the UI with multiple Facebook entries

**We chose option 1 because:**
- Simplest user experience - connect once, post many times
- Matches how other platforms work (connect → done)
- Avoids adding complexity to the share dialog
- If user wants different pages, they can disconnect and reconnect

## Key Decisions

- **When**: Page selection happens during connection, not at post time
- **Where**: Same OAuth popup window, after Facebook OAuth redirects back
- **Multi-page handling**: User picks ONE page from their authorized pages. To use a different page, they disconnect and reconnect.
- **UI Pattern**: Follow the Bluesky pattern - custom route that handles the multi-step flow instead of generic OAuth

## Technical Approach

### Postiz API Endpoints Discovered

1. **OAuth Callback** (`POST /integrations/social-connect/facebook`):
   - Handles OAuth response
   - For `inBetweenSteps=true` providers, returns `{ ...integrationData, pages: [...] }`
   - The `pages` array contains available Facebook Pages

2. **Page Selection** (`POST /integrations/provider/{id}/connect`):
   - Body: `{ state: "...", page: "pageId" }`
   - Calls `fetchPageInformation(accessToken, { page: pageId })`
   - Updates integration with page's `access_token`, `name`, `picture`, etc.
   - Sets `inBetweenSteps=false`

### Facebook Page Data Format

```typescript
// From Postiz facebook.provider.ts pages() method
interface FacebookPage {
  id: string;           // Page ID
  name: string;         // Page name
  username?: string;    // Page username
  picture: {
    data: {
      url: string;      // Profile picture URL
    };
  };
}
```

### Implementation Plan

1. **Create `/api/oauth/facebook/callback` route** that:
   - Receives OAuth callback from Postiz (after user authorizes on Facebook)
   - Calls Postiz `POST /integrations/social-connect/facebook` to exchange code
   - If response includes `pages` array → render page selection UI
   - If no pages needed → redirect/close as normal

2. **Create Page Selection UI Component**:
   - Render in the callback route as HTML/React
   - Show dropdown/list of available pages with profile pictures
   - On selection, call `POST /integrations/provider/{id}/connect` with `{ page: selectedPageId }`
   - Close popup and trigger parent window refresh

3. **Modify OAuth Flow for Facebook**:
   - In `/api/oauth/start`, detect if platform is `facebook`
   - Set our custom callback URL instead of Postiz default
   - Postiz OAuth URL already includes redirect_uri parameter

## Open Questions

- ~~What Postiz API endpoint returns the list of available Facebook Pages?~~ **ANSWERED**: `POST /integrations/social-connect/facebook` returns `pages` array in response
- ~~What Postiz API endpoint completes the page selection?~~ **ANSWERED**: `POST /integrations/provider/{id}/connect` with `{ state, page }` body
- Does the same pattern apply to YouTube? **YES** - YouTube also has `inBetweenSteps=true` for channel selection

## Next Steps

→ `/workflows:plan` for implementation details
