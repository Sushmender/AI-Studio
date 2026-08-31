/**
 * ResultGallery.jsx — CSS grid of all completed image/video results.
 *
 * Features:
 *  - Images: <img loading="lazy">
 *  - Videos: <video controls preload="metadata"> (embedded, no new tab)
 *  - Hover overlay: prompt snippet + "View" button
 *  - Click card → opens Lightbox
 *  - Empty state when no items
 *
 * Props:
 *   items        — array from useGallery()
 *   loading      — boolean (localStorage refetch in progress)
 *   onCardClick  — callback(item) to open lightbox from parent
 */
import { useState } from 'react';
import { Lightbox } from './Lightbox';

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

export function ResultGallery({ items, loading }) {
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

      {items.length === 0 ? (
        <div className="result-gallery__empty">
          <span className="result-gallery__empty-icon" aria-hidden="true">🎨</span>
          <p>No results yet — generate your first image or video</p>
        </div>
      ) : (
        <div className="gallery-grid">
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
