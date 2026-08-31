/**
 * useVideoAnalysis.js — Manages Groq Call 1 (Video): raw description → 10 structured attributes.
 *
 * Returns:
 *   analyse(description)    — triggers the video analysis
 *   attributes              — { subject, action, scene, style, temporal_elements,
 *                               camera_angles, camera_movements, lens_effects,
 *                               dialogue, sound_effects } | null
 *   rawDescription          — the original text the user typed (for the collapsible)
 *   analysing               — boolean
 *   analysisError           — { message } | null
 *   reset()                 — clears attributes and returns to idle
 *   updateAttribute(key, v) — edits a single attribute field
 */
import { useState, useCallback } from 'react';
import { analyseVideoDescription, ApiError } from '../api/client';

export function useVideoAnalysis() {
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
      const response = await analyseVideoDescription(description.trim());
      setAttributes(response.attributes);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.userMessage
          : 'Video analysis failed — please try again';
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
   * @param {string} key — one of the 10 video attribute keys
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
