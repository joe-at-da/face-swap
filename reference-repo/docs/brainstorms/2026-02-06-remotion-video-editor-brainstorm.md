# Remotion Video Editor - Brainstorm

**Date:** 2026-02-06
**Status:** Ready for planning
**Replaces:** Current custom video editor at `/dashboard/create-clips/edit-clip/[clipId]`

---

## What We're Building

A full-featured video editor built on Remotion that replaces the existing custom HTML5 video editor. The editor allows UK MPs and staff to create polished clips from parliament session videos with subtitles, transitions, text overlays, zoom/crop, speed control, and audio mixing.

### Core Capabilities

1. **Remotion Player Preview** - Frame-accurate, rendered preview using `@remotion/player` instead of native `<video>` playback
2. **Multi-track Timeline** - Drag-and-drop timeline with zoom, snapping, cut/trim operations
3. **Clip Library** - Browse pre-cut MP clips and full session videos (8+ hours), add segments to timeline
4. **Subtitles** - AI-generated (OpenAI Whisper API) word-level captions with inline editing on the preview, TikTok-style highlighting
5. **Transitions** - Fade, crossfade, slide, wipe between clips using `@remotion/transitions`
6. **Text Overlays** - Lower thirds, titles, annotations with frame-based animations
7. **Zoom/Crop** - Ken Burns effect, crop regions, animated zoom
8. **Speed Control** - Slow motion and fast-forward via `playbackRate`
9. **Audio Mixing** - Per-clip volume control, muting, fade in/out
10. **Watermark** - Configurable watermark overlay with position control
11. **JSON Export** - Serialize the full composition as JSON for server-side rendering on RunPod

### Output Formats

- Landscape: 1920x1080 (16:9)
- Vertical: 1080x1920 (9:16) for social media

---

## Why This Approach

### Full Custom Build with Remotion

We chose to build the editor from scratch using Remotion's component library rather than using the commercial Editor Starter or adapting the existing editor. Reasons:

- **Complete control** over the UX tailored to the parliament clip workflow
- **No commercial license dependency** - uses Remotion's free tier
- **Clean architecture** - no technical debt from the current editor
- **Deep integration** with existing clip library, session data, and Supabase backend
- **JSON-serializable compositions** are a natural output for RunPod rendering

### Why Not Keep the Current Editor

The current editor uses native HTML5 `<video>` with custom controls. It cannot:
- Render text overlays, subtitles, or effects in the preview
- Apply transitions between clips
- Do frame-accurate seeking with effects composited
- Produce a composition definition that a renderer can reproduce exactly

Remotion solves all of these by treating video as React components.

---

## Key Decisions

### 1. Remotion Player for Preview Only
- The browser renders a real-time preview via `<Player>`
- No FFmpeg or heavy rendering in the browser
- Server-side rendering happens on RunPod (separate concern, documented below)

### 2. OffthreadVideo for Long Sessions
- Parliament sessions can be 8+ hours
- `<OffthreadVideo>` uses range requests to load only needed segments
- Videos are chunked via `<Sequence>` components with `premountFor` for smooth transitions
- Full session browsing uses lazy-loaded segments, not the entire video

### 3. Subtitles via OpenAI Whisper API
- Next.js Server Action calls OpenAI Whisper API with the video/audio segment
- Returns word-level timestamps in `@remotion/captions` `Caption` format
- Displayed using `createTikTokStyleCaptions()` for word-level highlighting
- Users edit subtitle text inline on the video preview
- Subtitle timing adjustable by dragging blocks on the timeline

### 4. State Management with Legend State v3
- Continue using Legend State for reactive state (consistent with rest of app)
- Stores: `editorStore` (tracks, items, effects), `playerStore` (playback state), `subtitleStore` (captions data)
- Composition JSON derived from store state
- Auto-save to localStorage per clip session

### 5. Clip Extend/Trim from Edges (Source-Aware Clips)

All imported clips are segments of a full parliament session video. Every clip knows its `startTimestamp` and `endTimestamp` within the session, and the full session video URL is always available.

**Trim (shrink):** Drag a clip edge inward to shorten it. Standard behavior — reduces the visible portion.

