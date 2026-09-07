/**
 * App.jsx — Orchestrates all state for AI-Studio frontend.
 *
 * Day 5: HUD header + cosmic starfield background added.
 *
 * State:
 *   jobs          — array of job records (active + recent), newest first
 *   activeJobId   — the job currently being polled
 *   activeMode    — mode of the active job
 *   lastSubmit    — { prompt, mode } of the last submission (for retry)
 *
 * Flow:
 *   1. User submits → generateImage/generateVideo → returns job_id
 *   2. App stores job, sets activeJobId
 *   3. useJobPolling polls and updates the job in `jobs[]`
 *   4. On done → gallery.addItem(result)
 *   5. On failed → ErrorState shown
 *   6. Gallery persists across refreshes via useGallery (localStorage)
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { generateImage, generateVideo, synthesizePrompt, uploadReferenceImage } from './api/client';
import { useJobPolling } from './hooks/useJobPolling';
import { useGallery } from './hooks/useGallery';
import { useToast } from './hooks/useToast';
import { PromptConsole } from './components/PromptConsole';
import { FinalPromptPanel } from './components/FinalPromptPanel';
import { JobStatusStrip } from './components/JobStatusStrip';
import { GeneratingState } from './components/GeneratingState';
import { ErrorState } from './components/ErrorState';
import { ResultGallery } from './components/ResultGallery';
import { ToastContainer } from './components/Toast';

const MAX_RECENT_JOBS = 20;

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [activeJobId, setActiveJobId] = useState(null);
  const [activeMode, setActiveMode] = useState('image');
  const [submitError, setSubmitError] = useState(null);   // error from the POST call itself
  const [lastSubmit, setLastSubmit] = useState(null);     // { prompt, mode } for retry
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [synthesizedPrompt, setSynthesizedPrompt] = useState(null);
  const [synthesizedMode, setSynthesizedMode] = useState(null); // 'image' or 'video'
  const [editedFinalPrompt, setEditedFinalPrompt] = useState('');
  const [lastSynthesizeRequest, setLastSynthesizeRequest] = useState(null); // to pass attributes on generate
  const [referenceImageUrl, setReferenceImageUrl] = useState(null); // uploaded CDN URL
  const [referenceImageFile, setReferenceImageFile] = useState(null); // File object for retry
  const [isUploadingImage, setIsUploadingImage] = useState(false);

  const gallery = useGallery();
  const { toasts, showToast, dismissToast } = useToast();
  // Track last toasted job to avoid duplicate toasts on re-renders
  const lastToastedJobId = useRef(null);

  // Poll the active job
  const { status, result, error: pollError, elapsedMs, estimatedWait } = useJobPolling(
    activeJobId,
    activeMode,
  );

  // Keep the jobs[] list in sync with polling output
  useEffect(() => {
    if (!activeJobId) return;
    setJobs((prev) =>
      prev.map((j) =>
        j.job_id === activeJobId
          ? {
              ...j,
              status: status ?? j.status,
              elapsedMs,
              estimatedWait,
              error: pollError?.message ?? j.error,
            }
          : j,
      ),
    );
  }, [activeJobId, status, elapsedMs, estimatedWait, pollError]);

  // When a job completes, add to gallery + show success toast
  useEffect(() => {
    if (status === 'done' && result?.result_url && activeJobId) {
      const activeJob = jobs.find((j) => j.job_id === activeJobId);
      gallery.addItem({
        ...result,
        job_id: activeJobId,
        raw_prompt: activeJob?.raw_prompt,
        final_prompt: activeJob?.final_prompt,
        created_at: Date.now(),
      });
      if (lastToastedJobId.current !== activeJobId) {
        lastToastedJobId.current = activeJobId;
        const label = activeJob?.mode === 'video' ? '🎬 Video' : '🖼 Image';
        showToast(`${label} generated successfully!`, 'success');
      }
    }
    if (status === 'failed' && activeJobId && lastToastedJobId.current !== activeJobId) {
      lastToastedJobId.current = activeJobId;
      showToast('Generation failed — please retry', 'error', 6000);
    }
  }, [status, result, activeJobId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Update final_prompt in jobs[] when polling returns it
  useEffect(() => {
    if (!activeJobId) return;
    if (result?.final_prompt) {
      setJobs((prev) =>
        prev.map((j) =>
          j.job_id === activeJobId ? { ...j, final_prompt: result.final_prompt } : j,
        ),
      );
    }
  }, [result, activeJobId]);

  // ── Submit handlers ─────────────────────────────────────────────────────────

  /**
   * Image submission — uses the 3-stage structured pipeline.
   * attributes: { subject, action, location, composition, style }
   */
  const handleSubmitImage = useCallback(
    async ({ attributes, prompt = '', skip_enhance = false }) => {
      setSubmitError(null);
      setLastSubmit({ type: 'image', attributes, prompt, skip_enhance });
      setSynthesizedPrompt(null);

      try {
        const jobResp = await generateImage(prompt, { attributes, skip_enhance });

        const newJob = {
          job_id: jobResp.job_id,
          mode: 'image',
          raw_prompt: skip_enhance ? prompt : `Structured: ${attributes.subject}`,
          final_prompt: null,
          status: 'queued',
          elapsedMs: 0,
          estimatedWait: null,
          error: null,
        };

        setJobs((prev) => [newJob, ...prev].slice(0, MAX_RECENT_JOBS));
        setActiveJobId(jobResp.job_id);
        setActiveMode('image');
      } catch (err) {
        setSubmitError({
          errorType: err.errorType ?? 'generic_failed',
          message: err.userMessage ?? err.message,
          provider: err.provider ?? '',
        });
      }
    },
    [],
  );

  /**
   * Video submission — structured 3-stage pipeline.
   */
  const handleSubmitVideo = useCallback(
    async ({ video_attributes, prompt = '', skip_enhance = false, reference_image_url = null }) => {
      setSubmitError(null);
      setLastSubmit({ type: 'video', video_attributes, prompt, skip_enhance, reference_image_url });
      setSynthesizedPrompt(null);

      try {
        const jobResp = await generateVideo(prompt, { video_attributes, skip_enhance, reference_image_url });

        const newJob = {
          job_id: jobResp.job_id,
          mode: 'video',
          raw_prompt: skip_enhance ? prompt : (video_attributes ? video_attributes.subject : 'Video Generation'),
          final_prompt: null,
          status: 'queued',
          elapsedMs: 0,
          estimatedWait: jobResp.estimated_wait_seconds
            ? jobResp.estimated_wait_seconds * 1000
            : null,
          error: null,
        };

        setJobs((prev) => [newJob, ...prev].slice(0, MAX_RECENT_JOBS));
        setActiveJobId(jobResp.job_id);
        setActiveMode('video');
      } catch (err) {
        setSubmitError({
          errorType: err.errorType ?? 'generic_failed',
          message: err.userMessage ?? err.message,
          provider: err.provider ?? '',
        });
      }
    },
    [],
  );

  const handleRetry = useCallback(() => {
    if (!lastSubmit) return;
    setSubmitError(null);
    if (lastSubmit.type === 'image') handleSubmitImage(lastSubmit);
    else handleSubmitVideo(lastSubmit);
  }, [lastSubmit, handleSubmitImage, handleSubmitVideo]);

  const handleSynthesizeImage = useCallback(async ({ attributes, prompt = '' }) => {
    setIsSynthesizing(true);
    setSubmitError(null);
    setActiveMode('image');
    setLastSynthesizeRequest({ attributes, prompt });
    setLastSubmit(null);
    
    try {
      const res = await synthesizePrompt({ mode: 'image', attributes, prompt });
      setSynthesizedPrompt(res.final_prompt);
      setEditedFinalPrompt(res.final_prompt);
      setSynthesizedMode('image');
    } catch (err) {
      setSubmitError({
        errorType: err.errorType ?? 'generic_failed',
        message: err.userMessage ?? err.message,
        provider: err.provider ?? '',
      });
    } finally {
      setIsSynthesizing(false);
    }
  }, []);

  const handleSynthesizeVideo = useCallback(async ({ video_attributes, prompt = '', referenceImage = null }) => {
    setIsSynthesizing(true);
    setSubmitError(null);
    setActiveMode('video');
    setLastSynthesizeRequest({ video_attributes, prompt });
    setLastSubmit(null);
    setReferenceImageFile(referenceImage);
    
    // Upload reference image if provided (do it early so it's ready for generate)
    if (referenceImage) {
      setIsUploadingImage(true);
      try {
        const uploadRes = await uploadReferenceImage(referenceImage);
        setReferenceImageUrl(uploadRes.url);
      } catch (err) {
        setSubmitError({
          errorType: err.errorType ?? 'generic_failed',
          message: err.userMessage ?? err.message ?? 'Failed to upload reference image',
          provider: err.provider ?? '',
        });
        setIsUploadingImage(false);
        setIsSynthesizing(false);
        return;
      }
      setIsUploadingImage(false);
    } else {
      setReferenceImageUrl(null);
    }
    
    try {
      const res = await synthesizePrompt({ mode: 'video', video_attributes, prompt });
      setSynthesizedPrompt(res.final_prompt);
      setEditedFinalPrompt(res.final_prompt);
      setSynthesizedMode('video');
    } catch (err) {
      setSubmitError({
        errorType: err.errorType ?? 'generic_failed',
        message: err.userMessage ?? err.message,
        provider: err.provider ?? '',
      });
    } finally {
      setIsSynthesizing(false);
    }
  }, []);

  const handleBackToEdit = useCallback(() => {
    setSynthesizedPrompt(null);
    setEditedFinalPrompt('');
  }, []);

  // ── Derived state ───────────────────────────────────────────────────────────

  const activeJob = jobs.find((j) => j.job_id === activeJobId);
  const isGenerating = status === 'queued' || status === 'generating';
  const isFailed = status === 'failed';

  const displayError = submitError || (isFailed ? (pollError ?? { errorType: 'generic_failed', message: 'That generation didn\'t go through. Retry', provider: '' }) : null);

  return (
    <div className="app">
      {/* ── Cosmic Starfield Background ── */}
      <div className="starfield" aria-hidden="true" />

      {/* ── Header — HUD Style ── */}
      <header className="app-header">
        <div className="app-header__inner">
          <h1 className="app-header__logo">
            <span className="app-header__logo-mark">◈</span>
            AI//STUDIO
          </h1>

          <div className="app-header__divider" aria-hidden="true" />

          <p className="app-header__tagline">Image &amp; Video Generation</p>

          <div className="app-header__spacer" />

          <div className="app-header__hud" aria-label="System status">
            <div className="hud-stat">
              <span className="hud-stat__dot" aria-hidden="true" />
              <span>Backend Online</span>
            </div>
            <div className="hud-stat">
              <span>{new Date().toISOString().slice(0, 10)}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="app-layout">

          {/* ── Left column: console + status ── */}
          <div className="app-layout__left">
            <PromptConsole
              onSynthesizeImage={handleSynthesizeImage}
              onSynthesizeVideo={handleSynthesizeVideo}
              onBackToEdit={handleBackToEdit}
              isSynthesizing={isSynthesizing}
              isGenerating={isGenerating}
              finalPrompt={lastSubmit?.prompt || null}
            />



            {/* Generating animation */}
            {isGenerating && (
              <GeneratingState
                mode={activeMode}
                elapsedMs={elapsedMs}
                estimatedWait={estimatedWait}
              />
            )}

            {/* Error state */}
            {displayError && (
              <ErrorState
                errorType={displayError.errorType}
                message={displayError.message}
                provider={displayError.provider}
                onRetry={handleRetry}
              />
            )}

            {/* Job strip */}
            <JobStatusStrip jobs={jobs} />
          </div>

          {/* ── Right column: gallery ── */}
          <div className="app-layout__right">
            <ResultGallery
              items={gallery.items}
              loading={gallery.loading}
              activeJob={isGenerating ? activeJob : null}
              promptPanel={
                (isSynthesizing || synthesizedPrompt || (activeJob && activeJob.final_prompt)) ? (
                  <div className="prompt-panel-wrapper">
                    <FinalPromptPanel
                      activeJob={
                        isGenerating
                          ? activeJob
                          : {
                              status: isSynthesizing ? 'generating' : 'synthesized',
                              final_prompt: synthesizedPrompt,
                              model: synthesizedMode === 'image' ? 'fal-ai/flux/dev' : 'wan-video/wan-2.2-i2v-fast',
                              provider: synthesizedMode === 'image' ? 'fal.ai' : 'replicate',
                            }
                      }
                      onPromptChange={(val) => setEditedFinalPrompt(val)}
                    />
                    {synthesizedPrompt && !isGenerating && (
                      <div className="prompt-panel-generate-btn" style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          className="btn btn--primary btn--large"
                          onClick={() => {
                            const isEdited = editedFinalPrompt !== synthesizedPrompt;
                            if (synthesizedMode === 'image') {
                              handleSubmitImage({
                                attributes: isEdited ? null : lastSynthesizeRequest?.attributes,
                                prompt: editedFinalPrompt,
                                skip_enhance: isEdited
                              });
                            } else {
                              handleSubmitVideo({
                                video_attributes: isEdited ? null : lastSynthesizeRequest?.video_attributes,
                                prompt: editedFinalPrompt,
                                skip_enhance: isEdited,
                                reference_image_url: referenceImageUrl,
                              });
                            }
                          }}
                        >
                          {synthesizedMode === 'image' ? '🖼 Generate Image' : '🎬 Generate Video'}
                        </button>
                      </div>
                    )}
                  </div>
                ) : null
              }
            />
          </div>

        </div>
      </main>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
