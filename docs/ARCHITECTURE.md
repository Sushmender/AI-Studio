# AI-Studio — Architecture Guide

## System Overview

AI-Studio is a full-stack application that lets users generate AI images and videos through a **3-stage structured pipeline**. The backend is a FastAPI async server; the frontend is a React SPA built with Vite.

---

## Component Diagram

```
╔══════════════════════════════════════════════════════════════════╗
║                         BROWSER                                 ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │                      React SPA (Vite)                    │   ║
║  │                                                          │   ║
║  │  ┌─────────────────┐    ┌──────────────────────────┐    │   ║
║  │  │  PromptConsole  │    │  ImageAttributeEditor     │    │   ║
║  │  │  (mode select   │──►│  VideoAttributeEditor     │    │   ║
║  │  │   + input)      │    │  (inline editable rows)   │    │   ║
║  │  └─────────────────┘    └─────────────┬────────────┘    │   ║
║  │                                        │                 │   ║
║  │  ┌─────────────────┐    ┌──────────────▼────────────┐    │   ║
║  │  │  ResultGallery  │    │  GeneratingState           │    │   ║
║  │  │  + Lightbox     │◄───│  (cosmic orbit animation) │    │   ║
║  │  └─────────────────┘    └───────────────────────────┘    │   ║
║  │                                                          │   ║
║  │  ┌─────────────────────────────────────────────────┐    │   ║
║  │  │  api/client.js  (fetch wrappers + polling hook) │    │   ║
║  │  └─────────────────────────────────────────────────┘    │   ║
║  └──────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════╝
                              │ HTTP/JSON
╔══════════════════════════════▼═══════════════════════════════════╗
║                       FASTAPI BACKEND                           ║
║                                                                 ║
║  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  ┌───────┐  ║
║  │ /analyse/*   │  │ /generate/*  │  │  /jobs/*  │  │/health│  ║
║  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘  └───┬───┘  ║
║         │                 │                 │             │      ║
║  ┌──────▼─────────────────▼─────┐  ┌───────▼──────┐     │      ║
║  │       groq_client.py         │  │  job_store.py│     │      ║
║  │  analyse_image_attributes()  │  │  (asyncio    │     │      ║
║  │  analyse_video_attributes()  │  │   Lock dict) │     │      ║
║  │  synthesize_image_prompt()   │  └──────────────┘     │      ║
║  │  synthesize_video_prompt()   │                        │      ║
║  └──────────────────────────────┘  ┌───────────────────┐ │      ║
║                                    │  fal_client.py    │ │      ║
║  ┌──────────────────────────────┐  │  replicate_       │ │      ║
║  │   rate_limiter.py            │  │  client.py        │ │      ║
║  │   (IP sliding window 10/60s) │  └───────────────────┘ │      ║
║  └──────────────────────────────┘                         │      ║
║                                    ┌───────────────────┐  │      ║
║  ┌──────────────────────────────┐  │  health probes    │◄─┘      ║
║  │  retry.py + logger.py        │  │  (cached 30 s)    │         ║
║  └──────────────────────────────┘  └───────────────────┘         ║
╚═════════════════════════════════════════════════════════════════╝
                              │
         ┌────────────────────┼─────────────────────┐
         ▼                    ▼                      ▼
    ┌──────────┐       ┌───────────┐          ┌──────────┐
    │  Groq     │       │  fal.ai   │          │Replicate │
    │ (free)    │       │ FLUX Dev  │          │Luma Ray  │
    │ text only │       │ image gen │          │video gen │
    └──────────┘       └───────────┘          └──────────┘
```

---

## Data Flow — 3-Stage Image Pipeline

```
1. User enters description
   ────────────────────────
   "A lone astronaut on Mars at sunset"
              │
              ▼
2. POST /analyse/image  (Groq Call 1)
   ─────────────────────────────────
   Groq extracts 5 structured attributes:
   {
     subject:     "Astronaut in full space suit",
     action:      "Standing, gazing upward",
     location:    "Martian surface at sunset",
     composition: "Low angle wide shot",
     style:       "Cinematic realism, amber palette"
   }
              │
              ▼
3. User edits attributes in ImageAttributeEditor
   ─────────────────────────────────────────────
   User can click any row and refine the value.
              │
              ▼
4. POST /generate/image  (attributes in body)
   ──────────────────────────────────────────
   → HTTP 202 returned immediately with job_id
   → Background asyncio.Task starts
              │
              ▼ (background)
5. Groq Call 2 — Synthesize  (synthesize_image_prompt)
   ────────────────────────────────────────────────────
   Groq weaves the 5 confirmed attributes into an
   optimised fal.ai / FLUX Dev prompt string.
   Falls back to manual concatenation on Groq failure.
              │
              ▼
6. fal.ai / FLUX Dev  (fal_client.py)
   ───────────────────────────────────
   Sends synthesized prompt + image params.
   Returns CDN URL (PNG).
              │
              ▼
7. job_store.update_job(status=done, result_url=...)
   Frontend polling detects done → shows result
```

