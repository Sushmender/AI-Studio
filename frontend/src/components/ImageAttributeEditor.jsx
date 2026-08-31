/**
 * ImageAttributeEditor.jsx — Shows 5 structured image attributes for user review/editing.
 *
 * Layout:
 *   ┌──────────────────────────────────────────────────┐
 *   │ ▸ Your description (collapsible, read-only)      │
 *   ├──────────────────────────────────────────────────┤
 *   │ SUBJECT        [inline editable text]            │
 *   │ ACTION         [inline editable text]            │
 *   │ LOCATION       [inline editable text]            │
 *   │ COMPOSITION    [inline editable text]            │
 *   │ STYLE          [inline editable text]            │
 *   ├──────────────────────────────────────────────────┤
 *   │    [Re-analyse]           [Generate Image]       │
 *   └──────────────────────────────────────────────────┘
 *
 * Props:
 *   attributes       — { subject, action, location, composition, style }
 *   rawDescription   — the original user text (for the collapsible)
 *   onUpdate(k,v)    — called when user edits a field
 *   onGenerate()     — called when user clicks Generate Image
 *   onReanalyse()    — called when user clicks Re-analyse (resets to textarea)
 *   isGenerating     — boolean (disables Generate button)
 */
import { useState, useRef, useEffect, useCallback } from 'react';

const ATTRIBUTE_META = [
  {
    key: 'subject',
    label: 'Subject',
    description: 'Who or what is the main focus',
    icon: '👤',
  },
  {
    key: 'action',
    label: 'Action',
    description: 'What is happening — pose, motion, or state',
    icon: '⚡',
  },
  {
    key: 'location',
    label: 'Location',
    description: 'The setting, environment, and time of day',
    icon: '🌍',
  },
  {
    key: 'composition',
    label: 'Composition',
    description: 'Camera angle, framing, depth of field, lighting',
    icon: '📷',
  },
  {
    key: 'style',
    label: 'Style',
    description: 'Overall aesthetic, art movement, color palette, mood',
    icon: '🎨',
  },
];

// ── Inline-editable single attribute row ────────────────────────────────────

function AttributeRow({ meta, value, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const textareaRef = useRef(null);

  // Keep draft in sync if parent updates (e.g., on re-analyse)
  useEffect(() => {
    setDraft(value);
  }, [value]);

  function startEdit() {
    setDraft(value);
    setEditing(true);
  }

  function commitEdit() {
    setEditing(false);
    onUpdate(meta.key, draft.trim() || value);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      commitEdit();
    }
    if (e.key === 'Escape') {
      setEditing(false);
      setDraft(value); // discard
    }
  }

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus();
      // Place cursor at end
      const len = textareaRef.current.value.length;
      textareaRef.current.setSelectionRange(len, len);
    }
  }, [editing]);

  return (
    <div className={`attr-row${editing ? ' attr-row--editing' : ''}`}>
      <div className="attr-row__label-col">
        <span className="attr-row__icon" aria-hidden="true">{meta.icon}</span>
        <div>
          <span className="attr-row__label">{meta.label}</span>
          <span className="attr-row__desc">{meta.description}</span>
        </div>
      </div>

      <div className="attr-row__value-col">
        {editing ? (
          <textarea
            ref={textareaRef}
            className="attr-row__textarea"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commitEdit}
            onKeyDown={handleKeyDown}
            rows={2}
            aria-label={`Edit ${meta.label}`}
          />
        ) : (
          <button
            type="button"
            className="attr-row__display"
            onClick={startEdit}
            aria-label={`Edit ${meta.label}: ${value}`}
            title="Click to edit"
          >
            <span className="attr-row__text">{value || <em className="attr-row__empty">Not specified</em>}</span>
            <span className="attr-row__edit-icon" aria-hidden="true">✏</span>
          </button>
        )}
      </div>
    </div>
  );
}

// ── Collapsible original description ────────────────────────────────────────

function OriginalDescription({ text }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="original-desc">
      <button
        type="button"
        className="original-desc__toggle"
        onClick={() => setOpen((p) => !p)}
        aria-expanded={open}
      >
        <span className="original-desc__arrow">{open ? '▾' : '▸'}</span>
        <span>Your description</span>
      </button>
      {open && (
        <p className="original-desc__text">{text}</p>
      )}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export function ImageAttributeEditor({
  attributes,
  rawDescription,
  onUpdate,
  onGenerate,
  onReanalyse,
  isGenerating,
}) {
  const handleGenerate = useCallback(() => {
    if (!isGenerating) onGenerate();
  }, [isGenerating, onGenerate]);

  return (
    <div className="attr-editor" aria-label="Image Attributes Editor">
      {/* Collapsible original description */}
      {rawDescription && <OriginalDescription text={rawDescription} />}

      {/* 5 attribute rows */}
      <div className="attr-editor__rows">
        {ATTRIBUTE_META.map((meta) => (
          <AttributeRow
            key={meta.key}
            meta={meta}
            value={attributes[meta.key] ?? ''}
            onUpdate={onUpdate}
          />
        ))}
      </div>

      {/* Action bar */}
      <div className="attr-editor__actions">
        <button
          id="reanalyse-btn"
          type="button"
          className="btn btn--secondary"
          onClick={onReanalyse}
          disabled={isGenerating}
        >
          ↩ Re-analyse
        </button>

        <button
          id="generate-image-btn"
          type="button"
          className="btn btn--primary btn--large attr-editor__generate-btn"
          onClick={handleGenerate}
          disabled={isGenerating}
          aria-busy={isGenerating}
        >
          {isGenerating ? '⏳ Generating…' : '✦ Generate Image'}
        </button>
      </div>
    </div>
  );
}
