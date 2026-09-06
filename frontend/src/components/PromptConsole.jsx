/**
 * PromptConsole.jsx — Main input area. 3-state machine for BOTH image and video modes.
 *
 * States (image mode):
 *   idle       → textarea + "Analyse Description" button
 *   analysing  → AnalysingState cosmic animation (full-replace)
 *   ready      → <ImageAttributeEditor> with 5 editable fields
 *
 * States (video mode):
 *   idle       → textarea + "Analyse Description" button
 *   analysing  → AnalysingState cosmic animation (full-replace)
 *   ready      → <VideoAttributeEditor> with 10 fields across 3 groups
 *
 * Props:
 *   onSynthesizeImage({ attributes })       — called when Synthesize Prompt is clicked
 *   onSynthesizeVideo({ video_attributes }) — called when Synthesize Prompt is clicked
 *   onBackToEdit()                      — called when navigating back to Edit Attributes
 *   isSynthesizing                      — disables actions while synthesizing
 *   isGenerating                        — disables all actions while a job runs
 */
import { useState, useId, useRef } from 'react';
import { useImageAnalysis } from '../hooks/useImageAnalysis';
import { useVideoAnalysis } from '../hooks/useVideoAnalysis';
import { usePromptHistory } from '../hooks/usePromptHistory';
import { ImageAttributeEditor } from './ImageAttributeEditor';
import { VideoAttributeEditor } from './VideoAttributeEditor';
import { AnalysingState } from './AnalysingState';

const MAX_CHARS = 2000;

const MODE_OPTIONS = [
  { value: 'image', label: '🖼 Image' },
  { value: 'video', label: '🎬 Video' },
];