---

## Data Flow — 3-Stage Video Pipeline

Same pattern, but with 10 attributes and Replicate:

```
User description
    │
    ▼ POST /analyse/video
Groq Call 1 → 10 video attributes
    │
    ▼ User edits in VideoAttributeEditor
    │
    ▼ POST /generate/video
HTTP 202 + job_id (estimated_wait_seconds: 180)
    │
    ▼ background task
Groq Call 2 → synthesize_video_prompt()
    │
    ▼
Replicate / Luma Ray Flash 2 720p
    │
    ▼
CDN URL (MP4) → job_store done
    │
    ▼
Frontend polling → ResultGallery shows video
```

---

## Backend Components

### `backend/main.py`

- Creates FastAPI app with lifespan
- Registers CORS middleware (localhost:5173, localhost:3000)
- Registers all 4 routers
- Starts the background **TTL cleanup loop** (runs every hour, purges jobs > 24 h old)
- Global exception handler (never exposes raw stack traces)

### `backend/config.py`

- `pydantic-settings` `Settings` class — loads all config from `.env`
- `get_settings()` is cached with `@lru_cache` (singleton)
- **Never logs key values** — only confirms they are set (bool)

### `backend/models/schemas.py`

All Pydantic v2 models. Key types:

| Model | Purpose |
|-------|---------|
| `GenerateRequest` | Input for `/generate/*` — supports both structured and legacy modes |
| `ImageAttributes` | 5 image attributes (subject, action, location, composition, style) |
| `VideoAttributes` | 10 video attributes across 3 groups |
| `JobRecord` | Internal in-memory job state |
| `JobStatusResponse` | Response for `/jobs/{id}/status` |
| `JobResultResponse` | Response for `/jobs/{id}/result` (includes CDN URL) |
| `HealthResponse` | Response for `/health` |

### `backend/clients/groq_client.py`

4 async functions:

| Function | Groq Call | Purpose |
|----------|-----------|---------|
| `enhance_prompt(prompt, mode)` | — | Legacy: enhance raw prompt |
| `analyse_image_attributes(desc)` | Call 1 | Extract 5 image attributes |
| `analyse_video_attributes(desc)` | Call 1 | Extract 10 video attributes |
| `synthesize_image_prompt(attrs)` | Call 2 | Weave attributes into fal.ai prompt |
| `synthesize_video_prompt(attrs)` | Call 2 | Weave 10 attributes into Replicate prompt |

**Model fallback:** If the primary Groq model hits a rate limit, falls back to `llama-3.1-8b-instant` and logs `groq_model_fallback`.

### `backend/clients/fal_client.py`

- `generate_image(prompt, width, height, num_inference_steps, job_id)`
- Uses `fal_client` SDK with 30 s timeout
- When `MOCK_GENERATION_APIS=True`, returns a placeholder CDN URL immediately

### `backend/clients/replicate_client.py`

- `generate_video(prompt, aspect_ratio, duration, job_id)`
- Uses `replicate` SDK with 360 s timeout
- When `MOCK_GENERATION_APIS=True`, returns a placeholder video URL immediately

### `backend/services/job_store.py`

In-memory job store using a `dict` protected by `asyncio.Lock`.

| Method | Description |
|--------|-------------|
| `create_job(record)` | Insert a new `JobRecord` |
| `update_job(job_id, **fields)` | Partial update (any `JobRecord` field) |
| `get_job(job_id)` | Return `JobRecord` or `None` |
| `list_jobs()` | Return all `JobRecord` values as a list |
| `purge_expired(ttl_hours)` | Delete jobs older than N hours; returns count |

### `backend/services/rate_limiter.py`

IP-based sliding window limiter using a `deque` of timestamps per IP.

- `max_requests=10`, `window_seconds=60` (configurable via Settings or constructor)
- `check(ip)` raises `RateLimitExceeded(retry_after=N)` when over limit
- Thread/coroutine safe via `asyncio.Lock`

