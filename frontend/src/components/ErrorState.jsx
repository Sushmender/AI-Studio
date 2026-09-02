/**
 * ErrorState.jsx — Renders specific, in-voice error messages.
 *
 * Props:
 *   errorType  — one of the 7 defined error types
 *   message    — the exact user-facing copy
 *   provider   — "fal.ai" | "replicate" | "groq" | "" (optional badge)
 *   onRetry    — callback to retry the last action
 */

const ERROR_ICONS = {
  network_offline: '📡',
  rate_limit: '🚦',
  groq_timeout: '⏱',
  fal_server_error: '🔴',
  replicate_timeout: '⏱',
  generic_failed: '⚠️',
};

const PROVIDER_LABELS = {
  'fal.ai': 'fal.ai',
  replicate: 'Replicate',
  groq: 'Groq',
};

export function ErrorState({ errorType = 'generic_failed', message, provider, onRetry }) {
  const icon = ERROR_ICONS[errorType] ?? '⚠️';
  const providerLabel = PROVIDER_LABELS[provider] || provider;
  const isGroqTimeout = errorType === 'groq_timeout';

  return (
    <div
      className={`error-state error-state--${errorType}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="error-state__header">
        <span className="error-state__icon" aria-hidden="true">{icon}</span>
        <div className="error-state__title-row">
          <span className="error-state__title">
            {isGroqTimeout ? 'Prompt enhancement timeout' : 'That generation didn\'t go through'}
          </span>
          {providerLabel && (
            <span className="error-state__provider-badge">{providerLabel}</span>
          )}
        </div>
      </div>

      <p className="error-state__message">{message}</p>

      {!isGroqTimeout && onRetry && (
        <button
          id="error-retry-btn"
          type="button"
          className="btn btn--secondary"
          onClick={onRetry}
        >
          Retry
        </button>
      )}
    </div>
  );
}
