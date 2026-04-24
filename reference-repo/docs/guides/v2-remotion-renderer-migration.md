# V2 Remotion Renderer — New Handler Guide

Guide for building a **new** RunPod serverless handler (`clip_creator_handler_v2.py`) that renders Remotion v2 composition JSON. This handler is **completely separate** from the existing v1 clip creator — no v1/v2 branching, no shared processor class.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Why a Separate Handler](#why-a-separate-handler)
3. [Composition JSON Structure](#composition-json-structure)
4. [New Handler: `clip_creator_handler_v2.py`](#new-handler-clip_creator_handler_v2py)
5. [New Processor: `UserClipProcessorV2`](#new-processor-userclipprocessorv2)
6. [Node.js Renderer Service](#nodejs-renderer-service)
7. [No Full Video Download — HTTP Range Requests](#no-full-video-download--http-range-requests)
8. [Transcription (Same as V1)](#transcription-same-as-v1)
9. [Feature Mapping: JSON → Remotion Components](#feature-mapping-json--remotion-components)
10. [Docker Setup](#docker-setup)
11. [Error Handling](#error-handling)
12. [Testing](#testing)

---

## Architecture Overview

```
RunPod Serverless Endpoint (NEW, separate from v1)
│
├── clip_creator_handler_v2.py          ← New RunPod handler (Python)
│   └── calls handle_clip_v2()
│       └── UserClipProcessorV2         ← New processor class
│           ├── Fetch composition_json from DB
│           ├── Call Node.js renderer via subprocess
│           │   └── render-composition.mjs
│           │       ├── @remotion/renderer renderMedia()
│           │       ├── Chromium renders React components frame-by-frame
│           │       └── FFmpeg h264_nvenc encodes to MP4 (GPU)
│           ├── Generate thumbnails (FFmpeg, same as v1)
│           ├── Upload to S3 (StorageClient, same as v1)
│           ├── Whisper transcription (Transcriber, same as v1)
│           └── Update user_clips DB record
│
├── renderer/                           ← Node.js Remotion project (new)
│   ├── package.json
│   ├── remotion-bundle/                ← Pre-bundled compositions (built in Docker)
│   └── render-composition.mjs          ← Rendering entry point
│
└── Shared utilities (reused from v1)
    ├── app/shared/storage.py           ← S3 upload (StorageClient)
    ├── app/shared/transcription.py     ← Whisper (Transcriber)
    ├── app/shared/supabase_client.py   ← fetch_user_clip, update_user_clip
    └── app/handlers/common.py          ← Logging, watchdog, SIGTERM, wrap_result_with_refresh
```

### What V2 Renders

The frontend Remotion editor exports a `composition_json` JSONB column to the `user_clips` table. This JSON contains the full video composition: tracks with video/text/image items, transforms, keyframes, subtitles, and metadata.

The v2 handler renders this composition into two MP4 files:
- **Landscape**: 1920x1080 (16:9)
- **Vertical**: 1080x1920 (9:16)

Both are always rendered regardless of the `outputFormat` in metadata.

---

## Why a Separate Handler

| Concern | Decision |
|---------|----------|
| Different rendering technology | V1 uses FFmpeg segment extraction; V2 uses Remotion headless Chromium |
| Different dependencies | V2 needs Node.js, Chromium, Remotion npm packages |
| Different Docker image | V2 image is larger (Chromium + Node.js + Python) |
| No shared state | V1 processor has segment parsing, video download, concat — none of this applies to V2 |
| Independent scaling | V2 renders are heavier (Chromium per-frame) — may need different GPU instance types |
| Deployment isolation | Bug in v2 renderer doesn't break v1 clip creation |

The v1 handler (`clip_creator_handler.py`) and processor (`UserClipProcessor`) remain **completely untouched**.

---

## Composition JSON Structure

The `composition_json` column stores the entire video composition. Type definitions are in `types/remotionEditor.ts`.

### Root: `VideoComposition`

```json
{
  "version": 2,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "durationInFrames": 3600,
  "tracks": [...],
  "subtitles": { ... } | null,
  "metadata": {
    "clipId": "uuid",
    "userId": "uuid",
    "teamId": "uuid" | null,
    "createdAt": "2026-02-13T14:30:00Z",
    "outputFormat": "landscape" | "vertical"
  }
}
```

**Key points:**
- `fps` is always 30
- `width`/`height` reflect the canvas mode chosen during editing (1920x1080 or 1080x1920)
- All time values are in **frames** (not milliseconds, not seconds)
- Convert: `seconds = frames / 30`, `ms = (frames / 30) * 1000`

### TimelineItem (Video)

```json
{
  "id": "abc123",
  "type": "video",
  "from": 0,
  "durationInFrames": 1800,
  "src": "https://cdn.example.com/session-video.mp4",
  "startFrom": 156000,
  "endAt": 157800,
  "playbackRate": 1.0,
  "volume": 0.8,
  "isMuted": false,
  "audioFadeIn": 15,
  "audioFadeOut": 15,
  "opacity": 1.0,
  "transform": {
    "scale": 1.0,
    "translateX": 0,
    "translateY": 0,
    "rotation": 0
  },
  "keyframes": [
    { "frame": 0, "transform": { "scale": 1.0 } },
    { "frame": 1800, "transform": { "scale": 1.2 } }
  ],
  "filters": {
    "brightness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0
  },
  "flipH": false,
  "flipV": false,
  "sourceClip": {
    "clipId": "uuid",
    "originalStartMs": 5200000,
    "originalEndMs": 5260000,
    "sessionDurationMs": 28800000,
    "mpName": "Keir Starmer",
    "transcript": "...",
    "thumbnailUrl": "https://..."
  }
}
```

| Field | Type | Description |
|---|---|---|
| `from` | int | Start frame on the timeline (0-based) |
| `durationInFrames` | int | Duration on the timeline in frames |
| `src` | string | Full URL to the source video (8hr parliament session on CDN/S3) |
| `startFrom` | int | Frame offset into the source video where playback begins |
| `endAt` | int | Frame offset into the source video where playback ends |
| `playbackRate` | float | Speed multiplier: 0.25 - 4.0 (default 1) |
| `volume` | float | Audio volume: 0.0 - 1.0 (default 1) |
| `isMuted` | bool | Whether audio is muted |
| `audioFadeIn` | int | Frames of audio fade-in (0 = no fade) |
| `audioFadeOut` | int | Frames of audio fade-out (0 = no fade) |
| `opacity` | float | Visual opacity: 0.0 - 1.0 (default 1) |
| `transform` | object | Static transform (scale, translate, rotation) |
| `keyframes` | array | Animated transform keyframes for Ken Burns effects |
| `filters` | object | CSS filters: brightness, contrast, saturation (default 1.0 each) |
| `flipH` / `flipV` | bool | Horizontal/vertical flip |
| `sourceClip` | object | Metadata about the original parliament clip (for reference only, not used in rendering) |

### TimelineItem (Text)

```json
{
  "id": "txt123",
  "type": "text",
  "from": 30,
  "durationInFrames": 90,
  "text": "Breaking News",
  "fontSize": 48,
  "fontFamily": "Inter",
  "color": "#ffffff",
  "backgroundColor": "rgba(0,0,0,0.6)",
  "position": { "x": 0.5, "y": 0.8 },
  "animation": "fade-in"
}
```

| Field | Type | Description |
|---|---|---|
| `text` | string | The text content |
| `fontSize` | int | Font size in pixels (default 48) |
| `fontFamily` | string | One of: Inter, Arial, Georgia, Courier New, Impact |
| `color` | string | CSS color string |
| `backgroundColor` | string | CSS background color |
| `position` | object | `{x, y}` as 0-1 percentages (0.5 = center) |
| `animation` | string | `none`, `fade-in`, `slide-in-left`, `slide-in-right`, `typewriter` |

### TimelineItem (Image)

```json
{
  "id": "img123",
  "type": "image",
  "from": 0,
  "durationInFrames": 150,
  "src": "https://cdn.example.com/logo.png",
  "imageWidthPercent": 30,
  "position": { "x": 0.5, "y": 0.5 },
  "opacity": 0.8,
  "fitMode": "contain",
  "animation": "fade-in"
}
```

### Subtitles (SubtitleTrack)

```json
{
  "captions": [
    {
      "text": "We ",
      "startMs": 0,
      "endMs": 200,
      "timestampMs": 100,
      "confidence": 0.98
    }
  ],
  "style": {
    "fontSize": 48,
    "fontFamily": "Inter",
    "color": "#FFFFFF",
    "highlightColor": "#39E508",
    "highlightEnabled": true,
    "backgroundColor": "rgba(0,0,0,0.6)",
    "position": "bottom",
    "maxWordsPerLine": 6,
    "outlineColor": "#000000",
    "outlineWidth": 2,
    "shadowColor": null,
    "shadowBlur": null
  }
}
```

**Subtitle rendering details:**
- Uses `@remotion/captions` library's `createTikTokStyleCaptions()` for word-level highlighting
- Caption times are in **milliseconds** relative to the composition timeline (already aggregated during export)
- `highlightEnabled` + `highlightColor`: currently spoken word is highlighted (TikTok-style karaoke)
- `position`: `"bottom"`, `"center"`, or `"top"`

---

## New Handler: `clip_creator_handler_v2.py`

Follows the **exact same pattern** as the existing `clip_creator_handler.py`. Copy and adapt.

```python
"""
RunPod Serverless Handler for V2 Remotion Clip Creation.

Renders Remotion v2 composition JSON into landscape + vertical MP4 videos.
Uses headless Chromium + Remotion for rendering, NVIDIA h264_nvenc for encoding.
"""

import logging
import sys

import runpod

from app.api.clip_creator_v2.router import ClipCreatorV2Request, handle_clip_v2
from app.handlers.common import (
    configure_logging,
    flush_output,
    increment_jobs_processed,
    register_sigterm_handler,
    set_current_job_id,
    start_idle_watchdog,
    wrap_result_with_refresh,
)

configure_logging()
logger = logging.getLogger(__name__)

start_idle_watchdog()
register_sigterm_handler("clip_creator_v2")


async def clip_creator_v2_handler(job):
    """RunPod serverless handler for v2 Remotion clip creation."""
    job_input = job.get("input", {})
    user_clip_id = job_input.get("user_clip_id")
    job_id = job.get("id", "unknown")

    if not user_clip_id:
        logger.error(f"[CLIP_CREATOR_V2] Missing 'user_clip_id' in job {job_id}")
        flush_output()
        return wrap_result_with_refresh({
            "status": False,
            "error": "Missing 'user_clip_id' in input"
        })

    increment_jobs_processed()
    set_current_job_id(user_clip_id)

    logger.info(f"[CLIP_CREATOR_V2] Starting job: {job_id}, user_clip_id: {user_clip_id}")
    flush_output()

    try:
        request = ClipCreatorV2Request(user_clip_id=user_clip_id)
        result = await handle_clip_v2(request)

        if result.get("status"):
            logger.info(f"[CLIP_CREATOR_V2] Job {job_id} completed successfully")
        else:
            logger.error(f"[CLIP_CREATOR_V2] Job {job_id} failed: {result.get('error')}")
        flush_output()

        return wrap_result_with_refresh(result)

    except Exception as e:
        logger.error(f"[CLIP_CREATOR_V2] Exception in job {job_id}: {e}", exc_info=True)
        flush_output()
        return wrap_result_with_refresh({
            "status": False,
            "user_clip_id": user_clip_id,
            "error": str(e)
        })
    finally:
        set_current_job_id(None)
        flush_output()


if __name__ == "__main__":
    runpod.serverless.start({"handler": clip_creator_v2_handler})
```

### New Router: `app/api/clip_creator_v2/router.py`

```python
"""Clip Creator V2 API Router — Remotion composition rendering."""

import logging
import sys

from fastapi import APIRouter
from pydantic import BaseModel

from app.shared.state import increment_requests
from app.shared.user_clip_processor_v2 import UserClipProcessorV2


class ClipCreatorV2Request(BaseModel):
    user_clip_id: str


router = APIRouter(prefix="/clip-creator-v2", tags=["clip-creator-v2"])
logger = logging.getLogger(__name__)


async def handle_clip_v2(request: ClipCreatorV2Request):
    """Handle v2 clip creation using Remotion renderer."""
    logger.info("handle_clip_v2 invoked payload=%s", request.model_dump())
    increment_requests()

    try:
        processor = UserClipProcessorV2(request.user_clip_id)
        result = await processor.process()
        return result
    except Exception as e:
        logger.error(f"V2 clip creation error: {e}", exc_info=True)
        return {
            "status": False,
            "user_clip_id": request.user_clip_id,
            "error": str(e)
        }
```

---

## New Processor: `UserClipProcessorV2`

New file: `app/shared/user_clip_processor_v2.py`

This is a **standalone class** — no inheritance from `UserClipProcessor`. It reuses the same shared utilities (StorageClient, Transcriber, fetch_user_clip, update_user_clip) but has its own pipeline.

### Pipeline

```
1. Fetch user_clip data from DB (composition_json, editor_version=2)
2. Validate composition_json exists and has tracks
3. Render landscape (1920x1080) via Node.js subprocess → renderMedia()
4. Render vertical (1080x1920) via Node.js subprocess → renderMedia()
5. Generate thumbnails (FFmpeg, same as v1)
6. Upload 4 files to S3 in parallel (StorageClient)
7. Extract audio → Whisper transcription (same as v1)
8. Update user_clips DB record with URLs, transcript, timing
9. Cleanup temp files
```

### Sample Implementation

```python
"""
V2 User Clip Processor — Remotion composition rendering.

Pipeline:
1. Fetch composition_json from DB
2. Render landscape + vertical via Node.js Remotion subprocess
3. Generate thumbnails (FFmpeg)
4. Upload to S3
5. Whisper transcription
6. Update DB
"""

import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import torch

from app.shared.storage import StorageClient
from app.shared.supabase_client import fetch_user_clip, update_user_clip

logger = logging.getLogger(__name__)

CLIP_TEMP_DIR = "/app/temp/clips_v2"
RENDERER_DIR = "/app/renderer"
BUNDLE_DIR = os.path.join(RENDERER_DIR, "remotion-bundle")
RENDER_SCRIPT = os.path.join(RENDERER_DIR, "render-composition.mjs")
RENDER_TIMEOUT = 600  # 10 minutes per render
THUMB_HORIZONTAL = (1280, 720)
THUMB_VERTICAL = (720, 1280)


def run_ffmpeg(args: list, description: str = "") -> bool:
    """Run an FFmpeg command, return True on success."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    logger.info(f"FFmpeg: {description}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error(f"FFmpeg failed ({description}): {result.stderr}")
        return False
    return True


class UserClipProcessorV2:
    def __init__(self, user_clip_id: str):
        self.user_clip_id = user_clip_id
        self.user_clip_data: Optional[Dict] = None
        self.composition: Optional[Dict] = None
        self.storage_client = StorageClient()
        self.transcript: Optional[str] = None
        self.output_urls: Dict[str, str] = {}
        self.timing: Dict[str, float] = {}

        # Temp paths
        self.temp_dir = os.path.join(CLIP_TEMP_DIR, str(uuid.uuid4()))
        os.makedirs(self.temp_dir, exist_ok=True)

        self.horizontal_clip_path = os.path.join(self.temp_dir, "horizontal.mp4")
        self.vertical_clip_path = os.path.join(self.temp_dir, "vertical.mp4")
        self.horizontal_thumb_path = os.path.join(self.temp_dir, "horizontal_thumb.jpg")
        self.vertical_thumb_path = os.path.join(self.temp_dir, "vertical_thumb.jpg")

    async def process(self) -> Dict[str, Any]:
        """Run the full v2 rendering pipeline."""
        total_start = time.time()

        try:
            # 1. Fetch and validate
            await self._fetch_and_validate()

            # 2. Render both orientations
            render_start = time.time()
            self._render_composition("landscape", 1920, 1080, self.horizontal_clip_path)
            self._render_composition("vertical", 1080, 1920, self.vertical_clip_path)
            self.timing["render"] = time.time() - render_start

            # 3. Generate thumbnails
            self._generate_thumbnails()

            # 4. Upload to S3
            upload_start = time.time()
            await self._upload_to_s3()
            self.timing["upload"] = time.time() - upload_start

            # 5. Transcription
            transcript_start = time.time()
            await self._generate_transcript()
            self.timing["transcript"] = time.time() - transcript_start

            # 6. Update DB
            self.timing["total"] = time.time() - total_start
            await self._update_database_success()

            return self._build_success_response()

        except Exception as e:
            self.timing["total"] = time.time() - total_start
            error_msg = str(e)[:1000]
            logger.error(f"V2 processing failed: {error_msg}", exc_info=True)
            await self._update_database_failure(error_msg)
            return self._build_error_response(str(e))

        finally:
            self._cleanup()

    async def _fetch_and_validate(self):
        """Fetch user_clip from DB and validate composition_json."""
        self.user_clip_data = fetch_user_clip(self.user_clip_id)
        if not self.user_clip_data:
            raise ValueError(f"User clip not found: {self.user_clip_id}")

        if self.user_clip_data.get("editor_version") != 2:
            raise ValueError("Not a v2 clip — use v1 handler instead")

        self.composition = self.user_clip_data.get("composition_json")
        if not self.composition:
            raise ValueError("V2 clip missing composition_json")

        if not self.composition.get("tracks"):
            raise ValueError("Composition has no tracks")

        duration = self.composition.get("durationInFrames", 0)
        if duration <= 0:
            raise ValueError("Composition has zero duration")

        logger.info(
            f"V2 clip validated: {duration} frames "
            f"({duration / 30:.1f}s), "
            f"{len(self.composition['tracks'])} tracks"
        )

    def _render_composition(
        self,
        orientation: str,
        width: int,
        height: int,
        output_path: str
    ):
        """
        Render the composition via Node.js subprocess.

        The Node.js script uses @remotion/renderer's renderMedia() to:
        1. Load the pre-bundled Remotion compositions
        2. Pass composition_json as inputProps
        3. Render each frame via headless Chromium
        4. Encode to H.264 via NVIDIA h264_nvenc
        """
        logger.info(f"Rendering {orientation} ({width}x{height})...")

        # Write composition JSON to a temp file (avoids arg length limits)
        comp_file = os.path.join(self.temp_dir, f"composition_{orientation}.json")
        with open(comp_file, "w") as f:
            json.dump(self.composition, f)

        result = subprocess.run(
            [
                "node", RENDER_SCRIPT,
                "--input", comp_file,
                "--output", output_path,
                "--width", str(width),
                "--height", str(height),
            ],
            capture_output=True,
            text=True,
            timeout=RENDER_TIMEOUT,
            cwd=RENDERER_DIR,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Remotion render failed ({orientation}): {result.stderr[-500:]}"
            )

        if not os.path.exists(output_path):
            raise RuntimeError(f"Render output missing: {output_path}")

        file_size = os.path.getsize(output_path)
        logger.info(f"Rendered {orientation}: {file_size / 1024 / 1024:.1f} MB")

    def _generate_thumbnails(self):
        """Generate thumbnails from rendered clips (same approach as v1)."""
        # Get duration for thumbnail timing
        duration = self.composition["durationInFrames"] / 30
        thumb_time = duration * 0.1  # 10% into the video

        run_ffmpeg(
            [
                "-ss", str(thumb_time),
                "-i", self.horizontal_clip_path,
                "-vframes", "1",
                "-vf", f"scale={THUMB_HORIZONTAL[0]}:{THUMB_HORIZONTAL[1]}",
                "-q:v", "2",
                self.horizontal_thumb_path,
            ],
            description="Generate horizontal thumbnail",
        )

        run_ffmpeg(
            [
                "-ss", str(thumb_time),
                "-i", self.vertical_clip_path,
                "-vframes", "1",
                "-vf", f"scale={THUMB_VERTICAL[0]}:{THUMB_VERTICAL[1]}",
                "-q:v", "2",
                self.vertical_thumb_path,
            ],
            description="Generate vertical thumbnail",
        )

    async def _upload_to_s3(self):
        """Upload rendered files to S3 (same pattern as v1)."""
        user_id = self.user_clip_data.get("user_id", "unknown")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_path = f"user_clips/{user_id}/{timestamp}_{self.user_clip_id}"

        files_to_upload = []
        for local_path, remote_name in [
            (self.horizontal_clip_path, "horizontal_clip.mp4"),
            (self.vertical_clip_path, "vertical_clip.mp4"),
            (self.horizontal_thumb_path, "horizontal_thumbnail.jpg"),
            (self.vertical_thumb_path, "vertical_thumbnail.jpg"),
        ]:
            if os.path.exists(local_path):
                files_to_upload.append((local_path, f"{base_path}/{remote_name}"))

        if not files_to_upload:
            raise RuntimeError("No files to upload")

        results = self.storage_client.upload_files_parallel(files_to_upload, max_workers=4)

        for local_path, url in results:
            if url is None:
                logger.error(f"Failed to upload: {local_path}")
                continue
            if "horizontal_clip.mp4" in local_path:
                self.output_urls["horizontal_clip_url"] = url
            elif "vertical_clip.mp4" in local_path:
                self.output_urls["vertical_clip_url"] = url
            elif "horizontal_thumbnail.jpg" in local_path:
                self.output_urls["horizontal_thumbnail_url"] = url
            elif "vertical_thumbnail.jpg" in local_path:
                self.output_urls["vertical_thumbnail_url"] = url

    async def _generate_transcript(self):
        """
        Generate transcript using Whisper (same as v1).

        Even though subtitles may already be embedded visually in the rendered
        video, we still run Whisper on the rendered output to get a clean text
        transcript for the DB (used for search, sharing, etc.).
        """
        try:
            from app.shared.transcription import Transcriber

            audio_path = os.path.join(self.temp_dir, "audio.wav")
            success = run_ffmpeg(
                [
                    "-i", self.horizontal_clip_path,
                    "-ac", "1",
                    "-ar", "16000",
                    "-vn",
                    audio_path,
                ],
                description="Extract audio for transcription",
            )
            if not success:
                logger.warning("Failed to extract audio, skipping transcription")
                return

            transcriber = Transcriber()
            result = transcriber.transcribe(audio_path)

            if result and result.text:
                self.transcript = result.text.strip()
                logger.info(f"Transcript: {len(self.transcript)} characters")
            else:
                logger.warning("Transcription returned empty result")

        except ImportError:
            logger.warning("Transcription module not available")
        except Exception as e:
            logger.warning(f"Transcription failed: {e}")

    async def _update_database_success(self):
        """Update user_clips with success status and URLs."""
        update_data = {
            "status": "completed",
            "clip_url": self.output_urls.get("horizontal_clip_url"),
            "vertical_clip_url": self.output_urls.get("vertical_clip_url"),
            "thumbnail_url": self.output_urls.get("horizontal_thumbnail_url"),
            "vertical_thumbnail_url": self.output_urls.get("vertical_thumbnail_url"),
            "transcript": self.transcript,
            "processing_completed_at": datetime.utcnow().isoformat(),
            "processing_time_clip_creation": round(self.timing.get("render", 0), 2),
            "processing_time_upload": round(self.timing.get("upload", 0), 2),
            "processing_time_transcript": round(self.timing.get("transcript", 0), 2),
            "processing_time_total": round(self.timing.get("total", 0), 2),
            "error_message": None,
        }

        if torch.cuda.is_available():
            update_data["gpu_model"] = torch.cuda.get_device_name(0)

        update_user_clip(self.user_clip_id, update_data)

    async def _update_database_failure(self, error_message: str):
        """Update user_clips with failure status."""
        update_user_clip(self.user_clip_id, {
            "status": "failed",
            "error_message": error_message[:1000],
            "processing_completed_at": datetime.utcnow().isoformat(),
            "processing_time_total": round(self.timing.get("total", 0), 2),
        })

    def _cleanup(self):
        """Remove temp directory."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    def _build_success_response(self) -> Dict[str, Any]:
        return {
            "status": True,
            "user_clip_id": self.user_clip_id,
            "outputs": self.output_urls,
            "transcript": self.transcript,
            "processing_time": self.timing,
            "gpu_info": {
                "available": torch.cuda.is_available(),
                "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            },
        }

    def _build_error_response(self, error: str) -> Dict[str, Any]:
        return {
            "status": False,
            "user_clip_id": self.user_clip_id,
            "error": error,
            "processing_time": self.timing,
        }
```

---

## Node.js Renderer Service

### Project Structure

```
renderer/
├── package.json
├── remotion/
│   ├── index.ts              ← registerRoot entry point
│   └── compositions/         ← Copied from frontend repo
│       ├── MainComposition.tsx
│       ├── ClipSequence.tsx
│       ├── SubtitleOverlay.tsx
│       ├── TextOverlay.tsx
│       ├── ImageOverlay.tsx
│       └── SequenceErrorBoundary.tsx
├── types/
│   └── remotionEditor.ts     ← Copied from frontend repo
├── render-composition.mjs    ← CLI entry point
├── remotion-bundle/           ← Generated at Docker build time
└── tsconfig.json
```

### `package.json`

```json
{
  "name": "mp-ai-remotion-renderer",
  "private": true,
  "type": "module",
  "dependencies": {
    "remotion": "4.0.419",
    "@remotion/renderer": "4.0.419",
    "@remotion/bundler": "4.0.419",
    "@remotion/captions": "4.0.419",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "zod": "3.23.8"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "typescript": "^5.7.0"
  }
}
```

> **Note:** This project uses Zod 3.23.8 directly (not the v4 alias the frontend uses) since the renderer runs standalone.

### `remotion/index.ts`

```typescript
import { registerRoot } from "remotion";
import { Composition } from "remotion";
import { MainComposition } from "./compositions/MainComposition";

const Root: React.FC = () => {
  return (
    <Composition
      id="MainComposition"
      component={MainComposition}
      durationInFrames={1}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{
        tracks: [],
        subtitlesByItemId: {},
      }}
    />
  );
};

registerRoot(Root);
```

### `render-composition.mjs`

```javascript
import { renderMedia, selectComposition } from "@remotion/renderer";
import { parseArgs } from "node:util";
import { readFileSync } from "node:fs";
import path from "node:path";

// Parse CLI arguments
const { values } = parseArgs({
  options: {
    input: { type: "string" },
    output: { type: "string" },
    width: { type: "string" },
    height: { type: "string" },
  },
});

const compositionJson = JSON.parse(readFileSync(values.input, "utf-8"));
const outputPath = values.output;
const width = parseInt(values.width, 10);
const height = parseInt(values.height, 10);

const bundleLocation = path.resolve("./remotion-bundle");

// ── Build per-item subtitle tracks ─────────────────────────────────────────

function buildPerItemSubtitles(composition) {
  const subtitlesByItemId = {};
  if (!composition.subtitles) return subtitlesByItemId;

  const { captions, style } = composition.subtitles;
  const videoItems = composition.tracks
    .flatMap((t) => t.items)
    .filter((i) => i.type === "video");

  for (const item of videoItems) {
    const itemStartMs = (item.from / 30) * 1000;
    const itemEndMs = ((item.from + item.durationInFrames) / 30) * 1000;

    const itemCaptions = captions
      .filter((c) => c.startMs >= itemStartMs && c.endMs <= itemEndMs)
      .map((c) => ({
        ...c,
        startMs: c.startMs - itemStartMs,
        endMs: c.endMs - itemStartMs,
        timestampMs:
          c.timestampMs != null ? c.timestampMs - itemStartMs : null,
      }));

    if (itemCaptions.length > 0) {
      subtitlesByItemId[item.id] = { captions: itemCaptions, style };
    }
  }

  return subtitlesByItemId;
}

// ── Render ──────────────────────────────────────────────────────────────────

const subtitlesByItemId = buildPerItemSubtitles(compositionJson);

const composition = await selectComposition({
  serveUrl: bundleLocation,
  id: "MainComposition",
  inputProps: {
    tracks: compositionJson.tracks,
    subtitlesByItemId,
  },
});

await renderMedia({
  composition: {
    ...composition,
    width,
    height,
    durationInFrames: compositionJson.durationInFrames,
    fps: 30,
  },
  serveUrl: bundleLocation,
  codec: "h264",
  outputLocation: outputPath,
  inputProps: {
    tracks: compositionJson.tracks,
    subtitlesByItemId,
  },
  // GPU-accelerated encoding via NVIDIA NVENC
  ffmpegOverride: ({ args }) => {
    return {
      args: args.map((a) => (a === "libx264" ? "h264_nvenc" : a)),
    };
  },
  // Chromium flags for headless rendering in Docker
  chromiumOptions: {
    gl: "angle",
    enableMultiProcessOnLinux: true,
  },
  // Log progress
  onProgress: ({ progress }) => {
    if (Math.round(progress * 100) % 10 === 0) {
      process.stderr.write(
        `Render progress: ${Math.round(progress * 100)}%\n`
      );
    }
  },
});

process.stderr.write(`Render complete: ${outputPath}\n`);
```

### Pre-bundling (Docker build step)

```bash
npx remotion bundle ./remotion/index.ts --out-dir ./remotion-bundle
```

This creates a static bundle that `renderMedia()` serves to Chromium. Bundling happens once at Docker build time, not per-request.

---

## No Full Video Download — HTTP Range Requests

This is the **key architectural insight** that makes v2 fundamentally different from v1.

### V1 Problem

The v1 processor downloads the **entire 8+ hour parliament session video** (~15-30 GB) to extract 30-60 second clips. This is slow (5-10 min download), wasteful (99.9% of bytes unused), and requires massive temp disk space.

### V2 Solution

Remotion's `<OffthreadVideo>` component uses **HTTP Range requests** under the hood. When headless Chromium renders a frame that needs video at time `T`:

1. Chromium's media decoder sends an HTTP Range request: `Range: bytes=12345678-12356789`
2. The CDN/S3 responds with only those bytes (typically 50-200 KB per request)
3. Chromium decodes the frame and renders it into the React component tree
4. Remotion captures the rendered frame

**Result:** Only the needed byte ranges are fetched. For a 60-second clip from an 8-hour video, this fetches ~50-100 MB instead of ~20 GB.

### Requirements for Range Requests to Work

1. **Source video URL must be publicly accessible** (or use a signed URL with sufficient TTL)
2. **CDN/S3 must support Range requests** (S3 and DigitalOcean Spaces both do by default)
3. **Source video must be MP4 with moov atom at the start** (so the browser can seek without downloading the whole file). Our parliament session videos are already encoded this way (`-movflags +faststart`)
4. **No video download step in the Python processor** — the Node.js renderer handles all video access via Chromium

### What This Means for the Processor

The `UserClipProcessorV2` has **no video download step**. Compare:

| Step | V1 (`UserClipProcessor`) | V2 (`UserClipProcessorV2`) |
|------|--------------------------|----------------------------|
| 1 | Fetch clip data from DB | Fetch composition_json from DB |
| 2 | **Download full 8hr video (5-10 min, 20+ GB)** | *(skipped)* |
| 3 | FFmpeg extract segments | *(skipped — Remotion handles via Range requests)* |
| 4 | FFmpeg concat segments | *(skipped — Remotion handles sequencing)* |
| 5 | FFmpeg create vertical crop | Render landscape via Remotion |
| 6 | FFmpeg watermark | Render vertical via Remotion |
| 7 | Generate thumbnails | Generate thumbnails (same) |
| 8 | Upload to S3 | Upload to S3 (same) |
| 9 | Whisper transcription | Whisper transcription (same) |
| 10 | Update DB | Update DB (same) |

---

## Transcription (Same as V1)

The v2 processor runs Whisper transcription on the **rendered output** (not the source video), using the exact same `Transcriber` class as v1:

```python
from app.shared.transcription import Transcriber

# Extract audio from rendered horizontal clip
run_ffmpeg([
    "-i", self.horizontal_clip_path,
    "-ac", "1", "-ar", "16000", "-vn",
    audio_path,
])

# Transcribe with Whisper (GPU-accelerated, same model as v1)
transcriber = Transcriber()
result = transcriber.transcribe(audio_path)
self.transcript = result.text.strip()
```

Even though the editor may have embedded visual subtitles (burned into the video), we still run Whisper because:
1. The DB `transcript` field is used for **text search** across clips
2. The transcript is used for **clip sharing** (text-based previews)
3. Not all clips have subtitles enabled by the user

---

## Feature Mapping: JSON → Remotion Components

| Feature | JSON Fields | Remotion Component | Implementation |
|---|---|---|---|
| Video playback | `src`, `startFrom`, `endAt` | `ClipSequence` → `<OffthreadVideo>` | Direct props, Range requests |
| Speed change | `playbackRate` | `<OffthreadVideo playbackRate={...}>` | Direct prop |
| Audio volume | `volume`, `isMuted` | `ClipSequence` → volume function | `interpolate()` with fade values |
| Audio fade | `audioFadeIn`, `audioFadeOut` | `ClipSequence` → volume function | Frame-based `interpolate()` ramp |
| Visual fade | `opacity` + fade durations | `ClipSequence` → container opacity | Matches audio fade timing |
| Pan/Zoom | `transform.scale`, `translateX/Y` | `ClipSequence` → CSS transform | `translate(X%, Y%) scale(N)` |
| Rotation | `transform.rotation` | `ClipSequence` → CSS transform | `rotate(Ndeg)` |
| Flip | `flipH`, `flipV` | `ClipSequence` → CSS transform | `scaleX(-1)`, `scaleY(-1)` |
| Ken Burns | `keyframes[]` | `ClipSequence` → `interpolateKeyframes()` | Linear interp between transforms |
| Filters | `filters.brightness/contrast/saturation` | `ClipSequence` → CSS filter | `brightness() contrast() saturate()` |
| Text overlay | `text`, `fontSize`, `fontFamily`, etc. | `TextOverlay` | Absolute div, percentage coords |
| Text animation | `animation` | `TextOverlay` | `fade-in`, `slide-in-left/right`, `typewriter` |
| Image overlay | `src`, `imageWidthPercent`, `position` | `ImageOverlay` | `<Img>` with calculated width |
| Subtitles | `subtitles.captions[]`, `style` | `SubtitleOverlay` → `@remotion/captions` | `createTikTokStyleCaptions()` |
| Layer order | tracks array | `MainComposition` | Videos (bottom) → Images → Text (top) |
| Premounting | N/A | `<Sequence premountFor={150}>` | 150-frame buffer for preloading |

### Rendering Layer Order (MainComposition)

1. **Video items** — `<Sequence premountFor={150}>` → `<ClipSequence>` + per-item `<SubtitleOverlay>`
2. **Image items** — `<Sequence premountFor={30}>` → `<ImageOverlay>`
3. **Text items** — `<Sequence>` → `<TextOverlay>`

All items use `from` and `durationInFrames` to control when they appear.

---

## Docker Setup

### Dockerfile

```dockerfile
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# ── System dependencies ─────────────────────────────────────────────────────

# Python
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Chromium dependencies (required by Remotion)
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxrandr2 libxdamage1 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Fonts (Inter is the default editor font)
RUN apt-get update && apt-get install -y \
    fonts-inter fonts-liberation fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# FFmpeg with NVENC support
RUN apt-get update && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js renderer ────────────────────────────────────────────────────────

WORKDIR /app/renderer

COPY renderer/package.json renderer/package-lock.json ./
RUN npm ci --production

# Ensure Chromium is downloaded for Remotion
RUN npx remotion browser ensure

# Copy compositions and types from frontend repo
COPY renderer/remotion/ ./remotion/
COPY renderer/types/ ./types/
COPY renderer/render-composition.mjs ./
COPY renderer/tsconfig.json ./

# Pre-bundle compositions (one-time build step)
RUN npx remotion bundle ./remotion/index.ts --out-dir ./remotion-bundle

# ── Python handler ───────────────────────────────────────────────────────────

WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# ── Entry point ──────────────────────────────────────────────────────────────

CMD ["python3", "-u", "app/handlers/clip_creator_handler_v2.py"]
```

### Font Installation

The editor uses these fonts for text overlays:
- **Inter** (default) — `fonts-inter` package
- **Arial** — `fonts-liberation` (Liberation Sans is metrically compatible)
- **Georgia** — Available in `fonts-liberation` (Liberation Serif)
- **Courier New** — `fonts-dejavu-core` (DejaVu Sans Mono)
- **Impact** — May need a separate package or manual installation

### GPU Access

RunPod workers provide NVIDIA GPU access. Remotion's FFmpeg encoding uses `h264_nvenc` via the `ffmpegOverride` callback. Verify GPU availability:

```bash
# Inside the container
nvidia-smi
ffmpeg -hide_banner -encoders 2>/dev/null | grep nvenc
```

### Memory Requirements

- **1080p rendering**: ~2-4 GB RAM (Chromium + FFmpeg)
- **Both orientations rendered sequentially**: Peak ~4 GB
- **Recommendation**: Use RunPod instances with at least 8 GB RAM

---

## Error Handling

### Composition Validation

Validate before rendering. The frontend enforces these limits via the Zod schema in `schemas/compositionSchema.ts`:

| Limit | Value |
|---|---|
| Max duration | 108,000 frames (1 hour at 30fps) |
| Max tracks | 20 |
| Max items per track | 200 |
| Max captions | 10,000 |
| Max JSON size | 5 MB (enforced by API) |

### Common Failure Modes

| Failure | Cause | Mitigation |
|---|---|---|
| Video URL inaccessible | CDN signed URL expired, network error | Ensure URLs have long TTL (24h+) |
| Chromium crash | Out of memory during rendering | Use `enableMultiProcessOnLinux: true`, increase RAM |
| NVENC busy | All GPU encoder sessions in use | Render sequentially (not in parallel) |
| Font missing | Text renders with fallback font | Install all required fonts in Docker |
| Render timeout | Composition too long | Enforce `MAX_DURATION_FRAMES` limit |
| Range request fails | S3 throttling or network error | Remotion retries automatically; ensure S3 rate limits are sufficient |

### DB Status Updates

The processor updates the `user_clips` row throughout the pipeline:

```python
# On failure at any point:
update_user_clip(self.user_clip_id, {
    "status": "failed",
    "error_message": error_msg[:1000],
    "processing_completed_at": datetime.utcnow().isoformat(),
})

# On success:
update_user_clip(self.user_clip_id, {
    "status": "completed",
    "clip_url": "https://...",
    "vertical_clip_url": "https://...",
    "thumbnail_url": "https://...",
    "vertical_thumbnail_url": "https://...",
    "transcript": "...",
    "processing_completed_at": datetime.utcnow().isoformat(),
})
```

---

## Testing

### Verify GPU Encoding

```bash
# Check NVENC availability
ffmpeg -hide_banner -encoders 2>/dev/null | grep nvenc
# Should show: h264_nvenc

# Verify Chromium is installed
npx remotion browser ensure
```

### Test Render Locally

```bash
# Write a minimal composition JSON
cat > /tmp/test-composition.json << 'EOF'
{
  "version": 2,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "durationInFrames": 90,
  "tracks": [{
    "id": "t1",
    "name": "Track 1",
    "type": "generic",
    "items": [{
      "id": "i1",
      "type": "text",
      "from": 0,
      "durationInFrames": 90,
      "text": "Hello World",
      "fontSize": 64,
      "fontFamily": "Inter",
      "color": "#ffffff",
      "position": { "x": 0.5, "y": 0.5 },
      "animation": "fade-in"
    }],
    "transitions": []
  }],
  "subtitles": null,
  "metadata": {
    "clipId": "test",
    "userId": "test",
    "teamId": null,
    "createdAt": "2026-01-01T00:00:00Z",
    "outputFormat": "landscape"
  }
}
EOF

# Render
node render-composition.mjs \
  --input /tmp/test-composition.json \
  --output /tmp/test-output.mp4 \
  --width 1920 \
  --height 1080
```

### Validate Schema

```bash
# From the Next.js project
npx tsx -e "
  const { compositionSchema } = require('./schemas/compositionSchema');
  const sample = require('/tmp/test-composition.json');
  const result = compositionSchema.safeParse(sample);
  console.log(result.success ? 'VALID' : result.error.issues);
"
```

### Integration Test Checklist

1. [ ] Fetch composition_json from a real `user_clips` row where `editor_version = 2`
2. [ ] Render landscape (1920x1080) — verify output plays correctly
3. [ ] Render vertical (1080x1920) — verify output plays correctly
4. [ ] Thumbnails generated from rendered clips
5. [ ] Files uploaded to S3 with correct paths
6. [ ] Whisper transcription runs on rendered audio
7. [ ] DB updated with all URLs and transcript
8. [ ] Temp files cleaned up after processing

---

## Files to Create

| File | Location (in `mp-ai-runpod-api/`) | Purpose |
|---|---|---|
| `app/handlers/clip_creator_handler_v2.py` | Handlers | RunPod entry point |
| `app/api/clip_creator_v2/__init__.py` | API | Package init |
| `app/api/clip_creator_v2/router.py` | API | Request handling |
| `app/shared/user_clip_processor_v2.py` | Shared | V2 processing pipeline |
| `renderer/package.json` | Renderer | Node.js dependencies |
| `renderer/render-composition.mjs` | Renderer | CLI rendering script |
| `renderer/remotion/index.ts` | Renderer | Remotion entry point |
| `renderer/remotion/compositions/*.tsx` | Renderer | Copied from frontend |
| `renderer/types/remotionEditor.ts` | Renderer | Copied from frontend |
| `renderer/tsconfig.json` | Renderer | TypeScript config |
| `Dockerfile.v2` | Root | V2 Docker image |

## Files Reused from V1

| File | What's Reused |
|---|---|
| `app/handlers/common.py` | `configure_logging`, `start_idle_watchdog`, `register_sigterm_handler`, `wrap_result_with_refresh`, `flush_output`, `set_current_job_id`, `increment_jobs_processed` |
| `app/shared/storage.py` | `StorageClient.upload_files_parallel()` |
| `app/shared/transcription.py` | `Transcriber.transcribe()` |
| `app/shared/supabase_client.py` | `fetch_user_clip()`, `update_user_clip()` |
| `app/shared/state.py` | `increment_requests()` |

## Frontend Files Referenced (Copy to `renderer/`)

| Source (in `new-mpai-frontend/`) | Purpose |
|---|---|
| `remotion/compositions/MainComposition.tsx` | Root composition — renders layers |
| `remotion/compositions/ClipSequence.tsx` | Video playback, transforms, keyframes, audio fade |
| `remotion/compositions/SubtitleOverlay.tsx` | TikTok-style word highlighting |
| `remotion/compositions/TextOverlay.tsx` | Text with animations |
| `remotion/compositions/ImageOverlay.tsx` | Image overlays |
| `remotion/compositions/SequenceErrorBoundary.tsx` | Error boundary for video sequences |
| `types/remotionEditor.ts` | TypeScript type definitions |