### `backend/utils/retry.py`

`@async_retry(max_attempts, backoff_base)` decorator with exponential backoff.

| Exception | Behaviour |
|-----------|-----------|
| `NonRetryableError` | Raised immediately, no retries (4xx, auth errors) |
| `RetryableError` | Retried up to `max_attempts` (5xx, timeout) |
| Any other exception | Treated as retryable |

`retry_count` is bound to `structlog` contextvars after every attempt so it appears automatically in all downstream log lines.

### `backend/utils/logger.py`

`structlog` JSON logger. Standard fields on every log line:

```json
{
  "event": "image_job_done",
  "provider": "fal.ai",
  "model": "fal-ai/flux/dev",
  "job_id": "3fa85f64-...",
  "latency_ms": 8432.1,
  "retry_count": 0,
  "timestamp": "2026-09-03T06:00:12Z"
}
```

### `backend/utils/tasks.py`

`log_task_exception` — a done-callback for `asyncio.create_task()`. Ensures background task exceptions surface in structured logs instead of being silently swallowed.

---

## Frontend Components

| Component | Purpose |
|-----------|---------|
| `App.jsx` | HUD header, starfield background, top-level state |
| `PromptConsole.jsx` | Mode selector, description input, analyse/generate button |
| `ImageAttributeEditor.jsx` | 5 editable attribute rows for image mode |
| `VideoAttributeEditor.jsx` | 10 editable attribute rows for video mode |
| `GeneratingState.jsx` | Cosmic orbit animation with live timer |
| `ResultGallery.jsx` | CSS grid of completed jobs; persisted via `localStorage` |
| `Lightbox.jsx` | Full-screen overlay; download button; Escape key |
| `JobStatusStrip.jsx` | Real-time status bar during generation |
| `ErrorState.jsx` | Handles all 7 error states with recovery UI |
| `ErrorBoundary.jsx` | React error boundary wrapping the entire app |

### `api/client.js`

Typed fetch wrappers for all backend endpoints:

```javascript
analyseImage(description)          // POST /analyse/image
analyseVideo(description)          // POST /analyse/video
generateImage(request)             // POST /generate/image
generateVideo(request)             // POST /generate/video
getJobStatus(jobId)                // GET /jobs/{id}/status
getJobResult(jobId)                // GET /jobs/{id}/result
getHealth()                        // GET /health
```

### `hooks/useJobPolling.js`

Polls `/jobs/{id}/status` on an interval until `done` or `failed`.

- Image jobs: every **2 seconds**
- Video jobs: every **5 seconds**
- Exposes `{ status, result, error, elapsedMs, estimatedWait }`

---

## Design System — Cosmic Observatory

Defined in `frontend/src/index.css`:

| Token | Value |
|-------|-------|
| Background | `#090b0f` (deep space black) |
| Primary accent | `#c9a227` (golden amber) |
| Display font | `Outfit` (Google Fonts) |
| Body font | `Inter` (Google Fonts) |
| Code font | `JetBrains Mono` |
| Panel style | Glassmorphism + amber-tinted borders |

Key animations:
- **CSS Starfield** — 50+ star positions via `::after` pseudo-element
- **Bokeh glow** — Radial gradients behind panels
- **Cosmic orbit** — `GeneratingState.jsx` uses two counter-rotating orbital rings with pulsing amber core

---

## Security Considerations

| Risk | Mitigation |
|------|-----------|
| API key exposure | Keys loaded only server-side; never logged, never in responses |
| Stack trace leakage | Global exception handler returns sanitised `{"error": "internal_error"}` |
| Prompt injection | Groq system prompts use strict JSON output schemas; malformed responses trigger fallback |
| Rate abuse | IP sliding window; `Retry-After` header on 429 |
| Job data leakage | Jobs are in-memory only; purged after 24 h; no auth required (POC scope) |

---

## Deployment Notes

> ⚠️ This is an internal POC. It is **not** hardened for production use.

Known limitations to address before production:
- **No persistence** — jobs lost on server restart (use Redis or a DB)
- **No auth** — any local user can submit jobs
- **Single worker** — asyncio is single-threaded; add `--workers N` only with a persistent job store
- **CORS** — hardcoded to `localhost:5173`; update `CORS_ORIGINS` in `.env`
- **CDN expiry** — fal.ai and Replicate CDN links expire in ~24 h; implement result archival if needed
