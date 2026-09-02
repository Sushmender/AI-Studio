/**
 * PromptConsole.jsx — Main input area. 3-state machine for BOTH image and video modes.
 *
 * States (image mode):
 *   idle       → textarea + "Analyse Description" button
 *   analysing  → textarea (disabled) + spinner
 *   ready      → <ImageAttributeEditor> with 5 editable fields
 *
 * States (video mode):
 *   idle       → textarea + "Analyse Description" button
 *   analysing  → textarea (disabled) + spinner
 *   ready      → <VideoAttributeEditor> with 10 fields across 3 groups
 *
 * Props:
 *   onSubmitImage({ attributes })       — called when Generate Image is clicked
 *   onSubmitVideo({ video_attributes }) — called when Generate Video is clicked
 *   isGenerating                        — disables all actions while a job runs
 */
import { useState, useId, useRef } from 'react';
import { useImageAnalysis } from '../hooks/useImageAnalysis';
import { useVideoAnalysis } from '../hooks/useVideoAnalysis';
import { usePromptHistory } from '../hooks/usePromptHistory';
import { ImageAttributeEditor } from './ImageAttributeEditor';
import { VideoAttributeEditor } from './VideoAttributeEditor';

const MAX_CHARS = 2000;

const MODE_OPTIONS = [
  { value: 'image', label: '🖼 Image' },
  { value: 'video', label: '🎬 Video' },
];

