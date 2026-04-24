# E2E Tests for Auth-Protected Pages

**Date:** 2026-03-02
**Status:** Ready for planning

## What We're Building

Comprehensive end-to-end tests for all core user-facing auth-protected pages. This covers the full user journey: setup wizards, dashboard, clips management, settings, and auth guards.

## Scope

### In Scope (Core user-facing pages)
| Route | Test Depth |
|-------|-----------|
| `/setup` | Full multi-step wizard, dedicated `is_first_login: true` user |
| `/mp-setup` | MP auto-match, social media setup, dedicated MP test user |
| `/team-setup` | Team member setup wizard, dedicated team-member test user |
| `/no-team-access` | Page display, navigation links |
| `/dashboard` | Page load, content display, auth guard |
| `/dashboard/settings` | Profile form CRUD, notification toggles, delete account |
| `/dashboard/my-clips` | Search, filters, pagination, delete, real-time updates |
| `/dashboard/my-clips/[userClipId]` | Video player, transcript, share, download, edit dialogs |
| `/dashboard/create-clips` | Clip grid, search, date filters |
| `/dashboard/create-clips/clip/[clipId]` | Single clip detail, video, transcript |
| Auth guards | Unauthenticated redirect for all `/dashboard/*` routes |

### Out of Scope
- `/dashboard/create-clips/edit-clip/[clipId]` — Remotion canvas, hard to test
- `/dashboard/teams/*` — Team features excluded from this iteration
- `/dashboard/summaries/*` — Hardcoded data, low value
- `/dashboard/pipeline-evaluation*` — Internal Veedoo tools
- `/dashboard/portrait-*` — Internal Veedoo tools

## Key Decisions

1. **Test depth: Comprehensive functional tests** — Full CRUD flows, form validation (valid + invalid), real-time updates, pagination, filters, role-based UI
2. **Test data: Global seed + per-test factories** — Extend `global-setup.ts` for base data (parliament members, clips, user associations). Add factory helpers (`createTestClip()`, etc.) for test-specific data. Cleanup in `afterEach` + global teardown
3. **Setup flow testing: Yes, with dedicated users** — Separate `e2e-setup-*` test users with `is_first_login: true` for setup wizard tests. Cleaned up per run
4. **Video editor: Skip** — Remotion canvas rendering too complex for Playwright
5. **Organization: Page-Per-Spec** — One spec file per route, mirrors app router structure

## Test Infrastructure Needed

### New Test Users (extend global-setup.ts)
- `e2e-setup-user@test.local` — `is_first_login: true`, for `/setup` tests
- `e2e-mp-user@test.local` — Actual MP (email in `parliament_member_contacts`), for `/mp-setup`
- `e2e-team-member@test.local` — Team member with team association, for `/team-setup`

### New Factory Helpers
- `createTestParliamentMember()` — Seed a parliament member record
- `createTestClip()` — Create a clip associated with a parliament member
- `createTestUserClip()` — Create a user-created clip for my-clips tests
- `createTestFollowedMP()` — Associate a user with a followed MP
- `cleanupTestClips()` — Remove test clips

### New Page Object Models
- `setup.page.ts` — Setup wizard steps, profile form, MP selection
- `dashboard.page.ts` — Dashboard home elements
- `settings.page.ts` — Profile form, notifications, danger zone
- `my-clips.page.ts` — Clip list, search, filters, pagination
- `clip-detail.page.ts` — Video player, transcript, edit dialogs
- `create-clips.page.ts` — Clip grid, search, date filters

### New Fixtures
- `setupUserPage` — Authenticated as user with `is_first_login: true`
- `mpUserPage` — Authenticated as MP user

## File Structure

