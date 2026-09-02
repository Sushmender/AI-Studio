/**
 * Toast.jsx — Non-blocking toast notification container.
 *
 * Renders in a fixed bottom-right stack with slide-in/out animation.
 * Styled with amber glassmorphism to match the Cosmic Observatory design system.
 *
 * Props:
 *   toasts     — array from useToast()
 *   onDismiss  — callback(id)
 */

const TYPE_ICONS = {
  success: '✓',
  error: '✕',
  info: '◈',
};

const TYPE_CLASS = {
  success: 'toast--success',
  error: 'toast--error',
  info: 'toast--info',
};

function ToastItem({ toast, onDismiss }) {
  const icon = TYPE_ICONS[toast.type] ?? TYPE_ICONS.info;
  const cls = TYPE_CLASS[toast.type] ?? TYPE_CLASS.info;

  return (
    <div className={`toast ${cls}`} role="status" aria-live="polite">
      <span className="toast__icon" aria-hidden="true">{icon}</span>
      <span className="toast__message">{toast.message}</span>
      <button
        type="button"
        className="toast__close"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  );
}

export function ToastContainer({ toasts, onDismiss }) {
  if (!toasts.length) return null;

  return (
    <div className="toast-container" aria-label="Notifications" role="region">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
