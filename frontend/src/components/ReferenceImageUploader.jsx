/**
 * ReferenceImageUploader.jsx — Drag & drop, paste, or file-picker for a reference image.
 *
 * Used in the Video Generation workflow (optional, but highly recommended).
 *
 * Supports:
 *   - Drag & drop an image file onto the drop zone
 *   - Paste an image from the clipboard (Ctrl+V / Cmd+V)
 *   - Click to open a file picker
 *
 * Validation (client-side):
 *   - File type: JPEG, PNG, WebP
 *   - File size: ≤ 5 MB
 *
 * Props:
 *   referenceImage  — File | null
 *   previewUrl      — string | null  (object URL for preview, managed by parent)
 *   onImageChange   — (file: File | null) => void
 *   disabled        — boolean
 *   error           — string | null  (external error to display)
 */
import { useState, useRef, useCallback, useEffect } from 'react';

const MAX_SIZE = 5 * 1024 * 1024; // 5 MB
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const ALLOWED_EXT = ['.jpg', '.jpeg', '.png', '.webp'];

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ReferenceImageUploader({
  referenceImage,
  previewUrl,
  onImageChange,
  disabled = false,
  error: externalError = null,
}) {
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState(null);
  const inputRef = useRef(null);
  const dropRef = useRef(null);

  const displayError = externalError || localError;

  // ── Validation helper ────────────────────────────────────────────────────
  const validateFile = useCallback((file) => {
    if (!file) return 'No file selected.';
    if (!ALLOWED_TYPES.has(file.type)) {
      return `Unsupported format: ${file.type || 'unknown'}. Use JPG, PNG, or WebP.`;
    }
    if (file.size > MAX_SIZE) {
      return `File too large: ${formatSize(file.size)}. Maximum: 5 MB.`;
    }
    if (file.size === 0) return 'File is empty.';
    return null;
  }, []);

  const handleFile = useCallback(
    (file) => {
      setLocalError(null);
      const err = validateFile(file);
      if (err) {
        setLocalError(err);
        return;
      }
      onImageChange(file);
    },
    [validateFile, onImageChange],
  );

  // ── Drag & drop handlers ─────────────────────────────────────────────────
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set false if actually leaving the drop zone
    if (dropRef.current && !dropRef.current.contains(e.relatedTarget)) {
      setDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(false);
      if (disabled) return;
      const file = e.dataTransfer?.files?.[0];
      if (file) handleFile(file);
    },
    [disabled, handleFile],
  );

  // ── Paste handler ────────────────────────────────────────────────────────
  useEffect(() => {
    const zone = dropRef.current;
    if (!zone) return;

    function handlePaste(e) {
      if (disabled) return;
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.kind === 'file' && item.type.startsWith('image/')) {
          e.preventDefault();
          const file = item.getAsFile();
          if (file) handleFile(file);
          return;
        }
      }
    }

    zone.addEventListener('paste', handlePaste);
    return () => zone.removeEventListener('paste', handlePaste);
  }, [disabled, handleFile]);

  // ── Click to pick ────────────────────────────────────────────────────────
  function handleClick() {
    if (!disabled && inputRef.current) {
      inputRef.current.click();
    }
  }

  function handleInputChange(e) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset input so re-selecting the same file triggers onChange
    e.target.value = '';
  }

  // ── Remove handler ───────────────────────────────────────────────────────
  function handleRemove(e) {
    e.stopPropagation();
    setLocalError(null);
    onImageChange(null);
  }

  // ── Render ───────────────────────────────────────────────────────────────

  // Preview state
  if (referenceImage && previewUrl) {
    return (
      <div className="ref-image-uploader">
        <div className="ref-image-preview" aria-label="Reference image preview">
          <div className="ref-image-preview__thumb-wrap">
            <img
              className="ref-image-preview__thumb"
              src={previewUrl}
              alt={`Reference: ${referenceImage.name}`}
            />
            {!disabled && (
              <button
                type="button"
                className="ref-image-preview__remove"
                onClick={handleRemove}
                aria-label="Remove reference image"
                title="Remove image"
              >
                ✕
              </button>
            )}
          </div>
          <div className="ref-image-preview__info">
            <span className="ref-image-preview__name" title={referenceImage.name}>
              📎 {referenceImage.name}
            </span>
            <span className="ref-image-preview__size">
              {formatSize(referenceImage.size)}
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Drop zone state
  return (
    <div className="ref-image-uploader">
      <div
        ref={dropRef}
        className={`ref-image-dropzone${dragOver ? ' ref-image-dropzone--drag-over' : ''}${disabled ? ' ref-image-dropzone--disabled' : ''}${displayError ? ' ref-image-dropzone--error' : ''}`}
        onClick={handleClick}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        tabIndex={disabled ? -1 : 0}
        role="button"
        aria-label="Upload a reference image — drag and drop, paste, or click to browse"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
          }
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_EXT.join(',')}
          onChange={handleInputChange}
          className="ref-image-dropzone__input"
          tabIndex={-1}
          aria-hidden="true"
        />

        <div className="ref-image-dropzone__content">
          <span className="ref-image-dropzone__icon" aria-hidden="true">
            {dragOver ? '📥' : '🖼'}
          </span>
          <span className="ref-image-dropzone__label">
            {dragOver ? 'Drop image here' : 'Reference Image'}
            <span className="ref-image-dropzone__badge">Recommended</span>
          </span>
          <span className="ref-image-dropzone__hint">
            Drag & drop, paste, or click to upload
          </span>
          <span className="ref-image-dropzone__formats">
            JPG, PNG, WebP · Max 5 MB
          </span>
        </div>
      </div>

      {displayError && (
        <p className="ref-image-error" role="alert">
          ⚠ {displayError}
        </p>
      )}
    </div>
  );
}
