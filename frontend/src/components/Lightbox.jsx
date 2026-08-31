/**
 * Lightbox.jsx — Full-screen overlay for viewing a gallery item.
 *
 * Features:
 *  - Images rendered with <img>
 *  - Videos embedded with <video controls autoPlay> (no new tab redirect)
 *  - Escape key closes the lightbox
 *  - Click outside content area closes
 *  - Download: <a href download> for images; videos are embedded (no new tab)
 *  - CDN expiry notice
 *
 * Props:
 *   item    — { result_url, mode, raw_prompt, enhanced_prompt }
 *   onClose — callback
 */
import { useEffect, useCallback, useRef } from 'react';

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

  const { result_url, mode, raw_prompt, enhanced_prompt } = item;
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
            {/* Download — only for images (cross-origin download works for same-origin or with CORS) */}
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

            <span className="lightbox__expiry-notice">
              ⚠ CDN links expire in ~24h
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
