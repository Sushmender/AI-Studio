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
import { useState, useId } from 'react';
import { useImageAnalysis } from '../hooks/useImageAnalysis';
import { useVideoAnalysis } from '../hooks/useVideoAnalysis';
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
  const promptId = useId();

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
    await analyse(trimmed);
  }

  // ── Image: Generate from attributes ──────────────────────────────────────
  function handleGenerateImage() {
    onSubmitImage({ attributes });
  }

  // ── Image: Re-analyse ─────────────────────────────────────────────────────
  function handleReanalyseImage() {
    reset();
    // Restore the textarea to what was there before (rawDescription)
    setPrompt(rawDescription || prompt);
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
    await analyseVideo(trimmed);
  }

  // ── Video: Generate from attributes ──────────────────────────────────────
  function handleGenerateVideo() {
    onSubmitVideo({ video_attributes: videoAttributes });
  }

  // ── Video: Re-analyse ─────────────────────────────────────────────────────
  function handleReanalyseVideo() {
    resetVideo();
    setPrompt(rawVideoDescription || prompt);
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
    reset(); // clear any pending image analysis
    resetVideo(); // clear any pending video analysis
  }

  function handleStartOver() {
    reset();
    resetVideo();
    setPrompt('');
    setValidationError('');
  }

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
              aria-label="Start fresh"
            >
              ✕ Clear
            </button>
          )}
        </div>

        {/* Mode toggle — hidden once attributes are shown */}
        {imageState !== 'ready' && videoState !== 'ready' && (
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
        )}
      </header>

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
                <textarea
                  id={promptId}
                  className={`prompt-textarea${validationError ? ' prompt-textarea--error' : ''}`}
                  value={prompt}
                  onChange={handlePromptChange}
                  placeholder="Describe the image you want to generate… Be as brief or detailed as you like. The AI will fill in the missing pieces."
                  rows={5}
                  disabled={analysing || isGenerating}
                  aria-describedby={validationError ? 'prompt-error' : 'prompt-hint'}
                />
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
                  '🔍 Analyse Description'
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
              onUpdate={updateAttribute}
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
                <textarea
                  id={promptId}
                  className={`prompt-textarea${validationError ? ' prompt-textarea--error' : ''}`}
                  value={prompt}
                  onChange={handlePromptChange}
                  placeholder="Describe the video scene you want to generate… The AI will extract Overall, Camera, and Audio elements."
                  rows={5}
                  disabled={analysingVideo || isGenerating}
                  aria-describedby={validationError ? 'prompt-error' : 'prompt-hint'}
                />
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
                  '🔍 Analyse Description'
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
              onUpdate={updateVideoAttribute}
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
