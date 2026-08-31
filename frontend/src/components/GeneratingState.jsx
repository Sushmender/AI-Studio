/**
 * GeneratingState.jsx — Visual feedback while a job is in progress.
 *
 * Day 3: functional placeholder (spinner + text).
 * Day 5: replaced with the full HUD choreographed animation.
 *
 * Props:
 *   mode          — "image" | "video"
 *   elapsedMs     — ms since job started
 *   estimatedWait — ms (estimated_wait_seconds * 1000) for video
 */

function formatElapsed(ms) {
  if (!ms || ms < 1000) return '0s';
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

export function GeneratingState({ mode, elapsedMs, estimatedWait }) {
  const isVideo = mode === 'video';
  const elapsed = formatElapsed(elapsedMs);

  return (
    <div className="generating-state" role="status" aria-live="polite" aria-label="Generating">
      {/* Spinner placeholder — will be replaced by HUD animation on Day 5 */}
      <div className="generating-state__spinner" aria-hidden="true">
        <div className="spinner" />
      </div>

      <div className="generating-state__info">
        <p className="generating-state__label">
          {isVideo ? 'Generating video' : 'Generating image'}
          <span className="generating-state__dots" aria-hidden="true" />
        </p>
        <p className="generating-state__elapsed">
          Elapsed: <strong>{elapsed}</strong>
          {isVideo && estimatedWait && (
            <span className="generating-state__estimate"> · Estimated: ~2–5 min</span>
          )}
        </p>
        {isVideo && (
          <p className="generating-state__note">
            Video generation takes 2–5 minutes. You can submit another job while this runs.
          </p>
        )}
      </div>
    </div>
  );
}