**Extend (grow):** Drag a clip edge outward to reveal more of the full session video beyond the original clip boundaries. This works because the clip is just a window into the longer session video.

- Extending the left edge moves `currentStartTimestamp` earlier in the session video
- Extending the right edge moves `currentEndTimestamp` later in the session video
- The limit is the session start (0:00) on the left and session end on the right
- The Remotion `<OffthreadVideo>` uses `startFrom` and duration to control which portion of the source video plays
- No visual distinction between original and extended portions — seamless experience

**Data model implications:**
- Each timeline item stores both `original` timestamps (the AI-clipped boundaries) and `current` timestamps (after user trim/extend)
- The `src` for all clips from the same session points to the same full session video URL
- `startFrom` in the Remotion composition is calculated from `currentStartTimestamp` relative to the session video
- This means any clip can theoretically be extended to cover the entire session

### 6. Frame-Based Everything
- All animations use `useCurrentFrame()` + `interpolate()` - no CSS animations
- Ensures preview matches server render exactly
- Transitions use `<TransitionSeries>` with `linearTiming` or `springTiming`

### 6. Output Format: JSON Composition
- The editor produces a JSON object describing the full composition
- This JSON is stored in the database and sent to RunPod for rendering
- Schema validated with Zod for type safety

---

## Composition JSON Output Schema (Documented)

The editor outputs a JSON object that fully describes the video composition for server-side rendering. This is what gets sent to the RunPod Remotion renderer.

```typescript
// Root composition output
interface VideoComposition {
  version: 1;
  fps: 30;
  width: 1920;
  height: 1080;
  durationInFrames: number;

  tracks: Track[];
  subtitles: SubtitleTrack | null;
  watermark: WatermarkConfig | null;

  metadata: {
    clipId: string;           // Source parliament_member_clips ID
    userId: string;
    teamId: string | null;
    createdAt: string;        // ISO timestamp
    outputFormat: "landscape" | "vertical";
  };
}

// Track containing timeline items
interface Track {
  id: string;
  name: string;
  items: TimelineItem[];
}

// Individual item on the timeline
interface TimelineItem {
  id: string;
  type: "video" | "text" | "image";
  from: number;              // Start frame on timeline
  durationInFrames: number;

  // Video-specific
  src?: string;              // Full session video URL (all clips from same session share this)
  startFrom?: number;        // Frame offset in source video (current, after trim/extend)
  endAt?: number;            // End frame in source video (current, after trim/extend)
  playbackRate?: number;     // Speed (0.25 - 4.0)
  volume?: number;           // Audio volume (0 - 1)
  isMuted?: boolean;

  // Source clip metadata (for extend/trim limits)
  sourceClip?: {
    clipId: string;                    // parliament_member_clips ID
    originalStartMs: number;           // Original AI-clipped start (ms in session)
    originalEndMs: number;             // Original AI-clipped end (ms in session)
    sessionDurationMs: number;         // Full session length (max extend limit)
    mpName: string;                    // MP display name
    transcript: string;                // Original clip transcript
  };

  // Transform
  transform?: {
    scale?: number;          // Zoom level
    translateX?: number;     // Pan X
    translateY?: number;     // Pan Y
    rotation?: number;       // Degrees
    cropRect?: { x: number; y: number; width: number; height: number };
  };

  // Keyframes for animated transforms
  keyframes?: {
    frame: number;
    transform: TimelineItem["transform"];
  }[];

  // Text-specific
  text?: string;
  fontSize?: number;
  fontFamily?: string;
  color?: string;
  backgroundColor?: string;
  position?: { x: number; y: number };
  animation?: "none" | "fade-in" | "slide-in-left" | "slide-in-right" | "typewriter";
}

// Transition between items
interface Transition {
  type: "fade" | "slide" | "wipe" | "crossfade" | "flip" | "clock-wipe";
  durationInFrames: number;
  timing: "linear" | "spring";
  direction?: "from-left" | "from-right" | "from-top" | "from-bottom";
  // Placed between consecutive items - items[n] -> transition -> items[n+1]
  afterItemId: string;
  beforeItemId: string;
}

// Subtitle track
interface SubtitleTrack {
  captions: Caption[];       // @remotion/captions format
  style: {
    fontSize: number;
    fontFamily: string;
    color: string;
    highlightColor: string;  // Active word color
    backgroundColor: string; // Caption background
    position: "bottom" | "center" | "top";
    maxWordsPerLine: number;
  };
}

// Individual caption (matches @remotion/captions Caption type)
interface Caption {
  text: string;
  startMs: number;
  endMs: number;
  timestampMs: number | null;
  confidence: number | null;
}

// Watermark configuration
interface WatermarkConfig {
  src: string;               // Image URL
  position: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center";
  opacity: number;           // 0 - 1
  scale: number;             // Size relative to video (e.g., 0.15 = 15% of width)
}
```

