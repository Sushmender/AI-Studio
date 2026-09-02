/**
 * ResultGallery.jsx — CSS grid of all completed image/video results.
 *
 * Features:
 *  - Images: <img loading="lazy">
 *  - Videos: <video controls preload="metadata"> (embedded, no new tab)
 *  - Hover overlay: prompt snippet + "View" button
 *  - Click card → opens Lightbox
 *  - Shimmer skeleton card while job is generating
 *  - Cosmic SVG empty state illustration
 *
 * Props:
 *   items        — array from useGallery()
 *   loading      — boolean (localStorage refetch in progress)
 *   onCardClick  — callback(item) to open lightbox from parent
 */
import { useState } from 'react';
import { Lightbox } from './Lightbox';

function formatElapsed(ms) {
  if (!ms || ms < 1000) return '0s';
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${String(rem).padStart(2, '0')}s`;
}

/** Cosmic telescope SVG illustration for the empty state */
function EmptyStateIllustration() {
  return (
    <svg
      className="result-gallery__empty-svg"
      viewBox="0 0 200 180"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      role="img"
      width="200"
      height="180"
    >
      {/* Deep space background stars */}
      <circle cx="20" cy="20" r="1.2" fill="#c9a227" opacity="0.6" />
      <circle cx="45" cy="12" r="0.8" fill="#e8c84a" opacity="0.8" />
      <circle cx="80" cy="8" r="1.5" fill="#c9a227" opacity="0.5" />
      <circle cx="130" cy="15" r="1" fill="#e8c84a" opacity="0.7" />
      <circle cx="168" cy="22" r="1.2" fill="#c9a227" opacity="0.6" />
      <circle cx="185" cy="10" r="0.7" fill="#e8c84a" opacity="0.9" />
      <circle cx="10" cy="60" r="0.9" fill="#c9a227" opacity="0.5" />
      <circle cx="190" cy="55" r="1.1" fill="#e8c84a" opacity="0.6" />
      <circle cx="155" cy="40" r="0.7" fill="#c9a227" opacity="0.8" />
      <circle cx="35" cy="45" r="1" fill="#e8c84a" opacity="0.5" />

      {/* Planet / orb */}
      <circle cx="155" cy="45" r="22" fill="url(#planetGrad)" opacity="0.85" />
      <ellipse cx="155" cy="45" rx="32" ry="7" stroke="#c9a227" strokeWidth="1.5" fill="none" opacity="0.5" />

      {/* Telescope body */}
      <rect x="60" y="100" width="80" height="18" rx="5" fill="url(#scopeGrad)" />
      {/* Telescope eyepiece */}
      <rect x="130" y="104" width="28" height="10" rx="3" fill="#c9a227" opacity="0.8" />
      {/* Telescope lens cap */}
      <ellipse cx="60" cy="109" rx="8" ry="9" fill="url(#lensGrad)" />
      {/* Tripod */}
      <line x1="100" y1="118" x2="80" y2="160" stroke="#c9a227" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
      <line x1="100" y1="118" x2="100" y2="162" stroke="#c9a227" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
      <line x1="100" y1="118" x2="120" y2="160" stroke="#c9a227" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
      {/* Tripod feet */}
      <line x1="72" y1="160" x2="88" y2="160" stroke="#c9a227" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
      <line x1="93" y1="162" x2="107" y2="162" stroke="#c9a227" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
      <line x1="112" y1="160" x2="128" y2="160" stroke="#c9a227" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />

      {/* Sight line from telescope to planet */}
      <line x1="60" y1="106" x2="140" y2="58" stroke="#c9a227" strokeWidth="0.8" strokeDasharray="4 3" opacity="0.35" />

      {/* Sparkles near planet */}
      <text x="175" y="30" fontSize="10" fill="#c9a227" opacity="0.8">✦</text>
      <text x="122" y="28" fontSize="7" fill="#e8c84a" opacity="0.6">✦</text>
      <text x="178" y="65" fontSize="6" fill="#c9a227" opacity="0.5">✦</text>

      {/* Gradient defs */}
      <defs>
        <radialGradient id="planetGrad" cx="40%" cy="35%" r="60%">
          <stop offset="0%" stopColor="#e8c84a" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#7a5a00" stopOpacity="0.8" />
        </radialGradient>
        <linearGradient id="scopeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#2a2000" />
          <stop offset="50%" stopColor="#4a3800" />
          <stop offset="100%" stopColor="#c9a227" stopOpacity="0.7" />
        </linearGradient>
        <radialGradient id="lensGrad" cx="40%" cy="35%" r="65%">
          <stop offset="0%" stopColor="#e8c84a" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#4a3800" stopOpacity="0.9" />
        </radialGradient>
      </defs>
    </svg>
  );
}

function GalleryLoadingCard({ job }) {
  const isVideo = job.mode === 'video';
  return (
    <article className="gallery-card gallery-card--loading" aria-label="Generating">
      <div className="gallery-card__media-wrap">
        {/* Shimmer skeleton fills the card */}
        <div className="gallery-skeleton">
          <div className="gallery-skeleton__shimmer" />
        </div>
        {/* Elapsed timer overlay */}
        <div className="gallery-loading-overlay">
          <span className="btn-spinner gallery-loading-spinner" aria-hidden="true" />
          <div className="gallery-loading-text">
            <span>{formatElapsed(job.elapsedMs)}</span>
            {isVideo && job.estimatedWait && (
              <span className="gallery-loading-est"> / {formatElapsed(job.estimatedWait)} est.</span>
            )}
          </div>
        </div>
      </div>
      <div className="gallery-card__footer">
        <span className="gallery-card__mode-badge">{isVideo ? '🎬' : '🖼'}</span>
      </div>
    </article>
  );
}

function GalleryCard({ item, onOpen }) {
  const { result_url, mode, raw_prompt, enhanced_prompt, job_id } = item;
  const isVideo = mode === 'video';
  const displayPrompt = enhanced_prompt || raw_prompt || '';
  const snippet = displayPrompt.slice(0, 80) + (displayPrompt.length > 80 ? '…' : '');

  return (
    <article
      className="gallery-card"
      aria-label={`${isVideo ? 'Video' : 'Image'}: ${displayPrompt.slice(0, 60)}`}
    >
      <div className="gallery-card__media-wrap">
        {isVideo ? (
          <video
            className="gallery-card__media"
            src={result_url}
            preload="metadata"
            muted
            playsInline
            loop
            onMouseEnter={(e) => e.target.play()}
            onMouseLeave={(e) => { e.target.pause(); e.target.currentTime = 0; }}
          />
        ) : (
          <img
            className="gallery-card__media"
            src={result_url}
            alt={displayPrompt.slice(0, 120)}
            loading="lazy"
          />
        )}

        {/* Hover overlay */}
        <div className="gallery-card__overlay">
          <p className="gallery-card__snippet">{snippet}</p>
          <button
            id={`gallery-view-${job_id}`}
            type="button"
            className="btn btn--primary btn--small"
            onClick={() => onOpen(item)}
            aria-label={`View ${isVideo ? 'video' : 'image'}`}
          >
            View
          </button>
        </div>
      </div>

      <div className="gallery-card__footer">
        <span className="gallery-card__mode-badge">{isVideo ? '🎬' : '🖼'}</span>
      </div>
    </article>
  );
}

export function ResultGallery({ items, loading, activeJob }) {
  const [lightboxItem, setLightboxItem] = useState(null);

  if (loading) {
    return (
      <section className="result-gallery" aria-label="Result Gallery">
        <h2 className="result-gallery__title">Gallery</h2>
        <p className="result-gallery__loading">Loading saved results…</p>
      </section>
    );
  }

  return (
    <section className="result-gallery" aria-label="Result Gallery">
      <h2 className="result-gallery__title">
        Gallery
        {items.length > 0 && (
          <span className="result-gallery__count">{items.length}</span>
        )}
      </h2>

      {items.length === 0 && !activeJob ? (
        <div className="result-gallery__empty">
          <EmptyStateIllustration />
          <p>No generations yet. Describe something above to start.</p>
        </div>
      ) : (
        <div className="gallery-grid">
          {activeJob && <GalleryLoadingCard job={activeJob} />}
          {items.map((item) => (
            <GalleryCard
              key={item.job_id}
              item={item}
              onOpen={setLightboxItem}
            />
          ))}
        </div>
      )}

      {lightboxItem && (
        <Lightbox item={lightboxItem} onClose={() => setLightboxItem(null)} />
      )}
    </section>
  );
}