export function PromptConsole({
  onSynthesizeImage,
  onSynthesizeVideo,
  onBackToEdit,
  isSynthesizing,
  isGenerating,
  finalPrompt,
}) {
  const [mode, setMode] = useState('image');
  const [prompt, setPrompt] = useState('');
  const [validationError, setValidationError] = useState('');
  const [hasSynthesizedImage, setHasSynthesizedImage] = useState(false);
  const [hasSynthesizedVideo, setHasSynthesizedVideo] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const promptId = useId();
  const historyRef = useRef(null);

  const { history, addToHistory } = usePromptHistory();

  const {
    analyse,
    attributes,
    rawDescription,
    analysing,
    analysisError,
    reset,
    updateAttribute,
  } = useImageAnalysis();

  const {
    analyse: analyseVideo,
    attributes: videoAttributes,
    rawDescription: rawVideoDescription,
    analysing: analysingVideo,
    analysisError: videoAnalysisError,
    reset: resetVideo,
    updateAttribute: updateVideoAttribute,
  } = useVideoAnalysis();

  // Derived: which state the console is in
  const imageState = attributes ? 'ready' : analysing ? 'analysing' : 'idle';
  const videoState = videoAttributes ? 'ready' : analysingVideo ? 'analysing' : 'idle';

  const currentState = mode === 'image' ? imageState : videoState;
  const hasSynthesizedCurrent = mode === 'image' ? hasSynthesizedImage : hasSynthesizedVideo;

  // Proactive validation: button disabled until textarea has content
  const isPromptEmpty = !prompt.trim();
  const currentAnalysing = mode === 'image' ? analysing : analysingVideo;

  function handleKeyDown(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      if (mode === 'image' && imageState !== 'ready' && !analysing && !isGenerating && !isPromptEmpty) {
        handleAnalyseImage(e);
      } else if (mode === 'video' && videoState !== 'ready' && !analysingVideo && !isGenerating && !isPromptEmpty) {
        handleAnalyseVideo(e);
      }
    }
  }

  const charsLeft = MAX_CHARS - prompt.length;

  // ── Image: Analyse Description ────────────────────────────────────────────
  async function handleAnalyseImage(e) {
    e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed) return; // button is disabled when empty, but guard anyway
    setValidationError('');
    setHasSynthesizedImage(false);
    if (onBackToEdit) onBackToEdit();
    addToHistory(trimmed, 'image');
    await analyse(trimmed);
  }

  // ── Image: Synthesize from attributes ──────────────────────────────────────
  function handleSynthesizeImage() {
    setHasSynthesizedImage(true);
    onSynthesizeImage({ attributes, prompt });
  }

  // ── Image: Re-analyse (Step 1 back-nav) ──────────────────────────────────
  function handleReanalyseImage() {
    setHasSynthesizedImage(false);
    if (onBackToEdit) onBackToEdit();
    reset();
    setPrompt(rawDescription || prompt);
  }

  // ── Image: Back to Edit (Step 2 back-nav from Review) ──────────────────
  function handleBackToEditImage() {
    setHasSynthesizedImage(false);
    if (onBackToEdit) onBackToEdit();
  }

  function handleUpdateImageAttribute(key, val) {
    setHasSynthesizedImage(false);
    if (onBackToEdit) onBackToEdit();
    updateAttribute(key, val);
  }

  // ── Video: Analyse Description ────────────────────────────────────────────
  async function handleAnalyseVideo(e) {
    e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed) return;
    setValidationError('');
    setHasSynthesizedVideo(false);
    if (onBackToEdit) onBackToEdit();
    addToHistory(trimmed, 'video');
    await analyseVideo(trimmed);
  }

  // ── Video: Synthesize from attributes ──────────────────────────────────────
  function handleSynthesizeVideo() {
    setHasSynthesizedVideo(true);
    onSynthesizeVideo({ video_attributes: videoAttributes, prompt });
  }

  // ── Video: Re-analyse (Step 1 back-nav) ──────────────────────────────────
  function handleReanalyseVideo() {
    setHasSynthesizedVideo(false);
    if (onBackToEdit) onBackToEdit();
    resetVideo();
    setPrompt(rawVideoDescription || prompt);
  }

  // ── Video: Back to Edit (Step 2 back-nav from Review) ──────────────────
  function handleBackToEditVideo() {
    setHasSynthesizedVideo(false);
    if (onBackToEdit) onBackToEdit();
  }

  function handleUpdateVideoAttribute(key, val) {
    setHasSynthesizedVideo(false);
    if (onBackToEdit) onBackToEdit();
    updateVideoAttribute(key, val);
  }

  function handlePromptChange(e) {
    if (e.target.value.length <= MAX_CHARS) {
      setPrompt(e.target.value);
      if (validationError) setValidationError('');
    }
  }

  function handleModeSwitch(newMode) {
    setMode(newMode);
    setValidationError('');
  }

  function handleStartOver() {
    setHasSynthesizedImage(false);
    setHasSynthesizedVideo(false);
    if (onBackToEdit) onBackToEdit();
    reset();
    resetVideo();
    setPrompt('');
    setValidationError('');
    setHistoryOpen(false);
  }

  function handlePickHistory(p) {
    setPrompt(p);
    setHistoryOpen(false);
    setValidationError('');
  }

  const currentHistory = history[mode] ?? [];

  // ── Step click handlers ───────────────────────────────────────────────────
  // Step 1 clickable when in Edit or Review steps (currentState === 'ready')
  const canClickStep1 = currentState === 'ready' && !isGenerating && !isSynthesizing && !currentAnalysing;
  // Step 2 clickable when in Review step (hasSynthesizedCurrent && currentState === 'ready')
  const canClickStep2 = hasSynthesizedCurrent && currentState === 'ready' && !isGenerating && !isSynthesizing && !currentAnalysing;

  function handleStep1Click() {
    if (!canClickStep1) return;
    if (mode === 'image') handleReanalyseImage();
    else handleReanalyseVideo();
  }

  function handleStep2Click() {
    if (!canClickStep2) return;
    if (mode === 'image') handleBackToEditImage();
    else handleBackToEditVideo();
  }

  // Determine stepper step states
  const step1State = currentState === 'idle' || currentState === 'analysing'
    ? 'active'
    : 'completed';
  const step2State = currentState === 'ready' && !hasSynthesizedCurrent
    ? 'active'
    : currentState === 'ready'
    ? 'completed'
    : '';
  const step3State = hasSynthesizedCurrent && !isGenerating
    ? 'active'
    : (isGenerating ? 'completed' : '');
  const step4State = isGenerating ? 'active' : '';

  return (
    <section className="prompt-console" aria-label="Prompt Console">
      <header className="prompt-console__header">
        {/* Title row — PROMPT CONSOLE label + Start Over on the same centerline */}
        <div className="prompt-console__header-row">
          <h2 className="prompt-console__title">Prompt Console</h2>
          {(prompt.length > 0 || imageState === 'ready' || videoState === 'ready') && (
            <button
              type="button"
              className="btn--ghost-danger"
              onClick={handleStartOver}
              disabled={isGenerating || isSynthesizing || analysing || analysingVideo}
              aria-label="Start over"
            >
              ✕ Start over
            </button>
          )}
        </div>

        {/* Mode toggle — clearly grouped under the title */}
        <div className="prompt-console__mode-row">
          <div className="mode-toggle" role="group" aria-label="Generation mode">
            {MODE_OPTIONS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                id={`mode-toggle-${value}`}
                className={`mode-toggle__btn${mode === value ? ' mode-toggle__btn--active' : ''}`}
                onClick={() => handleModeSwitch(value)}
                disabled={isGenerating || isSynthesizing || analysing || analysingVideo}
                aria-pressed={mode === value}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Pipeline Stepper */}
      <div className="pipeline-stepper" aria-label="Progress">
        {/* Step 1: Analyse — clickable when in Edit/Generate */}
        {canClickStep1 ? (
          <button
            type="button"
            className={`stepper-step stepper-step--${step1State} stepper-step--clickable`}
            onClick={handleStep1Click}
            title="Back to Analyse"
            aria-label="Go back to Analyse step"
          >
            1. Analyse
          </button>
        ) : (
          <span className={`stepper-step${step1State ? ` stepper-step--${step1State}` : ''}`}>
            1. Analyse
          </span>
        )}

        <span className="stepper-divider" />

        {/* Step 2: Edit Attributes — clickable when in Review and attributes exist */}
        {canClickStep2 ? (
          <button
            type="button"
            className={`stepper-step stepper-step--${step2State} stepper-step--clickable`}
            onClick={handleStep2Click}
            title="Back to Edit Attributes"
            aria-label="Go back to Edit Attributes step"
          >
            2. Edit Attributes
          </button>
        ) : (
          <span className={`stepper-step${step2State ? ` stepper-step--${step2State}` : ''}`}>
            2. Edit Attributes
          </span>
        )}

        <span className="stepper-divider" />

        <span className={`stepper-step${step3State ? ` stepper-step--${step3State}` : ''}`}>
          3. Review Prompt
        </span>

        <span className="stepper-divider" />

        <span className={`stepper-step${step4State ? ` stepper-step--${step4State}` : ''}`}>
          4. Generate
        </span>
      </div>

      {/* ── IMAGE MODE ─────────────────────────────────────────────────── */}
      {mode === 'image' && (
        <>
          {/* State: analysing — show cosmic animation */}
          {imageState === 'analysing' && <AnalysingState mode="image" />}

          {/* State: idle — show textarea */}
          {imageState === 'idle' && (
            <form onSubmit={handleAnalyseImage} noValidate>
              <div className="prompt-console__field">
                <label htmlFor={promptId} className="sr-only">
                  Describe the image you want to generate
                </label>
                <div className="prompt-field-wrap">
                  <textarea
                    id={promptId}
                    className={`prompt-textarea${validationError ? ' prompt-textarea--error' : ''}`}
                    value={prompt}
                    onChange={handlePromptChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe the image you want to generate… Be as brief or detailed as you like. The AI will fill in the missing pieces."
                    rows={5}
                    disabled={isGenerating || isSynthesizing}
                    aria-describedby={validationError ? 'prompt-error' : 'prompt-hint'}
                  />
                  {currentHistory.length > 0 && (
                    <div className="prompt-history" ref={historyRef}>
                      <button
                        type="button"
                        className="prompt-history__toggle"
                        onClick={() => setHistoryOpen((o) => !o)}
                        aria-expanded={historyOpen}
                        aria-label="Show prompt history"
                        title="Recent prompts"
                        disabled={isGenerating || isSynthesizing}
                      >
                        ▾
                      </button>
                      {historyOpen && (
                        <ul className="prompt-history__dropdown" role="listbox" aria-label="Recent prompts">
                          {currentHistory.map((p, i) => (
                            <li key={i} role="option">
                              <button
                                type="button"
                                className="prompt-history__item"
                                onClick={() => handlePickHistory(p)}
                              >
                                {p.slice(0, 80)}{p.length > 80 ? '…' : ''}
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
                <div className="prompt-console__meta">
                  {validationError ? (
                    <span id="prompt-error" className="prompt-console__error" role="alert">
                      {validationError}
                    </span>
                  ) : (
                    <span id="prompt-hint" className="prompt-console__chars">
                      {charsLeft} characters remaining
                    </span>
                  )}
                </div>
              </div>

              {/* Analysis error */}
              {analysisError && (
                <p className="prompt-console__analyse-error" role="alert">
                  ⚠ {analysisError.message}
                </p>
              )}

              <button
                id="analyse-btn"
                type="submit"
                className="btn btn--primary btn--large"
                disabled={isGenerating || isSynthesizing || isPromptEmpty}
                aria-busy={false}
                title={isPromptEmpty ? 'Enter a description to continue' : undefined}
              >
                🔍 Analyse description
              </button>

              {/* Hint below button */}
              {!analysisError && (
                <p className="prompt-console__hint">
                  AI will extract Subject, Action, Location, Composition, and Style — filling in anything you didn't mention.
                </p>
              )}
            </form>
          )}

          {/* State: ready — show attribute editor */}
          {imageState === 'ready' && (
            <ImageAttributeEditor
              attributes={attributes}
              rawDescription={rawDescription}
              onUpdate={handleUpdateImageAttribute}
              onSynthesize={handleSynthesizeImage}
              onReanalyse={handleReanalyseImage}
              isGenerating={isGenerating || isSynthesizing}
              finalPrompt={finalPrompt}
            />
          )}
        </>
      )}

      {/* ── VIDEO MODE ─────────────────────────────────────────────────── */}
      {mode === 'video' && (
        <>
          {/* State: analysing — show cosmic animation */}
          {videoState === 'analysing' && <AnalysingState mode="video" />}

          {/* State: idle — show textarea */}
          {videoState === 'idle' && (
            <form onSubmit={handleAnalyseVideo} noValidate>
              <div className="prompt-console__field">
                <label htmlFor={promptId} className="sr-only">
                  Describe the video scene you want to generate
                </label>
                <div className="prompt-field-wrap">
                  <textarea
                    id={promptId}
                    className={`prompt-textarea${validationError ? ' prompt-textarea--error' : ''}`}
                    value={prompt}
                    onChange={handlePromptChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe the video scene you want to generate… The AI will extract Overall, Camera, and Audio elements."
                    rows={5}
                    disabled={isGenerating || isSynthesizing}
                    aria-describedby={validationError ? 'prompt-error' : 'prompt-hint'}
                  />
                  {currentHistory.length > 0 && (
                    <div className="prompt-history" ref={historyRef}>
                      <button
                        type="button"
                        className="prompt-history__toggle"
                        onClick={() => setHistoryOpen((o) => !o)}
                        aria-expanded={historyOpen}
                        aria-label="Show prompt history"
                        title="Recent prompts"
                        disabled={isGenerating || isSynthesizing}
                      >
                        ▾
                      </button>
                      {historyOpen && (
                        <ul className="prompt-history__dropdown" role="listbox" aria-label="Recent prompts">
                          {currentHistory.map((p, i) => (
                            <li key={i} role="option">
                              <button
                                type="button"
                                className="prompt-history__item"
                                onClick={() => handlePickHistory(p)}
                              >
                                {p.slice(0, 80)}{p.length > 80 ? '…' : ''}
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
                <div className="prompt-console__meta">
                  {validationError ? (
                    <span id="prompt-error" className="prompt-console__error" role="alert">
                      {validationError}
                    </span>
                  ) : (
                    <span id="prompt-hint" className="prompt-console__chars">
                      {charsLeft} characters remaining
                    </span>
                  )}
                </div>
              </div>

              {/* Analysis error */}
              {videoAnalysisError && (
                <p className="prompt-console__analyse-error" role="alert">
                  ⚠ {videoAnalysisError.message}
                </p>
              )}

              <button
                id="analyse-video-btn"
                type="submit"
                className="btn btn--primary btn--large"
                disabled={isGenerating || isSynthesizing || isPromptEmpty}
                aria-busy={false}
                title={isPromptEmpty ? 'Enter a description to continue' : undefined}
              >
                🔍 Analyse description
              </button>

              {/* Hint below button */}
              {!videoAnalysisError && (
                <p className="prompt-console__hint">
                  AI will extract 10 video attributes — filling in anything you didn't mention.
                </p>
              )}
            </form>
          )}

          {/* State: ready — show video attribute editor */}
          {videoState === 'ready' && (
            <VideoAttributeEditor
              attributes={videoAttributes}
              rawDescription={rawVideoDescription}
              onUpdate={handleUpdateVideoAttribute}
              onSynthesize={handleSynthesizeVideo}
              onReanalyse={handleReanalyseVideo}
              isGenerating={isGenerating || isSynthesizing}
              finalPrompt={finalPrompt}
            />
          )}
        </>
      )}
    </section>
  );
}
