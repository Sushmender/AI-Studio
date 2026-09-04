/**
 * Lightbox.jsx — Full-screen overlay for viewing a gallery item.
 *
 * Features:
 *  - Images rendered with <img>
 *  - Videos embedded with <video controls autoPlay> (no new tab redirect)
 *  - Escape key closes the lightbox
 *  - Click outside content area closes
 *  - Download: <a href download> for images; videos are embedded (no new tab)
 *  - CDN expiry live countdown from item.created_at (falls back to static ~24h notice)
 *
 * Props:
 *   item    — { result_url, mode, raw_prompt, enhanced_prompt, created_at }
 *   onClose — callback
 */
import { useEffect, useCallback, useRef, useState } from 'react';

// CDN links live for approximately 24 hours from creation
const CDN_TTL_MS = 24 * 60 * 60 * 1000;

function formatCountdown(msLeft) {
  if (msLeft <= 0) return 'Expired';
  const totalSec = Math.floor(msLeft / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m ${String(s).padStart(2, '0')}s`;
  if (m > 0) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
}

function CdnCountdown({ createdAt }) {
  const [msLeft, setMsLeft] = useState(() => {
    if (!createdAt) return null;
    return Math.max(0, createdAt + CDN_TTL_MS - Date.now());
  });

  useEffect(() => {
    if (!createdAt) return;

    const tick = () => {
      const remaining = Math.max(0, createdAt + CDN_TTL_MS - Date.now());
      setMsLeft(remaining);
    };

    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [createdAt]);

  // No created_at — show static notice
  if (msLeft === null) {
    return (
      <span className="cdn-countdown cdn-countdown--static">
        ⚠ CDN link expires in ~24h
      </span>
    );
  }

  const isExpired = msLeft <= 0;
  const isUrgent = msLeft > 0 && msLeft <= 60 * 60 * 1000;       // < 1 hour
  const isWarning = msLeft > 0 && msLeft <= 6 * 60 * 60 * 1000;  // < 6 hours

  const modifier = isExpired
    ? 'cdn-countdown--expired'
    : isUrgent
    ? 'cdn-countdown--urgent'
    : isWarning
    ? 'cdn-countdown--warning'
    : 'cdn-countdown--ok';

  return (
    <span className={`cdn-countdown ${modifier}`} aria-live="polite" aria-atomic="true">
      {isExpired ? (
        <>⛔ Link expired — re-generate to download</>
      ) : isUrgent ? (
        <>🔴 Download now! Expires in {formatCountdown(msLeft)}</>
      ) : isWarning ? (
        <>⚠ Link expires in {formatCountdown(msLeft)}</>
      ) : (
        <>⏱ Link expires in {formatCountdown(msLeft)}</>
      )}
    </span>
  );
}

export function Lightbox({ item, onClose }) {
  const contentRef = useRef(null);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [handleKeyDown]);

  function handleBackdropClick(e) {
    if (contentRef.current && !contentRef.current.contains(e.target)) {
      onClose();
    }
  }

  if (!item) return null;

  const { result_url, mode, raw_prompt, enhanced_prompt, created_at } = item;
  const displayPrompt = enhanced_prompt || raw_prompt || '';
  const isVideo = mode === 'video';

  return (
    <div
      className="lightbox"
      role="dialog"
      aria-modal="true"
      aria-label="Media viewer"
      onClick={handleBackdropClick}
    >
      <div className="lightbox__content" ref={contentRef}>
        {/* Close button */}
        <button
          id="lightbox-close-btn"
          type="button"
          className="lightbox__close"
          onClick={onClose}
          aria-label="Close lightbox"
        >
          ✕
        </button>

        {/* Media */}
        <div className="lightbox__media">
          {isVideo ? (
            <video
              key={result_url}
              className="lightbox__video"
              src={result_url}
              controls
              autoPlay
              playsInline
              loop
            >
              Your browser does not support the video element.
            </video>
          ) : (
            <img
              className="lightbox__image"
              src={result_url}
              alt={displayPrompt.slice(0, 120)}
              loading="lazy"
            />
          )}
        </div>

        {/* CDN expiry banner — shown prominently above footer when warning/urgent */}
        <CdnCountdownBanner createdAt={created_at} />

        {/* Info footer */}
        <div className="lightbox__footer">
          <div className="lightbox__prompt-info">
            <span className="lightbox__mode-badge">{isVideo ? '🎬 Video' : '🖼 Image'}</span>
            {displayPrompt && (
              <p className="lightbox__prompt-text" title={displayPrompt}>
                {displayPrompt.slice(0, 200)}{displayPrompt.length > 200 ? '…' : ''}
              </p>
            )}
          </div>

          <div className="lightbox__actions">
            {/* Download — only for images */}
            {!isVideo && (
              <a
                id="lightbox-download-btn"
                href={result_url}
                download
                target="_blank"
                rel="noreferrer"
                className="btn btn--secondary"
              >
                ↓ Download Image
              </a>
            )}

            {/* Inline expiry pill (ok / static state) */}
            <CdnCountdown createdAt={created_at} />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Banner shown above the footer when link is warning or urgent state.
 * Invisible in the "ok" state (< 6h used).
 */
function CdnCountdownBanner({ createdAt }) {
  const [msLeft, setMsLeft] = useState(() => {
    if (!createdAt) return null;
    return Math.max(0, createdAt + CDN_TTL_MS - Date.now());
  });

  useEffect(() => {
    if (!createdAt) return;
    const id = setInterval(() => {
      setMsLeft(Math.max(0, createdAt + CDN_TTL_MS - Date.now()));
    }, 1000);
    return () => clearInterval(id);
  }, [createdAt]);

  if (msLeft === null) return null;

  const isExpired = msLeft <= 0;
  const isUrgent = msLeft > 0 && msLeft <= 60 * 60 * 1000;
  const isWarning = msLeft > 0 && msLeft <= 6 * 60 * 60 * 1000;

  if (!isExpired && !isUrgent && !isWarning) return null;

  return (
    <div
      className={`lightbox__cdn-banner ${isExpired ? 'lightbox__cdn-banner--expired' : isUrgent ? 'lightbox__cdn-banner--urgent' : 'lightbox__cdn-banner--warning'}`}
      role="alert"
    >
      {isExpired
        ? '⛔ This CDN link has expired. Re-generate to get a fresh download.'
        : isUrgent
        ? `🔴 Download now — this link expires in ${formatCountdown(msLeft)}!`
        : `⚠ This link expires in ${formatCountdown(msLeft)} — download before it's gone.`}
    </div>
  );
}
