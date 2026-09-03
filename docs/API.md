# AI-Studio — API Reference

> **Base URL (local):** `http://localhost:8000`  
> **Interactive docs:** `http://localhost:8000/docs` (Swagger UI)  
> **ReDoc:** `http://localhost:8000/redoc`

All requests and responses are JSON. All timestamps are UTC ISO 8601.

---

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Responses](#error-responses)
- [Root](#root)
- [Health](#health)
- [Analysis](#analysis)
  - [POST /analyse/image](#post-analyseimage)
  - [POST /analyse/video](#post-analysevideo)
- [Generation](#generation)
  - [POST /generate/image](#post-generateimage)
  - [POST /generate/video](#post-generatevideo)
- [Jobs](#jobs)
  - [GET /jobs](#get-jobs)
  - [GET /jobs/{id}/status](#get-jobsidstatus)
  - [GET /jobs/{id}/result](#get-jobsidresult)
- [Schemas](#schemas)

---

## Authentication

This is an internal POC. API keys are backend-only (loaded from `.env`). The frontend and API consumers do **not** supply credentials.

---

## Rate Limiting

All endpoints that trigger AI calls are rate-limited per client IP:

| Limit | Window | Header on 429 |
|-------|--------|----------------|
| 10 requests | 60-second sliding window | `Retry-After: <seconds>` |

```
HTTP/1.1 429 Too Many Requests
Retry-After: 45
Content-Type: application/json

{
  "detail": "Too many requests. Please wait 45 seconds."
}
```

---

## Error Responses

All errors return structured JSON. Raw stack traces are **never** exposed.

| Status | Meaning |
|--------|---------|
| `400` | Bad request / validation error |
| `404` | Job not found or expired |
| `422` | Pydantic schema validation failure |
| `429` | Rate limit exceeded |
| `500` | Internal server error (sanitised) |
| `503` | Upstream AI provider unreachable |

```json
{
  "error": "internal_error",
  "message": "An unexpected error occurred. Please try again."
}
```

---

## Root

### GET /

Service info and link to docs.

**Response 200**
```json
{
  "service": "AI-Studio",
  "version": "0.1.0",
  "docs": "/docs"
}
```

---

## Health

### GET /health

Probe all three AI providers in parallel. Results are **cached for 30 seconds**.

**Response 200**
```json
{
  "status": "ok",
  "services": {
    "fal_ai": {
      "reachable": true,
      "latency_ms": 312.4,
      "error": null
    },
    "replicate": {
      "reachable": true,
      "latency_ms": 185.1,
      "error": null
    },
    "groq": {
      "reachable": true,
      "latency_ms": 94.7,
      "error": null
    }
  },
  "timestamp": "2026-09-03T06:00:00.000Z"
}
```

`status` is `"ok"` when all services are reachable, `"degraded"` otherwise.

**cURL**
```bash
curl http://localhost:8000/health
```

---

## Analysis

The analysis endpoints run **Groq Call 1**: they extract structured attributes from a plain-language description. They are synchronous and return immediately — no job is created.

### POST /analyse/image

Extract 5 visual attributes from a raw image description.

**Request Body**
```json
{
  "description": "A lone astronaut standing on the surface of Mars at sunset, looking up at Earth"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `description` | `string` | ✅ | 1–2000 characters |

**Response 200**
```json
{
  "attributes": {
    "subject": "Astronaut in full space suit",
    "action": "Standing still, gazing upward toward Earth",
    "location": "Martian surface at sunset, red sky with dust haze",
    "composition": "Low angle wide shot, astronaut in foreground, Earth visible in sky",
    "style": "Cinematic realism, warm amber-red palette, epic scale"
  },
  "raw_description": "A lone astronaut standing on the surface of Mars at sunset..."
}
```

**Errors**
- `429` — Rate limit exceeded
- `503` — Groq unreachable or failed to parse structured response

**cURL**
```bash
curl -X POST http://localhost:8000/analyse/image \
  -H "Content-Type: application/json" \
  -d '{"description": "A lone astronaut on Mars at sunset"}'
```

---

### POST /analyse/video

Extract 10 video attributes from a raw video description across 3 groups.

**Request Body**
```json
{
  "description": "A cheetah sprinting across the African savanna at golden hour in slow motion"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `description` | `string` | ✅ | 1–2000 characters |

**Response 200**
```json
{
  "attributes": {
    "subject": "Cheetah, adult male, spotted coat",
    "action": "Full sprint at maximum speed",
    "scene": "African savanna, golden hour, tall grass",
    "style": "Cinematic wildlife documentary",
    "temporal_elements": "240fps slow motion capture, graceful stretched movement",
    "camera_angles": "Low tracking shot at ground level",
    "camera_movements": "Steadicam lateral follow, parallax background",
    "lens_effects": "Shallow depth of field, motion blur on paws",
    "dialogue": "No dialogue — pure visual storytelling",
    "sound_effects": "Wind rush, grass swishing, powerful paw strikes"
  },
  "raw_description": "A cheetah sprinting across the African savanna..."
}
```

**Attribute Groups**

| Group | Fields |
|-------|--------|
| **Overall** | `subject`, `action`, `scene`, `style`, `temporal_elements` |
| **Camera** | `camera_angles`, `camera_movements`, `lens_effects` |
| **Audio** *(informational — Luma is visual-only)* | `dialogue`, `sound_effects` |

**cURL**
```bash
curl -X POST http://localhost:8000/analyse/video \
  -H "Content-Type: application/json" \
  -d '{"description": "A cheetah sprinting in slow motion"}'
```

---

## Generation

Generation endpoints are **asynchronous** — they return a `job_id` immediately (HTTP 202) and run the AI pipeline in the background. Use the Jobs endpoints to poll for results.

### POST /generate/image

Submit an image generation job via **fal.ai / FLUX Dev**.

**Two Modes:**

**Mode A — Structured (recommended):** Pass `attributes` (from `/analyse/image`) for highest quality.

**Mode B — Legacy:** Pass `prompt` only; Groq enhances it before sending to fal.ai.

**Request Body — Structured mode**
```json
{
  "prompt": "",
  "attributes": {
    "subject": "Astronaut in full space suit",
    "action": "Standing still, gazing upward toward Earth",
    "location": "Martian surface at sunset",
    "composition": "Low angle wide shot, Earth visible in sky",
    "style": "Cinematic realism, warm amber-red palette"
  },
  "width": 1024,
  "height": 1024,
  "num_inference_steps": 28
}
```

**Request Body — Legacy mode**
```json
{
  "prompt": "A lone astronaut on Mars at sunset looking at Earth"
}
```

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `prompt` | `string` | `""` | max 2000 chars |
| `mode` | `"image"` \| `"video"` | `"image"` | — |
| `attributes` | `ImageAttributes` | `null` | All 5 fields required if present |
| `width` | `integer` | `1024` | 256–2048 |
| `height` | `integer` | `1024` | 256–2048 |
| `num_inference_steps` | `integer` | `28` | 1–50 |

**Response 202**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "queued",
  "mode": "image",
  "raw_prompt": "Structured image: Astronaut in full space suit",
  "message": "Image generation job queued",
  "estimated_wait_seconds": null
}
```

**cURL**
```bash
curl -X POST http://localhost:8000/generate/image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A red fox running through snow-covered forest at dusk"
  }'
```

---

### POST /generate/video

Submit a video generation job via **Replicate / Luma Ray Flash 2 720p**.

Typical generation time: **2–5 minutes**.

**Request Body — Structured mode**
```json
{
  "prompt": "",
  "video_attributes": {
    "subject": "Cheetah, adult male",
    "action": "Full sprint at maximum speed",
    "scene": "African savanna, golden hour",
    "style": "Cinematic wildlife documentary",
    "temporal_elements": "240fps slow motion",
    "camera_angles": "Low tracking shot",
    "camera_movements": "Steadicam lateral follow",
    "lens_effects": "Shallow depth of field",
    "dialogue": "No dialogue",
    "sound_effects": "Wind rush, grass swishing"
  },
  "aspect_ratio": "16:9",
  "duration": 5
}
```

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `prompt` | `string` | `""` | max 2000 chars |
| `video_attributes` | `VideoAttributes` | `null` | All 10 fields required if present |
| `aspect_ratio` | `string` | `"16:9"` | Pattern: `\d+:\d+` |
| `duration` | `integer` | `5` | 1–20 seconds |

**Response 202**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "queued",
  "mode": "video",
  "raw_prompt": "Structured video: Cheetah, adult male",
  "message": "Video generation job queued — may take 2–5 minutes",
  "estimated_wait_seconds": 180
}
```

---

## Jobs

### GET /jobs

List all jobs, newest first, with pagination.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | `integer` | `20` | Max jobs to return (1–100) |
| `offset` | `integer` | `0` | Skip N jobs (for pagination) |

**Response 200**
```json
{
  "jobs": [
    {
      "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "status": "done",
      "mode": "image",
      "raw_prompt": "A red fox in snow",
      "enhanced_prompt": "A majestic red fox...",
      "provider": "fal.ai",
      "model": "fal-ai/flux/dev",
      "retry_count": 0,
      "created_at": "2026-09-03T06:00:00Z",
      "updated_at": "2026-09-03T06:00:12Z",
      "estimated_wait_seconds": null,
      "error": null,
      "error_type": null
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

**cURL**
```bash
# First page
curl "http://localhost:8000/jobs"

# Second page
curl "http://localhost:8000/jobs?limit=20&offset=20"
```

---

### GET /jobs/{id}/status

Poll the current status of a job by its UUID.

**Safe to call repeatedly.** Recommended intervals:
- Image jobs: every **2 seconds**
- Video jobs: every **5 seconds**

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | `string` (UUID) | Job ID returned from `/generate/*` |

**Job Status Values**

| Status | Meaning |
|--------|---------|
| `queued` | Job created, background task not started yet |
| `generating` | AI provider is processing |
| `done` | Generation complete, CDN URL available |
| `failed` | Generation failed, error details available |

**Response 200**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "generating",
  "mode": "image",
  "raw_prompt": "A red fox in snow",
  "enhanced_prompt": "A majestic red fox running through a snow-covered forest...",
  "provider": "fal.ai",
  "model": "fal-ai/flux/dev",
  "retry_count": 0,
  "created_at": "2026-09-03T06:00:00Z",
  "updated_at": "2026-09-03T06:00:03Z",
  "estimated_wait_seconds": null,
  "error": null,
  "error_type": null
}
```

**Errors**
- `404` — Job not found or expired (TTL 24 h)

**cURL**
```bash
curl "http://localhost:8000/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6/status"
```

---

### GET /jobs/{id}/result

Retrieve the final result of a completed job.

**Response Codes**

| Code | Condition |
|------|-----------|
| `200` | Job is `done` or `failed` — full result returned |
| `202` | Job is still `queued` or `generating` |
| `404` | Job not found or expired |

**Response 200 — done**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "done",
  "mode": "image",
  "raw_prompt": "A red fox in snow",
  "enhanced_prompt": "A majestic red fox running through a snow-covered forest...",
  "result_url": "https://cdn.fal.ai/outputs/abc123.png",
  "latency_ms": 8432.1,
  "retry_count": 0,
  "error": null,
  "error_type": null,
  "cdn_expiry_note": "CDN links expire in approximately 24 hours."
}
```

**Response 200 — failed**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "failed",
  "mode": "image",
  "raw_prompt": "A red fox in snow",
  "enhanced_prompt": null,
  "result_url": null,
  "latency_ms": 30100.0,
  "retry_count": 2,
  "error": "Request timeout after 30s",
  "error_type": "TimeoutError",
  "cdn_expiry_note": "CDN links expire in approximately 24 hours."
}
```

> **Note:** CDN URLs from fal.ai and Replicate expire in approximately 24 hours. Save the image/video locally if you need to keep it.

**cURL**
```bash
curl "http://localhost:8000/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6/result"
```

---

## Schemas

### ImageAttributes

| Field | Type | Description |
|-------|------|-------------|
| `subject` | `string` | Who or what is the main focus |
| `action` | `string` | Pose, motion, or state |
| `location` | `string` | Setting, environment, time of day |
| `composition` | `string` | Camera angle, framing, depth of field, lighting |
| `style` | `string` | Aesthetic, art movement, colour palette, mood |

### VideoAttributes

| Field | Group | Description |
|-------|-------|-------------|
| `subject` | Overall | Who or what is the main focus |
| `action` | Overall | Motion, behavior, narrative arc |
| `scene` | Overall | Setting, environment, time of day, weather |
| `style` | Overall | Artistic filter / aesthetic |
| `temporal_elements` | Overall | Slow-mo, time-lapse, transitions, pacing |
| `camera_angles` | Camera | Shot viewpoints — wide, close-up, etc. |
| `camera_movements` | Camera | Dolly, pan, handheld, drone, etc. |
| `lens_effects` | Camera | Bokeh, anamorphic, rack focus, etc. |
| `dialogue` | Audio* | Spoken words or voice-over (visual mood guide only) |
| `sound_effects` | Audio* | Distinct sounds (visual energy guide only) |

*Luma Ray Flash 2 is visual-only. Audio fields guide the visual interpretation only.

### GenerateRequest

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `prompt` | `string` | `""` | Raw user prompt; max 2000 chars |
| `mode` | `"image"` \| `"video"` | `"image"` | — |
| `attributes` | `ImageAttributes?` | `null` | If set, structured image pipeline |
| `video_attributes` | `VideoAttributes?` | `null` | If set, structured video pipeline |
| `width` | `integer` | `1024` | Image only; 256–2048 |
| `height` | `integer` | `1024` | Image only; 256–2048 |
| `num_inference_steps` | `integer` | `28` | Image only; 1–50 |
| `aspect_ratio` | `string` | `"16:9"` | Video only; pattern `\d+:\d+` |
| `duration` | `integer` | `5` | Video only; 1–20 seconds |
