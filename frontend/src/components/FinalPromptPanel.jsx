import { useState, useEffect } from 'react';

/**
 * FinalPromptPanel
 * 
 * Displays the final synthesized prompt from the LLM.
 * Has an edit mode to let the user override the prompt and regenerate.
 */
export function FinalPromptPanel({ activeJob, onPromptChange }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState('');
  const [hasCopied, setHasCopied] = useState(false);

  // Auto-expand when a new final_prompt arrives, reset edit state
  useEffect(() => {
    if (activeJob?.final_prompt) {
      setEditedText(activeJob.final_prompt);
      setIsExpanded(true);
      setIsEditing(false);
    }
  }, [activeJob?.job_id, activeJob?.final_prompt]);

  // If no active job, don't render anything
  if (!activeJob) return null;

  const isGenerating = activeJob.status === 'queued' || activeJob.status === 'generating';
  const hasFinalPrompt = Boolean(activeJob.final_prompt);

  // Hidden unless it has a final prompt or is actively generating
  if (!hasFinalPrompt && !isGenerating) return null;

  const handleCopy = async () => {
    if (!activeJob.final_prompt) return;
    try {
      await navigator.clipboard.writeText(activeJob.final_prompt);
      setHasCopied(true);
      setTimeout(() => setHasCopied(false), 2000);
    } catch (e) {
      console.error('Copy failed', e);
    }
  };


  const wordCount = activeJob.final_prompt ? activeJob.final_prompt.trim().split(/\s+/).length : 0;

  return (
    <div className="final-prompt-panel">
      <header 
        className="final-prompt-panel__header" 
        onClick={() => hasFinalPrompt && setIsExpanded(e => !e)}
        role="button"
        tabIndex={0}
      >
        <h3 className="final-prompt-panel__title">Final Prompt Sent to Model</h3>
        {hasFinalPrompt && (
          <span className={`final-prompt-panel__chevron ${isExpanded ? 'final-prompt-panel__chevron--open' : ''}`}>
            ▼
          </span>
        )}
      </header>
      
      {/* Skeleton loader state */}
      {!hasFinalPrompt && isGenerating && (
        <div className="final-prompt-panel__body final-prompt-panel__skeleton">
          Refining your prompt...
        </div>
      )}

      {/* Expanded content */}
      {hasFinalPrompt && isExpanded && (
        <div className="final-prompt-panel__body">
          <div className="final-prompt-panel__content-wrapper">
            {isEditing ? (
              <textarea
                className="final-prompt-panel__textarea"
                value={editedText}
                onChange={(e) => {
                  setEditedText(e.target.value);
                  if (onPromptChange) onPromptChange(e.target.value);
                }}
                rows={6}
              />
            ) : (
              <div className="final-prompt-panel__text">
                {activeJob.final_prompt}
              </div>
            )}
            
            {!isEditing && (
              <button 
                type="button"
                className="final-prompt-panel__copy"
                onClick={handleCopy}
                title="Copy prompt"
                aria-label="Copy prompt"
              >
                {hasCopied ? (
                  <span className="final-prompt-panel__copied-text">Copied!</span>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                )}
              </button>
            )}
          </div>

          <div className="final-prompt-panel__footer">
            <div className="final-prompt-panel__meta">
              <span className="meta-chip">{wordCount} words</span>
              {activeJob.model && <span className="meta-chip">{activeJob.model}</span>}
              {activeJob.provider && <span className="meta-chip">{activeJob.provider}</span>}
            </div>

            <div className="final-prompt-panel__actions">
              {isEditing ? (
                <>
                  <button 
                    type="button" 
                    className="btn--ghost-danger" 
                    onClick={() => {
                      setIsEditing(false);
                      setEditedText(activeJob.final_prompt);
                      if (onPromptChange) onPromptChange(activeJob.final_prompt);
                    }}
                  >
                    Cancel
                  </button>
                  <button 
                    type="button" 
                    className="btn btn--primary" 
                    onClick={() => setIsEditing(false)}
                  >
                    Save Changes
                  </button>
                </>
              ) : (
                <button 
                  type="button" 
                  className="btn btn--secondary" 
                  onClick={() => setIsEditing(true)}
                  disabled={isGenerating}
                >
                  Edit Prompt
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
