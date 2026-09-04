/**
 * VideoAttributeEditor.jsx — Shows 10 structured video attributes across 3 collapsible groups.
 *
 * Layout:
 *   ┌──────────────────────────────────────────────────────────┐
 *   │ ▸ Your description (collapsible, read-only)              │
 *   ├──────────────────────────────────────────────────────────┤
 *   │ ▾ OVERALL [open]                             (5 fields)  │
 *   │   🎭 Subject    [inline editable]                        │
 *   │   ⚡ Action     [inline editable]                        │
 *   │   🌍 Scene      [inline editable]                        │
 *   │   🎨 Style      [inline editable]                        │
 *   │   ⏱ Temporal   [inline editable]                        │
 *   ├──────────────────────────────────────────────────────────┤
 *   │ ▾ CAMERA [open]                              (3 fields)  │
 *   │   📐 Angles     [inline editable]                        │
 *   │   🎬 Movements  [inline editable]                        │
 *   │   🔭 Lens       [inline editable]                        │
 *   ├──────────────────────────────────────────────────────────┤
 *   │ ▸ AUDIO 🔇 [collapsed by default]            (2 fields)  │
 *   │   → collapsed summary: "Not specified · Not specified"   │
 *   ├──────────────────────────────────────────────────────────┤
 *   │  [↩ Re-analyse]                  [🎬 Generate Video]    │
 *   └──────────────────────────────────────────────────────────┘
 *
 * Props:
 *   attributes       — the 10 VideoAttributes fields
 *   rawDescription   — original user text (for collapsible)
 *   onUpdate(k,v)    — called when user edits a field inline
 *   onGenerate()     — called when user clicks Generate Video
 *   onReanalyse()    — called when user clicks Re-analyse
 *   isGenerating     — boolean (disables Generate button)
 */
import { useState, useRef, useEffect, useCallback } from 'react';

// ── Attribute taxonomy with 3 groups ────────────────────────────────────────

const ATTRIBUTE_GROUPS = [
  {
    id: 'overall',
    label: 'Overall',
    dot: '#4fffb0',
    defaultOpen: true,
    fields: [
      { key: 'subject',           label: 'Subject',           desc: 'Who or what is the main focus',            icon: '🎭' },
      { key: 'action',            label: 'Action',            desc: 'What is happening — motion, narrative',     icon: '⚡' },
      { key: 'scene',             label: 'Scene',             desc: 'When and where — setting, time, weather',  icon: '🌍' },
      { key: 'style',             label: 'Style',             desc: 'Artistic filter / aesthetic',               icon: '🎨' },
      { key: 'temporal_elements', label: 'Temporal',          desc: 'Slow-mo, time-lapse, pacing, transitions', icon: '⏱' },
    ],
  },
  {
    id: 'camera',
    label: 'Camera',
    dot: '#60a5fa',
    defaultOpen: true,
    fields: [
      { key: 'camera_angles',    label: 'Angles',    desc: 'Shot viewpoints — wide, close-up, bird\'s eye', icon: '📐' },
      { key: 'camera_movements', label: 'Movements', desc: 'Dolly, pan, handheld, steadicam, drone',        icon: '🎬' },
      { key: 'lens_effects',     label: 'Lens',      desc: 'Bokeh, anamorphic, rack focus, flare',          icon: '🔭' },
    ],
  },
  {
    id: 'audio',
    label: 'Audio',
    dot: '#94a3b8',
    audioOnly: true, // shows 🔇 badge
    defaultOpen: false, // collapsed by default — visual-only model, less critical
    fields: [
      { key: 'dialogue',      label: 'Dialogue', desc: 'Spoken words or voice-over', icon: '💬' },
      { key: 'sound_effects', label: 'Sound FX', desc: 'Distinct sounds in the scene', icon: '🔊' },
    ],
  },
];

// ── Inline-editable attribute row ────────────────────────────────────────────

function VideoAttributeRow({ meta, value, onUpdate, muted = false }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const textareaRef = useRef(null);

  useEffect(() => { setDraft(value); }, [value]);

  function startEdit() {
    setDraft(value);
    setEditing(true);
  }

  function commitEdit() {
    setEditing(false);
    onUpdate(meta.key, draft.trim() || value);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commitEdit(); }
    if (e.key === 'Escape') { setEditing(false); setDraft(value); }
  }

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus();
      const len = textareaRef.current.value.length;
      textareaRef.current.setSelectionRange(len, len);
    }
  }, [editing]);

  return (
    <div className={`attr-row${editing ? ' attr-row--editing' : ''}${muted ? ' attr-row--muted' : ''}`}>
      <div className="attr-row__label-col">
        <span className="attr-row__icon" aria-hidden="true">{meta.icon}</span>
        <div>
          <span className="attr-row__label">{meta.label}</span>
          {editing && <span className="attr-row__editing-badge">✏ Editing</span>}
          <span className="attr-row__desc">{meta.desc}</span>
        </div>
      </div>

      <div className="attr-row__value-col">
        {editing ? (
          <div className="attr-row__editor">
            <textarea
              ref={textareaRef}
              className="attr-row__textarea"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={4}
              aria-label={`Edit ${meta.label}`}
            />
            <div className="attr-row__editor-actions">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => { setEditing(false); setDraft(value); }}
                style={{ padding: '4px 12px', fontSize: '12px' }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={commitEdit}
                style={{ padding: '4px 12px', fontSize: '12px' }}
              >
                Save
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            className="attr-row__display"
            onClick={startEdit}
            aria-label={`Edit ${meta.label}: ${value}`}
            title="Click to edit"
          >
            <span className="attr-row__text">
              {value || <em className="attr-row__empty">Not specified</em>}
            </span>
            <span className="attr-row__edit-icon" aria-hidden="true">✏</span>
          </button>
        )}
      </div>
    </div>
  );
}

