# AI-Studio

> **AI-powered image and video generation** — a full-stack POC using fal.ai, Replicate, and Groq.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6-purple)](https://vitejs.dev)

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Setup Guide](#setup-guide)
- [Environment Variables](#environment-variables)
- [Run Commands](#run-commands)
- [API Quick Reference](#api-quick-reference)
- [Testing](#testing)
- [Project Structure](#project-structure)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser  ─  React + Vite (localhost:5173)                      │
│                                                                 │
│  ┌──────────────┐  ┌──────────────────────┐  ┌──────────────┐  │
│  │PromptConsole │→ │  ImageAttributeEditor│→ │ResultGallery │  │
│  │              │  │  VideoAttributeEditor│  │  + Lightbox  │  │
│  └──────────────┘  └──────────────────────┘  └──────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────────┐
│  FastAPI Backend  (localhost:8000)                              │
│                                                                 │
│  POST /analyse/image|video  ──► groq_client.py                 │
│           │                         │ Groq Call 1 (analyse)    │
│           ▼                         ▼                          │
│  POST /generate/image|video ──► groq_client.py                 │
│           │                         │ Groq Call 2 (synthesize) │
│           ▼                         ▼                          │
│       job_store.py        fal_client.py / replicate_client.py  │
│    (asyncio.Lock dict)         │             │                  │
│           ▲                    ▼             ▼                  │
│  GET /jobs/{id}/status     fal.ai        Replicate             │
│  GET /jobs/{id}/result   (FLUX Dev)  (Luma Ray Flash 2)        │
└─────────────────────────────────────────────────────────────────┘
```

### 3-Stage Structured Pipeline

```
User types description
        │
        ▼
POST /analyse/image|video
        │
        ▼
   Groq Call 1 ─── Analyse ──► 5 image attrs / 10 video attrs
        │
        ▼
   User edits attributes in the UI
        │
        ▼
POST /generate/image|video  (with attributes in body)
        │
        ▼
   Groq Call 2 ─── Synthesize ──► Optimised provider prompt
        │
        ▼
   fal.ai / Replicate ──────────► CDN URL returned to frontend
```

### Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Job store | In-memory `dict` + `asyncio.Lock` | POC scope; no persistence needed |
| Prompt enhancement | Groq (free tier) | Zero inference cost for text analysis |
| Image generation | fal.ai / FLUX Dev | High quality, fast (~5–15 s) |
| Video generation | Replicate / Luma Ray Flash 2 720p | Best quality at 720p, reasonable latency |
| Rate limiting | IP-based sliding window | Simple, stateless, no Redis needed |
| Mock flag | `MOCK_GENERATION_APIS=True` | Separate image/video mocking from Groq |

---

## Setup Guide

### Prerequisites

- Python 3.12+
- Node.js 18+ and npm
- API keys for: [fal.ai](https://fal.ai), [Replicate](https://replicate.com), [Groq](https://console.groq.com)

### 1 — Clone & create virtual environment

```powershell
git clone <repo-url>
cd AI_Studio
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2 — Configure environment variables

Copy the example and fill in your keys:

```powershell
copy .env.example .env
# Then edit .env with your API keys (see Environment Variables table below)
```

### 3 — Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

---

## Environment Variables

All variables are loaded from `.env` at the project root. **Never commit real API keys.**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FAL_KEY` | ✅ | — | fal.ai API key |
| `REPLICATE_API_TOKEN` | ✅ | — | Replicate API token |
| `GROQ_API_KEY` | ✅ | — | Groq API key |
| `FAL_IMAGE_MODEL` | — | `fal-ai/flux/dev` | fal.ai model ID |
| `REPLICATE_VIDEO_MODEL` | — | `luma/ray-flash-2-720p` | Replicate model ID |
| `GROQ_MODEL` | — | `qwen/qwen3.8-27b` | Groq model ID |
| `MOCK_GENERATION_APIS` | — | `True` | Skip real fal.ai + Replicate calls (Groq always real) |
| `FAL_TIMEOUT` | — | `30` | fal.ai request timeout (seconds) |
| `REPLICATE_TIMEOUT` | — | `360` | Replicate request timeout (seconds) |
| `GROQ_TIMEOUT` | — | `10` | Groq request timeout (seconds) |
| `MAX_RETRY_ATTEMPTS` | — | `2` | Max retry attempts for transient errors |
| `RETRY_BACKOFF_BASE` | — | `1.5` | Exponential backoff base (seconds) |
| `RATE_LIMIT_REQUESTS` | — | `10` | Max requests per IP per window |
| `RATE_LIMIT_WINDOW_SECONDS` | — | `60` | Sliding window size (seconds) |
| `CORS_ORIGINS` | — | `["http://localhost:5173","http://localhost:3000"]` | Allowed CORS origins |

> **Tip:** Set `MOCK_GENERATION_APIS=False` only when you want to run real fal.ai and Replicate requests (incurs cost/quota usage).

---

## Run Commands

### Backend

```powershell
# Activate venv first
.venv\Scripts\activate

# Development (auto-reload on file changes)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Frontend

```powershell
cd frontend
npm run dev         # Dev server at http://localhost:5173
npm run build       # Production bundle → frontend/dist/
npm run preview     # Preview production build locally
```

### Both Together (separate terminals)

```powershell
# Terminal 1 — Backend
.venv\Scripts\activate && uvicorn backend.main:app --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## API Quick Reference

Full API documentation is available at **http://localhost:8000/docs** (Swagger UI) when the backend is running.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service info |
| `GET` | `/health` | Provider reachability probes (cached 30 s) |
| `POST` | `/analyse/image` | Groq Call 1: extract 5 image attributes |
| `POST` | `/analyse/video` | Groq Call 1: extract 10 video attributes |
| `POST` | `/generate/image` | Submit image generation job → `job_id` |
| `POST` | `/generate/video` | Submit video generation job → `job_id` |
| `GET` | `/jobs` | List all jobs (paginated, newest first) |
| `GET` | `/jobs/{id}/status` | Poll job status |
| `GET` | `/jobs/{id}/result` | Fetch final result / CDN URL |

See [docs/API.md](docs/API.md) for full request/response schemas and curl examples.

---

## Testing

### Unit Tests (no server required)

```powershell
.venv\Scripts\activate

# Run all unit tests
.venv\Scripts\python -m pytest tests/test_unit.py -v --asyncio-mode=auto

# With coverage report
.venv\Scripts\python -m pytest tests/test_unit.py -v --asyncio-mode=auto ^
    --cov=backend --cov-report=term-missing --cov-report=html:htmlcov
```

Coverage report opens at `htmlcov/index.html`.

### Integration Tests (requires running backend)

```powershell
# Start backend first (in another terminal)
uvicorn backend.main:app --reload

# Run integration tests
.venv\Scripts\python -m pytest tests/test_integration.py -v --asyncio-mode=auto

# Against a custom URL
$env:AI_STUDIO_TEST_URL="http://staging.example.com"
.venv\Scripts\python -m pytest tests/test_integration.py -v --asyncio-mode=auto
```

### Test Coverage

| Module | Coverage |
|--------|----------|
| `backend/services/job_store.py` | ~95% |
| `backend/services/rate_limiter.py` | ~90% |
| `backend/utils/retry.py` | ~95% |
| `backend/clients/` | mocked in unit tests |
| `backend/routes/` | covered by integration tests |

---

## Project Structure

```
AI_Studio/
├── .env                          # API keys and config (never commit)
├── .env.example                  # Template (safe to commit)
├── requirements.txt              # Backend Python dependencies
├── task.md                       # Day-by-day progress tracker
│
├── backend/
│   ├── main.py                   # FastAPI app, CORS, lifespan, TTL cleanup
│   ├── config.py                 # pydantic-settings Settings class
│   ├── models/
│   │   └── schemas.py            # All Pydantic request/response models
│   ├── clients/
│   │   ├── fal_client.py         # fal.ai image generation
│   │   ├── replicate_client.py   # Replicate video generation
│   │   └── llm_client.py         # LLM (Groq/OpenRouter): analyse + synthesize
│   ├── routes/
│   │   ├── generate.py           # POST /generate/image|video
│   │   ├── jobs.py               # GET /jobs, /jobs/{id}/status|result
│   │   ├── health.py             # GET /health (cached 30 s)
│   │   └── analyse.py            # POST /analyse/image|video
│   ├── services/
│   │   ├── job_store.py          # In-memory job store (asyncio.Lock)
│   │   ├── prompt_service.py     # Legacy Groq enhance() orchestrator
│   │   └── rate_limiter.py       # IP sliding window rate limiter
│   └── utils/
│       ├── logger.py             # structlog JSON logger
│       ├── retry.py              # async_retry decorator
│       └── tasks.py              # log_task_exception done-callback
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx               # HUD header, starfield, routing
│       ├── ErrorBoundary.jsx     # React error boundary
│       ├── index.css             # Cosmic Observatory design system
│       ├── api/client.js         # Typed fetch wrappers for all endpoints
│       ├── hooks/
│       │   └── useJobPolling.js  # Polling hook (2 s image / 5 s video)
│       └── components/
│           ├── PromptConsole.jsx
│           ├── ImageAttributeEditor.jsx
│           ├── VideoAttributeEditor.jsx
│           ├── AnalysingState.jsx    # Cosmic analysis animation
│           ├── GeneratingState.jsx   # Cosmic orbit animation
│           ├── ResultGallery.jsx
│           ├── Lightbox.jsx
│           ├── JobStatusStrip.jsx
│           └── ErrorState.jsx
│
├── tests/
│   ├── conftest.py               # Shared fixtures, Windows event loop fix
│   ├── test_unit.py              # 20 unit tests (JobStore, RateLimiter, Retry)
│   └── test_integration.py       # 11 integration tests (full HTTP flow)
│
└── docs/
    ├── API.md                    # Full API reference with curl examples
    └── ARCHITECTURE.md           # System diagrams and component guide
```
