/**
 * JobStatusStrip.jsx — Collapsible card showing all submitted jobs (active + recent).
 *
 * Features:
 *  - Collapsible with chevron toggle
 *  - Auto-expands when a new active/generating job is detected
 *  - Count badge in header when collapsed
 *  - Left border colour reflects overall status (amber=active, green=all done)
 *  - Each row shows: mode icon, prompt snippet, status badge, elapsed time
 *  - Inline error summary for failed jobs
 */
import { useState, useEffect } from 'react';

const MODE_ICONS = { image: '🖼', video: '🎬' };

const STATUS_LABELS = {
  queued: 'Queued',
  generating: 'Generating',
  done: 'Done',
  failed: 'Failed',
};

function formatElapsed(ms) {
  if (!ms || ms < 1000) return '<1s';
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

function JobStatusItem({ job }) {
  const {
    job_id,
    mode,
    raw_prompt,
    status,
    elapsedMs,
    estimatedWait,
    error,
  } = job;

  const snippet = (raw_prompt || '').slice(0, 60) + (raw_prompt?.length > 60 ? '…' : '');
  const isGenerating = status === 'generating';
  const isQueued = status === 'queued';
  const isFailed = status === 'failed';
  const isDone = status === 'done';

  return (
    <li
      className={`job-item job-item--${status}`}
      aria-label={`Job ${job_id}: ${status}`}
    >
      <span className="job-item__icon" aria-hidden="true">
        {MODE_ICONS[mode] ?? '?'}
      </span>

      <div className="job-item__body">
        <p className="job-item__prompt" title={raw_prompt}>
          {snippet || <em>No prompt</em>}
        </p>

        {/* Error summary for failed jobs */}
        {isFailed && error && (
          <p className="job-item__error">
            {error.slice(0, 80)}{error.length > 80 ? '…' : ''}
          </p>
        )}
      </div>

      <div className="job-item__meta">
        {/* Status badge */}
        <span className={`status-badge status-badge--${status}`}>
          {isGenerating && <span className="status-badge__dot" aria-hidden="true" />}
          {STATUS_LABELS[status] ?? status}
        </span>

        {/* Elapsed / estimated wait */}
        {(isGenerating || isQueued) && (
          <span className="job-item__time">
            {formatElapsed(elapsedMs)}
            {mode === 'video' && isGenerating && (
              <span className="job-item__estimate"> (~2–5 min)</span>
            )}
          </span>
        )}
        {isDone && elapsedMs > 0 && (
          <span className="job-item__time job-item__time--done">
            ✓ {formatElapsed(elapsedMs)}
          </span>
        )}
      </div>
    </li>
  );
}

export function JobStatusStrip({ jobs }) {
  const hasActiveJobs = jobs.some(
    (j) => j.status === 'generating' || j.status === 'queued',
  );

  // Auto-expand when jobs first appear or a new active job starts
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    if (hasActiveJobs) {
      setIsExpanded(true);
    }
  }, [hasActiveJobs]);

  if (!jobs || jobs.length === 0) return null;

  // Determine strip status modifier for left-border colour
  const stripModifier = hasActiveJobs
    ? 'job-strip--active'
    : jobs.some((j) => j.status === 'failed')
    ? 'job-strip--failed'
    : 'job-strip--done';

  return (
    <aside className={`job-strip ${stripModifier}`} aria-label="Job history">
      {/* Collapsible header */}
      <div className="job-strip__header">
        <button
          type="button"
          className="job-strip__collapse-btn"
          onClick={() => setIsExpanded((o) => !o)}
          aria-expanded={isExpanded}
          aria-controls="job-strip-list"
          aria-label={isExpanded ? 'Collapse jobs panel' : 'Expand jobs panel'}
        >
          <span className="job-strip__chevron" aria-hidden="true">
            {isExpanded ? '▾' : '▸'}
          </span>
          <span className="job-strip__title">Jobs</span>
          {!isExpanded && (
            <span className="job-strip__count-badge" aria-label={`${jobs.length} jobs`}>
              {jobs.length}
            </span>
          )}
          {hasActiveJobs && (
            <span className="job-strip__active-indicator" aria-hidden="true" />
          )}
        </button>
      </div>

      {/* Collapsible list */}
      {isExpanded && (
        <ul id="job-strip-list" className="job-strip__list" role="list">
          {jobs.map((job) => (
            <JobStatusItem key={job.job_id} job={job} />
          ))}
        </ul>
      )}
    </aside>
  );
}
