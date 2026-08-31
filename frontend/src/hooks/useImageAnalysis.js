/**
 * useImageAnalysis.js — Manages Groq Call 1: raw description → 5 structured attributes.
 *
 * Returns:
 *   analyse(description)  — triggers the analysis
 *   attributes            — { subject, action, location, composition, style } | null
 *   rawDescription        — the original text the user typed (for the collapsible)
 *   analysing             — boolean
 *   analysisError         — { message } | null
 *   reset()               — clears attributes and returns to idle
 */
import { useState, useCallback } from 'react';
import { analyseImageDescription, ApiError } from '../api/client';

export function useImageAnalysis() {
  const [attributes, setAttributes] = useState(null);
  const [rawDescription, setRawDescription] = useState('');
  const [analysing, setAnalysing] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);

  const analyse = useCallback(async (description) => {
    if (!description?.trim()) return;

    setAnalysing(true);
    setAnalysisError(null);
    setRawDescription(description);

    try {
      const response = await analyseImageDescription(description.trim());
      setAttributes(response.attributes);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.userMessage
          : 'Analysis failed — please try again';
      setAnalysisError({ message });
      setAttributes(null);
    } finally {
      setAnalysing(false);
    }
  }, []);

  const reset = useCallback(() => {
    setAttributes(null);
    setRawDescription('');
    setAnalysisError(null);
    setAnalysing(false);
  }, []);

  /**
   * Update a single attribute field (called when user edits inline).
   * @param {string} key — one of: subject | action | location | composition | style
   * @param {string} value
   */
  const updateAttribute = useCallback((key, value) => {
    setAttributes((prev) => prev ? { ...prev, [key]: value } : prev);
  }, []);

  return {
    analyse,
    attributes,
    rawDescription,
    analysing,
    analysisError,
    reset,
    updateAttribute,
  };
}
