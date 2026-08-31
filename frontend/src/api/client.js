/**
 * client.js — API fetch wrappers for AI-Studio backend.
 *
 * All functions throw an ApiError with { provider, errorType, message }
 * that maps directly to the copy shown in ErrorState.jsx.
 *
 * Base URL: /api  (proxied to http://127.0.0.1:8000 in dev via vite.config.js)
 */

const BASE = '/api';

// ── Error type → user-facing copy ────────────────────────────────────────────

const ERROR_MESSAGES = {
  groq_timeout:
    'Prompt enhancement timed out — generating with your original prompt',
  fal_server_error:
    'Image generation failed — fal.ai returned a server error after 2 attempts',
  replicate_timeout:
    'Video generation failed — Replicate returned a timeout (generation exceeded 5 minutes)',
  rate_limit:
    'Too many requests — please wait 60 seconds before generating again',
  network_offline:
    'Cannot reach AI-Studio server — check your connection',
  generic_failed:
    'Generation failed — please try again',
};

/**
 * Derive a clean errorType + message from a job's error_type field
 * (as returned by GET /jobs/{id}/status).
 */
export function mapJobErrorType(rawErrorType, mode) {
  if (!rawErrorType) return { errorType: 'generic_failed', message: ERROR_MESSAGES.generic_failed };

  const t = rawErrorType.toLowerCase();

  if (t.includes('timeout') && (t.includes('groq') || t.includes('enhance'))) {
    return { errorType: 'groq_timeout', message: ERROR_MESSAGES.groq_timeout };
  }
  if (t.includes('timeout') && mode === 'video') {
    return { errorType: 'replicate_timeout', message: ERROR_MESSAGES.replicate_timeout };
  }
  if (t.includes('fal') || (t.includes('server') && mode === 'image')) {
    return { errorType: 'fal_server_error', message: ERROR_MESSAGES.fal_server_error };
  }

  return { errorType: 'generic_failed', message: ERROR_MESSAGES.generic_failed };
}

// ── ApiError class ────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor({ provider = '', errorType = 'generic_failed', message, status }) {
    super(message);
    this.name = 'ApiError';
    this.provider = provider;
    this.errorType = errorType;
    this.userMessage = message;
    this.status = status;
  }
}

// ── Internal helpers ──────────────────────────────────────────────────────────

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
  } catch (_networkErr) {
    throw new ApiError({
      errorType: 'network_offline',
      message: ERROR_MESSAGES.network_offline,
      status: 0,
    });
  }

  if (response.status === 429) {
    throw new ApiError({
      errorType: 'rate_limit',
      message: ERROR_MESSAGES.rate_limit,
      status: 429,
    });
  }

  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = body?.detail || body?.message || '';
    } catch (_) {}
    throw new ApiError({
      errorType: 'generic_failed',
      message: detail || ERROR_MESSAGES.generic_failed,
      status: response.status,
    });
  }

  return response.json();
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Submit an image generation job.
 * If attributes are provided, the backend runs Groq Call 2 to synthesize the final prompt.
 * @returns {Promise<{job_id, status, mode, raw_prompt, estimated_wait_seconds}>}
 */
export async function generateImage(prompt = '', opts = {}) {
  return request('/generate/image', {
    method: 'POST',
    body: JSON.stringify({
      prompt,
      mode: 'image',
      // Structured attributes (optional — triggers Groq Call 2 on backend)
      attributes: opts.attributes ?? null,
      width: opts.width ?? 1024,
      height: opts.height ?? 1024,
      num_inference_steps: opts.num_inference_steps ?? 28,
    }),
  });
}

/**
 * Groq Call 1 (Video): Analyse a raw video description and extract 10 visual attributes
 * across 3 groups (Overall, Camera, Audio).
 * @param {string} description
 * @returns {Promise<{ attributes: VideoAttributes, raw_description: string }>}
 */
export async function analyseVideoDescription(description) {
  return request('/analyse/video', {
    method: 'POST',
    body: JSON.stringify({ description }),
  });
}

/**
 * Submit a video generation job.
 * If video_attributes are provided, the backend runs Groq Call 2 to synthesize the prompt.
 * @returns {Promise<{job_id, status, mode, raw_prompt, estimated_wait_seconds}>}
 */
export async function generateVideo(prompt = '', opts = {}) {
  return request('/generate/video', {
    method: 'POST',
    body: JSON.stringify({
      prompt,
      mode: 'video',
      // Structured video attributes (optional — triggers Groq Call 2 on backend)
      video_attributes: opts.video_attributes ?? null,
      aspect_ratio: opts.aspect_ratio ?? '16:9',
      duration: opts.duration ?? 5,
    }),
  });
}

/**
 * Groq Call 1: Analyse a raw image description and extract 5 visual attributes.
 * @param {string} description — raw user description
 * @returns {Promise<{ attributes: ImageAttributes, raw_description: string }>}
 */
export async function analyseImageDescription(description) {
  return request('/analyse/image', {
    method: 'POST',
    body: JSON.stringify({ description }),
  });
}

/**
 * Poll job status.
 * @returns {Promise<JobStatusResponse>}
 */
export async function getJobStatus(jobId) {
  return request(`/jobs/${jobId}/status`);
}

/**
 * Get the final result of a completed job.
 * @returns {Promise<JobResultResponse>}
 */
export async function getJobResult(jobId) {
  // 202 (still in progress) is returned as an error by the backend,
  // but we handle it gracefully by returning null.
  let response;
  try {
    response = await fetch(`${BASE}/jobs/${jobId}/result`, {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (_) {
    throw new ApiError({
      errorType: 'network_offline',
      message: ERROR_MESSAGES.network_offline,
      status: 0,
    });
  }

  if (response.status === 202) return null; // still in progress
  if (response.status === 429) {
    throw new ApiError({ errorType: 'rate_limit', message: ERROR_MESSAGES.rate_limit, status: 429 });
  }
  if (!response.ok) return null;

  return response.json();
}

/**
 * Health probe — returns per-service reachability.
 */
export async function getHealth() {
  return request('/health');
}