export function PromptConsole({
  onSubmitImage,
  onSubmitVideo,
  isGenerating,
}) {
  const [mode, setMode] = useState('image');
  const [prompt, setPrompt] = useState('');
  const [validationError, setValidationError] = useState('');
  const [hasGeneratedImage, setHasGeneratedImage] = useState(false);
  const [hasGeneratedVideo, setHasGeneratedVideo] = useState(false);
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
  const hasGeneratedCurrent = mode === 'image' ? hasGeneratedImage : hasGeneratedVideo;

  function handleKeyDown(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      if (mode === 'image' && imageState !== 'ready' && !analysing && !isGenerating) {
        handleAnalyseImage(e);
      } else if (mode === 'video' && videoState !== 'ready' && !analysingVideo && !isGenerating) {
        handleAnalyseVideo(e);
      }
    }
  }

  const charsLeft = MAX_CHARS - prompt.length;

  // ── Image: Analyse Description ────────────────────────────────────────────
  async function handleAnalyseImage(e) {
    e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed) {
      setValidationError('Prompt cannot be empty');
      return;
    }
    setValidationError('');
    setHasGeneratedImage(false);
    addToHistory(trimmed, 'image');
    await analyse(trimmed);
  }

  // ── Image: Generate from attributes ──────────────────────────────────────
  function handleGenerateImage() {
    setHasGeneratedImage(true);
    onSubmitImage({ attributes });
  }

  // ── Image: Re-analyse ─────────────────────────────────────────────────────
  function handleReanalyseImage() {
    setHasGeneratedImage(false);
    reset();
    // Restore the textarea to what was there before (rawDescription)
    setPrompt(rawDescription || prompt);
  }
  
  function handleUpdateImageAttribute(key, val) {
    setHasGeneratedImage(false);
    updateAttribute(key, val);
  }

  // ── Video: Analyse Description ────────────────────────────────────────────
  async function handleAnalyseVideo(e) {
    e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed) {
      setValidationError('Prompt cannot be empty');
      return;
    }
    setValidationError('');
    setHasGeneratedVideo(false);
    addToHistory(trimmed, 'video');
    await analyseVideo(trimmed);
  }

  // ── Video: Generate from attributes ──────────────────────────────────────
  function handleGenerateVideo() {
    setHasGeneratedVideo(true);
    onSubmitVideo({ video_attributes: videoAttributes });
  }

  // ── Video: Re-analyse ─────────────────────────────────────────────────────
  function handleReanalyseVideo() {
    setHasGeneratedVideo(false);
    resetVideo();
    setPrompt(rawVideoDescription || prompt);
  }

  function handleUpdateVideoAttribute(key, val) {
    setHasGeneratedVideo(false);
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
    setHasGeneratedImage(false);
    setHasGeneratedVideo(false);
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

  return (
    <section className="prompt-console" aria-label="Prompt Console">
      <header className="prompt-console__header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h2 className="prompt-console__title">Prompt Console</h2>
          {(prompt.length > 0 || imageState === 'ready' || videoState === 'ready') && (
            <button 
              type="button" 
              className="btn btn--secondary" 
              style={{ padding: '2px 8px', fontSize: '10px', height: '20px', minHeight: '20px' }}
              onClick={handleStartOver}
              disabled={isGenerating || analysing || analysingVideo}
              aria-label="Start over"
            >
              ✕ Start over
            </button>
          )}
        </div>

        {/* Mode toggle */}
        <div className="mode-toggle" role="group" aria-label="Generation mode">
          {MODE_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              id={`mode-toggle-${value}`}
              className={`mode-toggle__btn${mode === value ? ' mode-toggle__btn--active' : ''}`}
              onClick={() => handleModeSwitch(value)}
              disabled={isGenerating || analysing || analysingVideo}
              aria-pressed={mode === value}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      {/* Pipeline Stepper */}
      <div className="pipeline-stepper" aria-label="Progress">
        <div className={`stepper-step ${currentState === 'idle' || currentState === 'analysing' ? 'stepper-step--active' : 'stepper-step--completed'}`}>1. Analyse</div>
        <span className="stepper-divider" />
        <div className={`stepper-step ${currentState === 'ready' && !isGenerating && !hasGeneratedCurrent ? 'stepper-step--active' : (currentState === 'ready' ? 'stepper-step--completed' : '')}`}>2. Edit</div>
        <span className="stepper-divider" />
        <div className={`stepper-step ${isGenerating || hasGeneratedCurrent ? 'stepper-step--active' : ''}`}>3. Generate</div>
      </div>

      {/* ── IMAGE MODE ─────────────────────────────────────────────────── */}
      {mode === 'image' && (
        <>
          {/* State: idle or analysing — show textarea */}
          {imageState !== 'ready' && (
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
                    placeholder="Describe the image you want to generate\u2026 Be as brief or detailed as you like. The AI will fill in the missing pieces."
                    rows={5}
                    disabled={analysing || isGenerating}
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
                        disabled={analysing || isGenerating}
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
                                {p.slice(0, 80)}{p.length > 80 ? '\u2026' : ''}
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
                disabled={analysing || isGenerating}
                aria-busy={analysing}
              >
                {analysing ? (
                  <>
                    <span className="btn-spinner" aria-hidden="true" />
                    Analysing description…
                  </>
                ) : (
                  '🔍 Analyse description'
                )}
              </button>

              {/* Hint below button */}
              {imageState === 'idle' && !analysisError && (
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
              onGenerate={handleGenerateImage}
              onReanalyse={handleReanalyseImage}
              isGenerating={isGenerating}
            />
          )}
        </>
      )}

      {/* ── VIDEO MODE ─────────────────────────────────────────────────── */}
      {mode === 'video' && (
        <>
          {videoState !== 'ready' && (
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
                    placeholder="Describe the video scene you want to generate\u2026 The AI will extract Overall, Camera, and Audio elements."
                    rows={5}
                    disabled={analysingVideo || isGenerating}
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
                        disabled={analysingVideo || isGenerating}
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
                                {p.slice(0, 80)}{p.length > 80 ? '\u2026' : ''}
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
                disabled={analysingVideo || isGenerating}
                aria-busy={analysingVideo}
              >
                {analysingVideo ? (
                  <>
                    <span className="btn-spinner" aria-hidden="true" />
                    Analysing description…
                  </>
                ) : (
                  '🔍 Analyse description'
                )}
              </button>

              {/* Hint below button */}
              {videoState === 'idle' && !videoAnalysisError && (
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
              onGenerate={handleGenerateVideo}
              onReanalyse={handleReanalyseVideo}
              isGenerating={isGenerating}
            />
          )}
        </>
      )}
    </section>
  );
}
