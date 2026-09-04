/**
 * AnalysingState.jsx — Compact cosmic animation while the AI analyses a description.
 *
 * Renders the same orbit animation used in GeneratingState, but smaller and
 * with an "ANALYSING PROMPT" label. Fully replaces the textarea + button view
 * while analysing is in progress.
 *
 * Props:
 *   mode — "image" | "video"
 */

export function AnalysingState({ mode }) {
  const label = mode === 'video' ? '// ANALYSING VIDEO DESCRIPTION' : '// ANALYSING PROMPT';

  return (
    <div className="analysing-state" role="status" aria-live="polite" aria-label="Analysing">

      {/* Compact cosmic animation */}
      <div className="cosmo-anim cosmo-anim--sm" aria-hidden="true">

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
      </div>

      {/* Status text */}
      <div className="analysing-state__info">
        <p className="analysing-state__label">{label}</p>
        <p className="analysing-state__sub">
          Extracting structured attributes from your description…
        </p>
      </div>
    </div>
  );
}
