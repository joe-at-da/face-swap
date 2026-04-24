# The MP AI - Project Documentation

This document provides comprehensive technical documentation for The MP AI platform, covering architecture, integrations, and development workflows.

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Deep Dive](#architecture-deep-dive)
3. [Next.js Implementation](#nextjs-implementation)
4. [Supabase Integration](#supabase-integration)
5. [RunPod Integration](#runpod-integration)
6. [AI/ML Pipeline](#aiml-pipeline)
7. [Cron Jobs & Background Tasks](#cron-jobs--background-tasks)
8. [External Integrations](#external-integrations)
9. [Development Workflow](#development-workflow)
10. [Deployment](#deployment)

---

## Introduction

### Project Purpose

The MP AI is an AI-powered platform designed for UK Members of Parliament and their staff to:

- Create, search, and share parliamentary video clips
- Automatically process parliament session videos
- Enable AI-powered semantic search across clips
- Schedule social media posts across multiple platforms
- Collaborate within teams

### Target Users

1. **MPs with parliament.uk emails** - Full access to create teams and manage clips
2. **MP Staff** - Join teams via invitation, create and share clips
3. **Regular Users** - Search and view public clips, follow MPs

### Key Features

| Feature                    | Description                                             |
| -------------------------- | ------------------------------------------------------- |
| Automated Video Processing | RunPod GPU processes parliament session videos          |
| AI-Powered Search          | Vector embeddings enable semantic search                |
| Face Recognition           | Automatic MP identification in videos                   |
| Social Media Integration   | Post to Facebook, Twitter/X, Instagram, TikTok, Bluesky |
| Team Collaboration         | Teams for MP offices with role-based access             |
| Real-time Notifications    | Alerts when followed MPs speak                          |

---

## Architecture Deep Dive

### Full-Stack Next.js 15 Architecture

The application uses Next.js 15 with the App Router pattern, leveraging:

- **Server Components** (default) - For data fetching and SEO
- **Client Components** - Only for interactivity and browser APIs
- **Server Actions** - For form submissions and mutations
- **API Routes** - For webhooks, cron jobs, and external integrations

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Next.js 15 App                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Server         │  │  Client         │  │  API Routes     │ │
│  │  Components     │  │  Components     │  │                 │ │
│  │  (Default)      │  │  (Interactive)  │  │  /api/clips/*   │ │
│  │                 │  │                 │  │  /api/cron/*    │ │
│  │  - Data fetch   │  │  - Forms        │  │  /api/runpod/*  │ │
│  │  - SEO          │  │  - Video player │  │  /api/teams/*   │ │
│  │  - Auth check   │  │  - Realtime     │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │ Supabase │    │  RunPod  │    │ External │
       │          │    │   GPU    │    │   APIs   │
       │ - Auth   │    │          │    │          │
       │ - DB     │    │ - Video  │    │ - Parli  │
       │ - Storage│    │ - Clips  │    │ - Postiz │
       │ - RT     │    │ - Faces  │    │ - OpenAI │
       └──────────┘    └──────────┘    └──────────┘
```

### Server vs Client Components

**Server Components (Default)**

```tsx
// No "use client" directive needed
// Can use async/await directly
// Can access server-only resources

import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";

export default async function DashboardPage() {
  const supabase = await createSupabaseServerClient();
  const { data: clips } = await supabase
    .from("user_clips")
    .select("*")
    .order("created_at", { ascending: false });

  return <ClipsList clips={clips} />;
}
```

**Client Components (Interactive)**

```tsx
"use client";

import { useState } from "react";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";

export function VideoPlayer({ clipId }: { clipId: string }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const supabase = createSupabaseBrowserClient();

  // Interactive functionality...
}
```

### App Router Structure

```
app/
├── (publicPages)/              # Public route group
│   ├── layout.tsx             # Shared layout for public pages
│   ├── signin/
│   │   └── page.tsx
│   ├── signup/
│   │   └── page.tsx
│   └── (homePage)/
│       └── page.tsx
│
├── (privatePages)/             # Protected route group
│   ├── layout.tsx             # Auth-checking layout
│   ├── dashboard/
│   │   ├── page.tsx
│   │   ├── loading.tsx        # Skeleton loading
│   │   ├── error.tsx          # Error boundary
│   │   ├── my-clips/
│   │   ├── create-clips/
│   │   ├── teams/
│   │   └── settings/
│   ├── setup/
│   └── mp-setup/
│
└── api/                        # API routes
    ├── clips/
    ├── cron/
    ├── runpod/
    ├── teams/
    └── webhooks/
```

---

## Next.js Implementation

### Route Protection with Middleware

Authentication is handled via Supabase middleware. Protected routes require a valid session.

**Protected Routes:**

- `/dashboard/*` - Main dashboard and all subpages
- `/setup` - User onboarding
- `/mp-setup` - MP-specific onboarding

### Server Actions

Server Actions are used for form submissions and mutations:

```tsx
// app/actions/clips.ts
"use server";

import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { revalidatePath } from "next/cache";

export async function createClip(formData: FormData) {
  const supabase = await createSupabaseServerClient();

  const { data, error } = await supabase.from("user_clips").insert({
    title: formData.get("title"),
    // ...other fields
  });

  if (error) throw error;

  revalidatePath("/dashboard/my-clips");
  return data;
}
```

### API Routes

API routes handle webhooks, cron jobs, and external integrations:

```tsx
// app/api/runpod/create-clip/route.ts
import { NextRequest, NextResponse } from "next/server";
import { RunPodService } from "@/services/runpod/runpod-service";

export async function POST(request: NextRequest) {
  // Verify CRON_SECRET authentication
  const authHeader = request.headers.get("authorization");
  const cronSecret = process.env.CRON_SECRET;

  if (authHeader !== `Bearer ${cronSecret}`) {
    return NextResponse.json(
      { success: false, error: "Unauthorized" },
      { status: 401 },
    );
  }

  // Process request...
  const body = await request.json();
  const runPodService = new RunPodService();
  const result = await runPodService.createUserClip(body.user_clip_id);

  return NextResponse.json({
    success: true,
    data: { job_id: result.job_id },
  });
}
```

### Loading and Error Boundaries

Every route includes loading and error handling:

```tsx
// app/(privatePages)/dashboard/loading.tsx
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
```

```tsx
// app/(privatePages)/dashboard/error.tsx
"use client";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-4">
      <h2>Something went wrong!</h2>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

---

## Supabase Integration

### Client Configurations

The project uses three Supabase client configurations for different contexts:

#### Server Client (`supabaseServerClient.ts`)

Used in Server Components and Server Actions:

```typescript
import "server-only";

import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { Database } from "@/supabaseTypes";

export const createSupabaseServerClient = async () => {
  const cookieStore = await cookies();
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, { ...options, path: "/" });
            });
          } catch (error) {
            // Handle server component context
          }
        },
      },
    },
  );
};
```

#### Browser Client (`supabaseBrowserClient.ts`)

Used in Client Components:

```typescript
"use client";

import { createBrowserClient } from "@supabase/ssr";
import { Database } from "@/supabaseTypes";

export const createSupabaseBrowserClient = () => {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
};
```

#### Admin Client (`supabaseAdmin.ts`)

Used for service-role operations (bypasses RLS):

```typescript
import "server-only";

import { createClient } from "@supabase/supabase-js";
import { Database } from "@/supabaseTypes";

export const supabaseAdminClient = createClient<Database>(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!,
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  },
);
```

### Database Schema

The platform uses 10+ core tables:

#### Parliament Data Tables

| Table                              | Purpose                         | Key Fields                                                                                       |
| ---------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------ |
| `parliament_members`               | UK MPs and Lords (500+ records) | `member_id`, `name`, `house`, `party`, `constituency`, `is_current_member`                       |
| `parliament_member_clips`          | AI-detected video clips         | `clip_id`, `member_id`, `transcript`, `start_time`, `end_time`, `clip_url`, `embedding` (vector) |
| `parliament_member_portraits`      | MP headshots                    | `portrait_id`, `member_id`, `image_url`, `crop_type`                                             |
| `parliament_member_contacts`       | Contact information             | `contact_id`, `member_id`, `email`, `phone`, `twitter`, `facebook`                               |
| `parliament_member_face_encodings` | Face recognition data           | `encoding_id`, `portrait_id`, `face_encoding`                                                    |
| `parliament_events`                | Parliament Live TV events       | `event_id`, `title`, `session_uid`, `status`, `session_date`                                     |

#### User & Content Tables

| Table        | Purpose              | Key Fields                                                                                                 |
| ------------ | -------------------- | ---------------------------------------------------------------------------------------------------------- |
| `user_clips` | User-created clips   | `clip_id`, `user_id`, `team_id`, `title`, `segments`, `status`, `horizontal_clip_url`, `vertical_clip_url` |
| `user_roles` | User settings & auth | `user_id`, `role`, `username`, `is_first_login`, `postiz_api_key`, `notification_preferences`              |

#### Team Tables

| Table              | Purpose           | Key Fields                                                           |
| ------------------ | ----------------- | -------------------------------------------------------------------- |
| `teams`            | Team management   | `team_id`, `name`, `owner_id`, `is_deleted`                          |
| `team_members`     | Team membership   | `member_id`, `team_id`, `user_id`, `role` (owner/administrator/user) |
| `team_invitations` | Email invitations | `invitation_id`, `team_id`, `email`, `token`, `expires_at`           |
| `team_mp_follows`  | Team MP tracking  | `follow_id`, `team_id`, `member_id`                                  |

#### Processing Tables

| Table                    | Purpose             | Key Fields                                                                 |
| ------------------------ | ------------------- | -------------------------------------------------------------------------- |
| `runpod_processing_logs` | RunPod job tracking | `log_id`, `table_name`, `record_id`, `endpoint`, `status`, `error_message` |
| `parliament_sync_status` | Sync metadata       | `sync_id`, `last_sync`, `records_processed`, `status`                      |

### Row Level Security (RLS)

All tables have RLS policies enforcing data isolation:

```sql
-- Example: Users can only see their own clips or team clips
CREATE POLICY "Users can view own clips" ON user_clips
  FOR SELECT
  USING (
    auth.uid() = user_id
    OR team_id IN (
      SELECT team_id FROM team_members
      WHERE user_id = auth.uid()
    )
  );
```

### Authentication Flow

```
┌─────────────┐
│   User      │
│ Signs In    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│  Magic Link / OTP via Supabase  │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   /auth/callback                │
│   Verifies token, creates       │
│   session cookie                │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   Database Trigger:             │
│   handle_new_user()             │
│   - Creates user_roles entry    │
│   - Generates username          │
└──────────────┬──────────────────┘
               │
               ▼
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│ @parliament │ │   Other     │
│ .uk email   │ │   email     │
└──────┬──────┘ └──────┬──────┘
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│  /mp-setup  │ │   /setup    │
└─────────────┘ └─────────────┘
```

### Storage Buckets

| Bucket       | Purpose                 | Access        |
| ------------ | ----------------------- | ------------- |
| `avatars`    | User profile images     | Public        |
| `clips`      | Video clip files        | Public        |
| `thumbnails` | Clip thumbnails         | Public        |
| `watermarks` | Custom watermark images | Authenticated |

### Realtime Subscriptions

```typescript
// Subscribe to user_clips changes
const supabase = createSupabaseBrowserClient();

supabase
  .channel("user-clips")
  .on(
    "postgres_changes",
    {
      event: "UPDATE",
      schema: "public",
      table: "user_clips",
      filter: `user_id=eq.${userId}`,
    },
    (payload) => {
      // Handle clip status update
      console.log("Clip updated:", payload.new);
    },
  )
  .subscribe();
```

### Migration Workflow

1. **Create migration:**

   ```bash
   supabase migration new migration_name
   ```

2. **Edit migration file** in `supabase/migrations/`:

   ```sql
   -- Example: Add new column
   ALTER TABLE user_clips
   ADD COLUMN description TEXT;
   ```

3. **Apply migration:**

   ```bash
   supabase db push --local
   ```

4. **Generate types:**
   ```bash
   pnpm genTypes
   ```

---

## RunPod Integration

RunPod provides serverless GPU functions for video processing.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js Application                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Routes                                │
│  /api/runpod/process-video  - Parliament video processing   │
│  /api/runpod/create-clip    - User clip creation            │
│  /api/runpod/encode-faces   - Face encoding                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  RunPodService                               │
│  - processParliamentVideo()                                 │
│  - createUserClip()                                         │
│  - processFaceEncodings()                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  RunPodClient                                │
│  POST https://api.runpod.ai/v2/{endpoint}/run               │
│  Returns: { id: "job_id", status: "IN_QUEUE" }              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 RunPod Serverless GPU                        │
│  - Processes video asynchronously                           │
│  - Updates database directly                                 │
│  - Uploads files to S3                                       │
└─────────────────────────────────────────────────────────────┘
```

### Three Serverless Endpoints

#### 1. Video Processor

Processes parliament session videos into individual clips.

**TypeScript Interface:**

```typescript
interface VideoProcessorInput {
  parliament_event_id: string; // UUID from parliament_events table
}

interface VideoProcessorResponse {
  status: boolean;
  parliament_event_id?: string;
  session_uid: string;
  file_size_mb: number;
  total_time_seconds: number;
  summary: {
    total_segments: number;
    mps_identified: number;
    mps_identified_percentage: number;
    transcripts_generated: number;
    clips_uploaded: number;
    db_records_created: number;
  };
  segments: VideoProcessorSegment[];
  full_video_url?: string;
}
```

#### 2. Clip Creator

Creates user-generated clips from parliament videos.

**TypeScript Interface:**

```typescript
interface ClipCreatorInput {
  user_clip_id: string; // UUID from user_clips table
}

interface ClipCreatorResponse {
  status: boolean;
  job_id: string;
  user_clip_id?: string;
  outputs: {
    horizontal_clip_url?: string;
    vertical_clip_url?: string;
    horizontal_thumbnail_url?: string;
    vertical_thumbnail_url?: string;
  };
  transcript?: string;
  processing_time: {
    validation: number;
    clip_creation: number;
    upload: number;
    total: number;
  };
  gpu_info: {
    available: boolean;
    name: string;
    memory_gb: string;
  };
}
```

#### 3. Face Encoder

Generates face encodings for MP identification.

**TypeScript Interface:**

```typescript
interface FaceEncoderInput {
  detection_threshold?: number; // Default: 0.65
  batch_size?: number;
  max_workers?: number;
  target_portraits?: number;
}

interface FaceEncoderResponse {
  status: boolean;
  job_id: string;
  total_time_seconds: number;
  processing_summary: {
    total_portraits: number;
    portraits_processed: number;
    encodings_created: number;
    encodings_failed: number;
    avg_time_per_portrait: number;
  };
  gpu_info: {
    name: string;
    memory_gb: number;
    cuda_available: boolean;
  };
}
```

### API Routes

#### POST /api/runpod/create-clip

```typescript
// Request
POST /api/runpod/create-clip
Authorization: Bearer ${CRON_SECRET}
Content-Type: application/json

{
  "user_clip_id": "uuid-here"
}

// Success Response (200)
{
  "success": true,
  "data": {
    "job_id": "runpod-job-id",
    "user_clip_id": "uuid-here",
    "status": "IN_QUEUE"
  },
  "retry_count": 0,
  "timestamp": "2024-01-01T00:00:00.000Z"
}

// Retry Response (503)
{
  "success": false,
  "error": "RunPod service error",
  "queued_for_retry": true,
  "retry_count": 1,
  "max_retries": 3,
  "next_retry_in_minutes": 10,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### Database Triggers

Automatic processing is triggered by database changes:

```sql
-- Trigger for parliament video processing
CREATE OR REPLACE FUNCTION trigger_parliament_video_processing()
RETURNS TRIGGER AS $$
BEGIN
  -- Only trigger for House of Commons events with 'pending' status
  IF NEW.title_type = 'House of Commons' AND NEW.status = 'pending' THEN
    -- Call API endpoint via HTTP
    PERFORM http_post(
      'http://localhost:3000/api/runpod/process-video',
      json_build_object('parliament_event_id', NEW.event_id)::text,
      'application/json'
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_trigger_parliament_video_processing
  AFTER INSERT OR UPDATE ON parliament_events
  FOR EACH ROW
  EXECUTE FUNCTION trigger_parliament_video_processing();
```

```sql
-- Trigger for user clip processing
CREATE OR REPLACE FUNCTION trigger_user_clip_processing()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'pending_review' THEN
    PERFORM http_post(
      'http://localhost:3000/api/runpod/create-clip',
      json_build_object('user_clip_id', NEW.clip_id)::text,
      'application/json'
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_trigger_user_clip_processing
  AFTER INSERT OR UPDATE ON user_clips
  FOR EACH ROW
  EXECUTE FUNCTION trigger_user_clip_processing();
```

### Retry System

The retry system handles transient failures automatically.

**Error Classification:**

| Error Type     | HTTP Code | Retryable | Example               |
| -------------- | --------- | --------- | --------------------- |
| Server Errors  | 5xx       | Yes       | Internal server error |
| Timeout        | -         | Yes       | Connection timeout    |
| Network Issues | -         | Yes       | Network unreachable   |
| RunPod Service | -         | Yes       | RunPod queue full     |
| Invalid Data   | 400       | No        | Malformed UUID        |
| Unauthorized   | 401       | No        | Invalid CRON_SECRET   |
| Not Found      | 404       | No        | Clip doesn't exist    |

**Retry Configuration:**

```typescript
const retryConfig = {
  maxRetries: 3,
  delayMinutes: 10,
  processingLogTable: "runpod_processing_logs",
};
```

**Processing Logs Table:**

```sql
CREATE TABLE runpod_processing_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name TEXT NOT NULL,          -- 'user_clips' or 'parliament_events'
  record_id UUID NOT NULL,           -- ID of the record being processed
  endpoint TEXT NOT NULL,            -- '/api/runpod/create-clip'
  status TEXT NOT NULL,              -- 'pending', 'success', 'failed'
  response_status INTEGER,           -- HTTP status code
  error_message TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## AI/ML Pipeline

### OpenAI Embeddings

The platform uses OpenAI's text-embedding-3-small model (1536 dimensions) for semantic search.

**Embedding Generation:**

```typescript
import OpenAI from "openai";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

async function generateEmbedding(text: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    model: "text-embedding-3-small",
    input: text,
  });
  return response.data[0].embedding;
}
```

### pgvector Setup

Vector similarity search is powered by pgvector:

```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column
ALTER TABLE parliament_member_clips
ADD COLUMN embedding vector(1536);

-- Create HNSW index for fast similarity search
CREATE INDEX idx_clips_embedding_hnsw
ON parliament_member_clips
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### Similarity Search Function

```sql
CREATE OR REPLACE FUNCTION search_clips_by_similarity(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  clip_id UUID,
  member_id INTEGER,
  transcript TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    pmc.clip_id,
    pmc.member_id,
    pmc.transcript,
    1 - (pmc.embedding <=> query_embedding) AS similarity
  FROM parliament_member_clips pmc
  WHERE 1 - (pmc.embedding <=> query_embedding) > match_threshold
  ORDER BY pmc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

### Face Recognition Pipeline

```
┌─────────────────┐
│ MP Portraits    │
│ (Images)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Face Encoder    │
│ (RunPod GPU)    │
│                 │
│ - Detect faces  │
│ - Generate      │
│   128-d vectors │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ face_encodings  │
│ table           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Video Processor │
│                 │
│ - Compare faces │
│ - Identify MPs  │
│ - Label clips   │
└─────────────────┘
```

### Embedding Queue System

Embeddings are generated asynchronously via a queue:

```sql
-- Queue new clips for embedding generation
CREATE OR REPLACE FUNCTION queue_clip_for_embedding()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.transcript IS NOT NULL AND NEW.embedding IS NULL THEN
    PERFORM pgmq.send(
      'embedding_queue',
      json_build_object(
        'clip_id', NEW.clip_id,
        'transcript', NEW.transcript
      )::jsonb
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Cron Jobs & Background Tasks

### Scheduled Jobs via Coolify

All cron jobs run via Coolify scheduled tasks (not pg_cron).

| Job             | Schedule         | Endpoint                            | Purpose                          |
| --------------- | ---------------- | ----------------------------------- | -------------------------------- |
| Parliament Sync | Daily @ 2 AM UTC | `/api/cron/parliament-sync`         | Sync MP data from Parliament API |
| Event Sync      | Every 6 hours    | `/api/cron/parliament-event-sync`   | Fetch new parliament videos      |
| Embedding Queue | Every 5 minutes  | `/api/cron/process-embedding-queue` | Process transcript embeddings    |
| RunPod Retries  | Every 10 minutes | `/api/cron/process-runpod-retries`  | Retry failed processing jobs     |

### Coolify Configuration

```bash
# Parliament Sync - Daily at 2 AM UTC
# Schedule: 0 2 * * *
curl -X POST "http://localhost:3000/api/cron/parliament-sync" \
  -H "Authorization: Bearer ${CRON_SECRET}" \
  -H "Content-Type: application/json" \
  --max-time 600

# Event Sync - Every 6 hours
# Schedule: 0 */6 * * *
curl -X POST "http://localhost:3000/api/cron/parliament-event-sync" \
  -H "Authorization: Bearer ${CRON_SECRET}" \
  -H "Content-Type: application/json" \
  --max-time 300

# Embedding Queue - Every 5 minutes
# Schedule: */5 * * * *
curl -X POST "http://localhost:3000/api/cron/process-embedding-queue" \
  -H "Authorization: Bearer ${CRON_SECRET}" \
  -H "Content-Type: application/json" \
  --max-time 300

# RunPod Retries - Every 10 minutes
# Schedule: */10 * * * *
curl -X POST "http://localhost:3000/api/cron/process-runpod-retries" \
  -H "Authorization: Bearer ${CRON_SECRET}" \
  -H "Content-Type: application/json" \
  --max-time 300
```

### Webhook System

Database triggers call API endpoints for asynchronous processing:

```
┌─────────────────┐
│ Database        │
│ INSERT/UPDATE   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Trigger         │
│ Function        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ HTTP POST       │
│ /api/endpoint   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Async           │
│ Processing      │
└─────────────────┘
```

---

## External Integrations

### UK Parliament API

**Configuration:**

```typescript
const parliamentApiConfig = {
  baseUrl: "https://api.parliament.uk",
  rateLimit: {
    burst: 4, // Max 4 requests per burst
    intervalMs: 500, // 500ms between requests
  },
  retry: {
    maxAttempts: 3,
    backoffMs: 1000,
  },
};
```

**Rate Limiting Implementation:**

```typescript
import { RateLimiter } from "@/lib/rate-limiter";

const limiter = new RateLimiter({
  tokensPerInterval: 4,
  interval: 500,
});

async function fetchMember(memberId: number) {
  await limiter.removeTokens(1);
  const response = await fetch(`https://api.parliament.uk/members/${memberId}`);
  return response.json();
}
```

### Postiz Social Media

Social media scheduling via Postiz API:

```typescript
// services/postiz/postizApi.ts
interface PostizConfig {
  apiKey: string;
  baseUrl: string;
}

async function schedulePost(config: {
  clipUrl: string;
  platforms: string[];
  scheduledAt: Date;
  caption: string;
}) {
  const response = await fetch(`${POSTIZ_BASE_URL}/posts`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(config),
  });
  return response.json();
}
```

### Bluesky OAuth

```typescript
// services/bluesky/blueskyApi.ts
async function authenticateBluesky(code: string) {
  // OAuth callback handling
  const tokenResponse = await fetch("https://bsky.social/oauth/token", {
    method: "POST",
    body: JSON.stringify({
      grant_type: "authorization_code",
      code,
      redirect_uri: process.env.BLUESKY_REDIRECT_URI,
    }),
  });
  return tokenResponse.json();
}
```

### Glitchtip Error Monitoring

```typescript
// sentry.client.config.ts
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_GLITCHTIP_DSN,
  tracesSampleRate: 0.1,
  environment: process.env.NODE_ENV,
});
```

---

## Development Workflow

### Local Setup

1. **Install dependencies:**

   ```bash
   pnpm install
   ```

2. **Start Supabase:**

   ```bash
   supabase start
   ```

3. **Apply migrations:**

   ```bash
   supabase db push --local
   ```

4. **Generate types:**

   ```bash
   pnpm genTypes
   ```

5. **Start dev server:**
   ```bash
   pnpm dev
   ```

### Email Testing with Mailpit

Access Mailpit at `http://localhost:55324` to view:

- Magic link authentication emails
- OTP verification codes
- Team invitation emails

### Type Generation

After any database schema changes:

```bash
pnpm genTypes
```

This updates `supabaseTypes.ts` with the latest schema.

### Testing with Playwright

```bash
# Run all tests
pnpm test:e2e

# Interactive UI mode
pnpm test:e2e:ui

# Debug mode
pnpm test:e2e:debug

# Run specific test file
pnpm test:e2e tests/auth.spec.ts
```

---

## Deployment

### Coolify Self-Hosted Setup

The application is deployed on a self-hosted Coolify instance.

**nixpacks.toml:**

```toml
[variables]
NODE_ENV = "production"

[phases.setup]
nixPkgs = ["nodejs_20", "pnpm", "fontconfig", "freetype"]

[phases.install]
cmds = ["pnpm install"]

[phases.build]
cmds = ["pnpm run build"]

[start]
cmd = "pnpm start"
```

### Environment Variables Reference

| Variable                          | Description                        | Required |
| --------------------------------- | ---------------------------------- | -------- |
| `NEXT_PUBLIC_SUPABASE_URL`        | Supabase project URL               | Yes      |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`   | Supabase anonymous key             | Yes      |
| `SUPABASE_SERVICE_KEY`            | Supabase service role key          | Yes      |
| `RUNPOD_API_KEY`                  | RunPod API key                     | Yes      |
| `RUNPOD_VIDEO_PROCESSOR_ENDPOINT` | Video processor endpoint ID        | Yes      |
| `RUNPOD_CLIP_CREATOR_ENDPOINT`    | Clip creator endpoint ID           | Yes      |
| `RUNPOD_FACE_ENCODER_ENDPOINT`    | Face encoder endpoint ID           | Yes      |
| `OPENAI_API_KEY`                  | OpenAI API key for embeddings      | Yes      |
| `CRON_SECRET`                     | Secret for cron job authentication | Yes      |
| `POSTIZ_API_KEY`                  | Postiz API key                     | Optional |
| `NEXT_PUBLIC_GLITCHTIP_DSN`       | Glitchtip DSN for error tracking   | Optional |

### Production Checklist

- [ ] Configure all environment variables
- [ ] Run database migrations
- [ ] Set up storage buckets with correct permissions
- [ ] Configure Coolify scheduled tasks for cron jobs
- [ ] Set up domain and SSL certificates
- [ ] Configure Glitchtip error monitoring
- [ ] Test authentication flow
- [ ] Verify RunPod endpoints are responding
- [ ] Test social media integrations

---

## Additional Resources

- [README.md](./README.md) - Quick start guide
- [CLAUDE.md](./CLAUDE.md) - Development guidelines for AI assistance
- [COOLIFY_SCHEDULED_TASKS.md](./COOLIFY_SCHEDULED_TASKS.md) - Cron job configuration
- [.claude/style-guide.md](./.claude/style-guide.md) - UI/UX style guide
- [.claude/design-principles.md](./.claude/design-principles.md) - Design principles
