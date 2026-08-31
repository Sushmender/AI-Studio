/**
 * JobStatusStrip.jsx — Live list of all submitted jobs (active + recent).
 *
 * Each row shows:
 *  - Mode icon (🖼/🎬)
 *  - Prompt snippet (first 60 chars)
 *  - Status badge with pulsing dot for generating
 *  - Elapsed time / estimated wait for video jobs
 *  - Inline error summary for failed jobs
 */

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
  if (!jobs || jobs.length === 0) return null;

  return (
    <aside className="job-strip" aria-label="Job history">
      <h2 className="job-strip__title">Jobs</h2>
      <ul className="job-strip__list" role="list">
        {jobs.map((job) => (
          <JobStatusItem key={job.job_id} job={job} />
        ))}
      </ul>
    </aside>
  );
}