### How the JSON Maps to Remotion Components

| JSON Field | Remotion Component |
|---|---|
| `tracks[].items[]` | `<Sequence>` wrapping `<OffthreadVideo>` or text component |
| `transitions[]` | `<TransitionSeries.Transition>` with presentation from `@remotion/transitions` |
| `subtitles` | `<Sequence>` per caption page using `createTikTokStyleCaptions()` |
| `watermark` | Absolutely positioned `<Img>` component |
| `item.playbackRate` | `<OffthreadVideo playbackRate={...}>` |
| `item.volume` | `<OffthreadVideo volume={...}>` |
| `item.transform` | CSS `transform` + `clip-path` on wrapper div |
| `item.keyframes` | `interpolate()` between keyframe values |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  Page: /dashboard/create-clips/edit-clip/[clipId]   │
│  (Server Component - fetches clips, session data)   │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │     RemotionEditorLayout    │
        │     (Client Component)      │
        └──────┬──────────┬───────────┘
               │          │
    ┌──────────▼──┐  ┌────▼────────────────┐
    │  Preview    │  │  Side Panel          │
    │  Panel      │  │  - Clips Library     │
    │  ┌────────┐ │  │  - Full Session      │
    │  │Remotion│ │  │  - Subtitles         │
    │  │Player  │ │  │  - Text Overlays     │
    │  └────────┘ │  │  - Effects           │
    │  Controls   │  │  - Watermark         │
    └──────┬──────┘  │  - Export            │
           │         └────────────────────────┘
    ┌──────▼──────────────────────────┐
    │  Timeline                       │
    │  ┌─────────────────────────┐    │
    │  │ Track 1: Video clips    │    │
    │  │ Track 2: Text overlays  │    │
    │  │ Track 3: Subtitles      │    │
    │  │ Track 4: Audio          │    │
    │  └─────────────────────────┘    │
    │  Zoom | Playhead | Snapping     │
    └─────────────────────────────────┘
               │
    ┌──────────▼──────────────────────┐
    │  Legend State Stores            │
    │  editorStore → composition JSON │
    │  playerStore → playback state   │
    │  subtitleStore → captions data  │
    └─────────────────────────────────┘
```

### Export Flow

```
Editor → JSON Composition → POST /api/clips/create → Store in DB →
  Webhook → RunPod Remotion Renderer → Output video → Update user_clips