// ── Collapsible original description ─────────────────────────────────────────

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
      {open && <p className="original-desc__text">{text}</p>}
    </div>
  );
}

// ── Collapsible accordion group ───────────────────────────────────────────────

function AttributeGroup({ group, attributes, onUpdate, defaultOpen }) {
  const [isOpen, setIsOpen] = useState(defaultOpen ?? group.defaultOpen ?? true);

  // Summary of field values for collapsed view
  const collapsedSummary = group.fields
    .map((f) => attributes[f.key] || 'Not specified')
    .map((v) => (v.length > 30 ? v.slice(0, 30) + '…' : v))
    .join(' · ');

  return (
    <div className={`vattr-group${group.audioOnly ? ' vattr-group--audio' : ''}`}>
      {/* Accordion header */}
      <button
        type="button"
        className="vattr-group__header vattr-group__toggle"
        onClick={() => setIsOpen((o) => !o)}
        aria-expanded={isOpen}
        aria-controls={`vattr-group-${group.id}`}
      >
        <span className="vattr-group__chevron" aria-hidden="true">
          {isOpen ? '▾' : '▸'}
        </span>
        <span className="vattr-group__dot" style={{ background: group.dot }} aria-hidden="true" />
        <span className="vattr-group__label">{group.label}</span>
        {group.audioOnly && (
          <span
            className="vattr-group__audio-badge"
            title="This model is visual-only. Audio fields guide the visual mood but are not rendered as sound."
          >
            🔇 Visual-only
          </span>
        )}
        <span className="vattr-group__field-count">
          {group.fields.length} {group.fields.length === 1 ? 'field' : 'fields'}
        </span>
      </button>

      {/* Collapsed summary */}
      {!isOpen && (
        <div className="vattr-group__summary" id={`vattr-group-${group.id}`}>
          {collapsedSummary}
        </div>
      )}

      {/* Expanded fields */}
      {isOpen && (
        <div className="attr-editor__rows" id={`vattr-group-${group.id}`}>
          {group.fields.map((meta) => (
            <VideoAttributeRow
              key={meta.key}
              meta={meta}
              value={attributes[meta.key] ?? ''}
              onUpdate={onUpdate}
              muted={group.audioOnly}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function VideoAttributeEditor({
  attributes,
  rawDescription,
  onUpdate,
  onGenerate,
  onReanalyse,
  isGenerating,
}) {
  const [copied, setCopied] = useState(false);

  const handleGenerate = useCallback(() => {
    if (!isGenerating) onGenerate();
  }, [isGenerating, onGenerate]);

  function handleCopy() {
    const lines = ATTRIBUTE_GROUPS.flatMap((g) => [
      `--- ${g.label.toUpperCase()} ---`,
      ...g.fields.map((f) => `${f.label.toUpperCase()}: ${attributes[f.key] ?? ''}`),
    ]);
    navigator.clipboard.writeText(lines.join('\n')).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  }

  return (
    <div className="attr-editor" aria-label="Video Attributes Editor">
      {/* Collapsible original description */}
      {rawDescription && <OriginalDescription text={rawDescription} />}

      {/* 3 accordion groups */}
      <div className="vattr-groups">
        {ATTRIBUTE_GROUPS.map((group) => (
          <AttributeGroup
            key={group.id}
            group={group}
            attributes={attributes}
            onUpdate={onUpdate}
          />
        ))}
      </div>

      {/* Audio disclaimer */}
      <p className="vattr-audio-notice">
        🔇 <strong>Audio fields</strong> are used by Groq to guide the visual mood and atmosphere of the scene. The current model (<code>luma/ray-flash-2-720p</code>) does not render audio or dialogue.
      </p>

      {/* Action bar */}
      <div className="attr-editor__actions">
        {/* Utility row: Re-analyse (weighted) + Copy (compact) */}
        <div className="attr-editor__util-row">
          <button
            id="video-reanalyse-btn"
            type="button"
            className="btn btn--secondary attr-editor__reanalyse-btn"
            onClick={onReanalyse}
            disabled={isGenerating}
          >
            ↩ Re-analyse
          </button>

          <button
            id="copy-video-attrs-btn"
            type="button"
            className={`btn btn--secondary attr-editor__copy-util-btn attr-editor__copy-btn${copied ? ' attr-editor__copy-btn--copied' : ''}`}
            onClick={handleCopy}
            aria-label="Copy attributes to clipboard"
            title="Copy attributes to clipboard"
          >
            {copied ? '✓ Copied!' : '📋 Copy'}
          </button>
        </div>

        {/* Primary CTA — visually separated by the increased gap */}
        <button
          id="generate-video-structured-btn"
          type="button"
          className="btn btn--primary btn--large attr-editor__generate-btn"
          onClick={handleGenerate}
          disabled={isGenerating}
          aria-busy={isGenerating}
        >
          {isGenerating ? '⏳ Generating…' : (
            <>
              🎬 Generate video <span className="attr-editor__estimate">~2-5 min</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