```
tests/e2e/
├── auth/                          (existing)
│   ├── sign-in.spec.ts
│   └── sign-up.spec.ts
├── setup/
│   ├── setup.spec.ts              (regular user /setup wizard)
│   ├── mp-setup.spec.ts           (/mp-setup flow)
│   ├── team-setup.spec.ts         (/team-setup flow)
│   └── no-team-access.spec.ts     (/no-team-access page)
├── dashboard/
│   ├── dashboard.spec.ts          (/dashboard home)
│   ├── settings.spec.ts           (/dashboard/settings)
│   ├── create-clips.spec.ts       (/dashboard/create-clips)
│   └── clip-detail.spec.ts        (/dashboard/create-clips/clip/[id])
├── clips/
│   ├── my-clips.spec.ts           (/dashboard/my-clips)
│   └── user-clip-detail.spec.ts   (/dashboard/my-clips/[id])
├── auth-guards/
│   └── protected-routes.spec.ts   (redirect tests for all routes)
├── pages/                         (Page Object Models)
│   ├── sign-in.page.ts            (existing)
│   ├── sign-up.page.ts            (existing)
│   ├── setup.page.ts
│   ├── dashboard.page.ts
│   ├── settings.page.ts
│   ├── my-clips.page.ts
│   ├── clip-detail.page.ts
│   └── create-clips.page.ts
├── fixtures/
│   └── test-fixtures.ts           (extended with new fixtures)
├── helpers/
│   ├── supabase-admin.ts          (existing)
│   ├── test-users.ts              (extended with new user types)
│   ├── cleanup.ts                 (extended)
│   ├── inbucket.ts                (existing)
│   └── factories/
│       ├── clip-factory.ts
│       ├── parliament-member-factory.ts
│       └── user-clip-factory.ts
└── CLAUDE.md                      (existing guide)
```

## Test Categories Per Page

### Auth Guards (`protected-routes.spec.ts`)
- Unauthenticated visit to each `/dashboard/*` route → redirects to `/`
- Unauthenticated visit to `/setup`, `/mp-setup`, `/team-setup` → redirects to `/`

### Setup Wizard (`setup.spec.ts`)
- **Pass:** Complete multi-step wizard (name → MP selection → finish → redirect to `/dashboard`)
- **Fail:** Submit empty name, skip MP selection
- **Edge:** Back/forward navigation between steps, page refresh preserves state

### Dashboard Home (`dashboard.spec.ts`)
- **Pass:** Page loads with correct heading, latest clips display, quick actions visible, recent activity visible
- **Edge:** No clips state (empty state UI), sidebar navigation works

### Settings (`settings.spec.ts`)
- **Pass:** Load settings, update profile name, update avatar, toggle notifications
- **Fail:** Empty name submission, invalid avatar format
- **Edge:** Delete account flow (confirmation dialog), cancel button

### My Clips (`my-clips.spec.ts`)
- **Pass:** List renders with clips, search by text, filter by date range, filter by status, pagination works, delete clip
- **Fail:** Search with no results shows empty state
- **Edge:** Real-time update (new clip appears), pagination boundary

### User Clip Detail (`user-clip-detail.spec.ts`)
- **Pass:** Page loads with video, transcript, metadata. Edit title dialog. Edit description dialog. Share link copy. Download section visible
- **Fail:** Invalid clip ID shows error
- **Edge:** Processing status display, real-time status update

### Create Clips (`create-clips.spec.ts`)
- **Pass:** Clip grid loads, search filters clips, date filter works
- **Fail:** Search with no results
- **Edge:** Loading states, empty state

### Clip Detail (`clip-detail.spec.ts`)
- **Pass:** Single clip loads with video, MP info, transcript
- **Fail:** Invalid clip ID

## Resolved Questions

1. **Real-time testing** → **DB insert + wait for UI.** Use `supabaseAdmin` to INSERT a record directly, then `expect(locator).toBeVisible({ timeout })` to assert the UI updates. Tests the actual real-time pipeline end-to-end.
2. **File upload** → **Test with Playwright file chooser.** Use `page.setInputFiles()` to upload a small test image for avatar. Verifies the full upload flow including Supabase storage.
3. **Video playback** → **Verify player exists + metadata.** Assert video element renders with valid `src`. Test surrounding metadata (title, transcript, MP info). Don't test play/pause/seek controls.
