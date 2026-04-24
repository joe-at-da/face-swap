# Brainstorm: New Clips Available Notification

**Date:** 2026-02-23
**Status:** Ready for planning

## What We're Building

An hourly scheduled job that detects new parliament_member_clips (with descriptions) and sends email notifications to relevant users — the MP's own staff and team members of teams owned by users following that MP.

The email uses the existing `emails/new-content-added.tsx` template. Since clips don't have a `title` field, titles are generated via AI (gpt-4o-mini) from the clip transcript, framed for MP staff who want to know what their MP said.

## Why This Approach

- **Hourly cron via Coolify** — Matches existing cron job patterns in the codebase (parliament-sync, daily-task, etc.). User adds the schedule in Coolify dashboard manually.
- **notification_sent_at column** — Simple idempotency at the clip level. NULL = not yet processed. Existing 10k+ clips get backfilled with NOW() so they're skipped.
- **clip_notification_log table** — Precise per-user+clip tracking so failed sends retry only for the specific user who failed.
- **Owner's member_id for teams** — Simpler than using team_mp_follows. A team member gets notified if the team owner's user_roles.member_id matches the clip's member_id.

## Key Decisions

### 1. Idempotency (Two-Layer)

**Layer 1 — Clip level:** Add `notification_sent_at TIMESTAMPTZ` to `parliament_member_clips`. Backfill all existing rows with `NOW()`. Only clips where `notification_sent_at IS NULL AND description IS NOT NULL` are candidates.

**Layer 2 — User+clip level:** New `clip_notification_log` table:
- `id` (UUID, PK)
- `clip_id` (FK to parliament_member_clips)
- `user_id` (FK to auth.users)
- `sent_at` (TIMESTAMPTZ)
- Unique constraint on (clip_id, user_id)

Flow:
1. Find clips where `notification_sent_at IS NULL AND description IS NOT NULL`
2. For each clip, find eligible users not already in `clip_notification_log`
3. Send email, then insert into `clip_notification_log`
4. After ALL users for a clip are logged, set `notification_sent_at` on the clip

### 2. User Targeting

- **Direct:** `user_roles.member_id = clip.member_id AND new_clips_available = true`
- **Via team:** user is in `team_members` of a `team` where the owner's `user_roles.member_id = clip.member_id` AND user's own `user_roles.new_clips_available = true`
- **Deduplicate** by user_id — each user gets one email even if they match via multiple paths
- **Opt-out rule:** The team owner's `member_id` determines *which MP's clips* trigger the notification, but each individual user's `user_roles.new_clips_available` determines *whether they receive it*. A user with `new_clips_available = false` NEVER gets the email, regardless of team membership. This is the per-user opt-out mechanism.

### 3. Email Grouping

One email per user with ALL their new clips. The template already supports multiple ClipCards (max 8 shown, with "+N more" text).

### 4. Email Template Data Mapping

| Template field | Source |
|---|---|
| `title` | AI-generated from transcript (fallback: first ~8 words of description) |
| `description` | `parliament_member_clips.description` (if fallback: description minus the title portion) |
| `image` | `parliament_member_clips.thumbnail_url` (fallback: placeholder image) |
| `duration` | `end_timestamp - start_timestamp`, formatted as "M:SS" |
| `date` | Today's ISO date string |
| `appUrl` | `NEXT_PUBLIC_APP_URL` env var + `/dashboard` |

### 5. AI Title Generation

- **Model:** gpt-4o-mini (existing in `services/ai/providers/openai.ts`)
- **One API call per clip**, sequential with ~100ms delay between calls
- **Prompt direction:** Generate a short (5-12 word) title from the transcript, oriented for MP staff. Example: "Speech on NHS Funding During Health Questions"
- **Fallback:** If AI call fails, use first ~8 words of description as title, rest of description as body

### 6. Security

CRON_SECRET bearer token auth, matching existing cron patterns in `app/api/cron/`.

## Failure Handling & Rate Limits

### OpenAI Rate Limits
- Sequential calls with ~100ms delay between requests
- If a single title generation fails, use the description fallback — email still gets sent
- If OpenAI is completely down, all clips use the fallback

### Mailjet Rate Limits
- Sequential email sends with ~200ms delay between each
- If Mailjet returns a rate limit error, stop sending — remaining users don't get logged in `clip_notification_log`, so they retry next hour
- Successfully sent emails ARE logged, so they won't be re-sent

### Retry Logic
- `clip_notification_log` entries are inserted per-user after successful send
- If sending fails for user 2 of 3, users 1 gets logged (won't retry), user 2 retries next hour, user 3 also retries
- `notification_sent_at` on the clip is set only when ALL eligible users have entries in `clip_notification_log`

## Open Questions

- None — ready to proceed to planning.
