/**
 * GeneratingState.jsx — Cosmic observatory animation while a job is in progress.
 *
 * Day 5: Full choreographed cosmic animation:
 *   - Two orbital rings with pulsing amber glow
 *   - Two orbiting bodies (moon + star) on different tracks and speeds
 *   - Pulsing golden core
 *   - 6 floating ambient particles
 *   - Live elapsed timer in monospace HUD style
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
  return `${m}m ${String(rem).padStart(2, '0')}s`;
}

export function GeneratingState({ mode, elapsedMs, estimatedWait }) {
  const isVideo = mode === 'video';
  const modeLabel = isVideo ? '// RENDERING VIDEO' : '// GENERATING IMAGE';

  return (
    <div className="generating-state" role="status" aria-live="polite" aria-label="Generating">

      {/* ── Cosmic animation ───────────────────────────────────────────── */}
      <div className="cosmo-anim" aria-hidden="true">

        {/* Static orbital rings */}
        <div className="cosmo-anim__ring cosmo-anim__ring--outer" />
        <div className="cosmo-anim__ring cosmo-anim__ring--inner" />

        {/* Orbiting body 1 — outer track, moon */}
        <div className="cosmo-anim__orbit cosmo-anim__orbit--1">
          <span className="cosmo-anim__body cosmo-anim__body--moon" />
        </div>

        {/* Orbiting body 2 — inner track, star, counter-clockwise */}
        <div className="cosmo-anim__orbit cosmo-anim__orbit--2">
          <span className="cosmo-anim__body cosmo-anim__body--star" />
        </div>

        {/* Pulsing core */}
        <div className="cosmo-anim__core" />

        {/* Ambient particles */}
        <span className="cosmo-anim__particle" />
        <span className="cosmo-anim__particle" />
        <span className="cosmo-anim__particle" />
        <span className="cosmo-anim__particle" />
        <span className="cosmo-anim__particle" />
        <span className="cosmo-anim__particle" />
      </div>

      {/* ── Status info ────────────────────────────────────────────────── */}
      <div className="generating-state__info">
        <p className="generating-state__label">{modeLabel}</p>

        <div className="generating-state__elapsed">
          <span className="generating-state__elapsed-label">Elapsed</span>
          <span className="generating-state__elapsed-value">
            {formatElapsed(elapsedMs)}
          </span>
        </div>

        {isVideo && (
          <p className="generating-state__note">
            Est. 2–5 min · You can submit another job while this runs
          </p>
        )}
      </div>
    </div>
  );
}