```

---

## Refined Design Decisions

### 7. Timeline UI Design

**Track Structure: Fully Flexible**
- Users can add any number of any track type (video, text, audio, subtitle)
- No predefined track limits
- Tracks can be reordered via drag-and-drop
- Empty tracks can be removed

**Zoom & Navigation: Full Controls**
- Zoom slider in timeline toolbar
- Ctrl+scroll wheel for horizontal zoom
- Pinch-to-zoom on trackpad
- "Fit to view" button (shows entire timeline)
- "Zoom to selection" (zoom into selected clip)
- Minimap overview bar at the top of the timeline for long compositions
- Auto-scroll to keep playhead visible during playback

**Keyboard Shortcuts: Premiere Pro Style**
| Shortcut | Action |
|---|---|
| Space | Play/Pause |
| J | Shuttle reverse |
| K | Stop / pause shuttle |
| L | Shuttle forward (tap multiple times for faster) |
| C | Razor/Cut tool (cuts at playhead) |
| V | Selection tool |
| I | Mark in point |
| O | Mark out point |
| [ | Trim start to playhead |
| ] | Trim end to playhead |
| Delete/Backspace | Delete selected clip |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| Ctrl+D | Apply default transition |
| +/- | Zoom in/out timeline |
| Home/End | Jump to start/end |
| Arrow Left/Right | Move playhead 1 frame |
| Shift+Arrow | Move playhead 10 frames |

**Snapping & Alignment**
- Magnetic snapping to clip edges (toggleable)
- Snap to playhead position
- Snap threshold: 0.5 seconds (adjustable)
- Visual snap guides shown during drag

### 8. Subtitle Editing UX

**Interaction Model: Click-to-Edit on Preview**
- Subtitles display on the video preview with word-level highlighting during playback
- Click on any subtitle word in the preview to enter edit mode
- Double-click to select a word for replacement
- Drag subtitle blocks on the subtitle timeline track to adjust timing
- Backspace/Delete removes a word and redistributes timing
- Enter confirms edit and moves to next subtitle block

**Whisper Transcription: On-Demand Per Clip**
- User selects a clip on the timeline and clicks "Generate Subtitles"
- Next.js Server Action sends the audio segment to OpenAI Whisper API
- Returns word-level timestamps in `@remotion/captions` `Caption` format
- Subtitles automatically placed on a subtitle track aligned with the clip
- Loading state shown while transcription is in progress

**Subtitle Styling: Full Customization**
- Font family (from a curated list of web-safe + Google Fonts)
- Font size (px, responsive to video dimensions)
- Text color + active/highlight word color
- Background color and opacity (per-word or full line)
- Text shadow and outline (stroke width + color)
- Position: top, center, bottom (with vertical offset)
- Max words per line (controls line wrapping)
- Animation: none, fade word, scale word, karaoke sweep

### 9. Side Panel Organization

**Layout: Tabbed Asset Browser + Context-Sensitive Properties**

The side panel has two modes that work together:

**Asset Browser Tabs** (default when nothing selected):
| Tab | Contents |
|---|---|
| Media | Clip library (MP clips, other MP clips, full session), search, import to timeline |
| Text | Text presets (lower third, title, caption), add to timeline |
| Transitions | Visual grid of transition types (fade, slide, wipe, etc.), drag onto clip junctions |
| Subtitles | Generate subtitles button, subtitle style controls |
| Watermark | Enable/disable, upload, position, opacity |
| Export | Timeline summary, format selection, export button |

**Properties Panel** (appears when a timeline item is selected):
- Replaces the asset browser temporarily
- Shows properties relevant to the selected item type:
  - **Video clip**: Speed, volume, transform (zoom/crop/rotate), trim points, mute toggle
  - **Text overlay**: Text content, font, color, size, animation, position
  - **Subtitle block**: Word text, timing, style overrides
  - **Transition**: Type, duration, timing curve, direction
- "Back" button returns to asset browser

**Transition Application: Dual Method**
- **Drag from Transitions tab**: Browse visually, drag onto the junction between two clips
- **Right-click junction**: Context menu with "Add Transition" > quick-pick dropdown
- **Keyboard shortcut**: Select junction, press Ctrl+D for default transition (fade)
- Default transition type configurable in settings

### 10. Canvas Mode Toggle (Vertical Video)

**How it works:**
- Toggle button in the editor header: "16:9" / "9:16"
- Switching canvas mode changes:
  - Remotion Player dimensions (1920x1080 <-> 1080x1920)
  - Composition `width` and `height` in the JSON output
  - Subtitle positioning recalculates for new aspect ratio
  - Text overlay positions recalculate
  - Video clips get center-cropped by default (user can adjust crop)
- Each format maintains its own crop/position settings per clip
- Export sends the selected format (or both) to RunPod

### 11. Clip Library Browsing UX

**Layout: List + Source Preview (Premiere Pro pattern)**
- Scrollable list of clips showing: thumbnail, MP name, transcript snippet, duration
- Clicking a clip loads it in the Remotion Player as a "source preview" (doesn't affect timeline)
- While previewing, user can press I/O to mark custom in/out points within the clip
- "Insert" button or drag from list to add clip (or marked portion) to timeline at playhead
- Drag directly from the list to a specific timeline position

**Search & Filter:**
- Search by MP name, transcript text, or keywords
- Filter tabs: "My MP's Clips" | "All MPs" | "Full Session"
- Full Session tab shows the waveform/thumbnail strip for browsing the 8hr+ video
- Sort by: time in session (default), duration, relevance to search

**Full Session Browser:**
- Dedicated view for the full parliament session video
- Thumbnail strip / filmstrip showing keyframes at intervals
- User can scrub over the strip, click to preview a spot, then I/O to mark a segment
- Marked segments can be added to timeline as new clips

### 12. Export Workflow

**Simple Export Flow:**
1. User clicks "Export" in the side panel
2. Choose format: Landscape (16:9), Vertical (9:16), or Both
3. Click "Export" to confirm
4. Composition JSON is validated (Zod schema) and saved to DB as a `user_clips` record
5. Status set to `pending_review` → webhook triggers RunPod rendering
6. User sees "Processing" status badge on the clip
7. When RunPod completes, status updates to `completed` and video URL is available

**No in-browser preview rendering** — the Remotion Player already shows an accurate preview.

### 13. Performance Strategy

**Long Video Handling (8hr+ sessions):**
- `<OffthreadVideo>` automatically uses HTTP Range headers — only loads bytes for the visible portion
- Each timeline clip is a `<Sequence>` with `startFrom` pointing to its offset in the session video
- `premountFor={30}` (1 second at 30fps) pre-buffers the next clip before the playhead reaches it
- Clips far from the playhead are automatically unmounted by Remotion
- **Extending a clip** beyond pre-cut boundaries works the same way — just adjusts `startFrom`/duration, and range requests fetch only the new portion. No performance difference between a 30s clip and a 5min extended clip.
- **Critical: Extended clip loading** — When a clip is extended on either side, the Remotion Player loads ONLY from the clip's current start to its current end within the session video. It does NOT load the entire session. The `<OffthreadVideo startFrom={clipStartFrame}>` inside a `<Sequence durationInFrames={clipDuration}>` tells Remotion exactly which byte range to fetch via HTTP Range headers. Example: a clip extended from 2:00:00-2:05:00 in an 8hr session only loads those 5 minutes of video data.

**Full Session Scrubbing Optimization:**
- When user scrubs the full session browser, use debounced seeking (100ms) to avoid excessive range requests
- Show low-res thumbnail strip generated server-side (keyframes every 10s) for instant visual browsing
- Only load actual video data when user clicks to preview a specific spot
- Range requests ensure scrubbing to hour 6 of an 8hr video doesn't need to download hours 1-5

**Timeline Performance (many clips):**
- Timeline item DOM virtualization for 50+ items (only render visible items in viewport)
- Debounce Legend State updates during drag operations (16ms throttle)
- Memoize composition JSON derivation from store state
- Lazy-load side panel tabs (Transitions grid, text presets loaded only when tab opened)

**Remotion Player Optimization:**
- Use `premountFor` on all `<Sequence>` components
- `<OffthreadVideo>` with `transparent={false}` (40% faster than transparent mode)
- Avoid re-rendering composition on every playhead frame — only re-render when track data changes

---

## Resolved Questions

| Question | Decision |
|---|---|
| Whisper transcription | On-demand per clip via Next.js Server Action calling OpenAI Whisper API |
| Vertical video | Canvas mode toggle in editor (16:9 <-> 9:16), per-format crop settings |
| Draft persistence | localStorage only (per clipId), same as current editor |
| Audio library | Not in v1 - only original parliament audio |

## Remaining Open Questions

1. **Remotion licensing** - Remotion Player is free for any use, but server-side rendering requires a license for companies. Need to confirm RunPod rendering licensing requirements.

---

## Dependencies to Add

```json
{
  "@remotion/player": "latest",
  "@remotion/captions": "latest",
  "@remotion/transitions": "latest",
  "@remotion/media-utils": "latest",
  "remotion": "latest"
}
```

No `@remotion/renderer` needed in the Next.js app - rendering happens on RunPod.

---

## What We're NOT Building (Now)

- RunPod rendering infrastructure (separate project, uses composition JSON)
- Background music/sound effects library
- Real-time collaboration
- Version history / undo-redo (could add later with Legend State history)
- Template system (pre-made video templates)
- AI-powered auto-editing suggestions
