import { useState, useCallback, useRef } from 'react';
import {
  InlineRevisionProposal,
  InlineRevisionDiff,
  InlineRevisionValidationResult,
  InlineRevisionAction,
  InlineRevisionStatus,
} from '../types/inlineRevision';
import { computeTextDiff, applyDiff } from '../utils/textDiff';
import { verifySelection } from '../utils/selectionVerify';

interface UseInlineRevisionOptions {
  onApply?: (revisedText: string) => void;
  onReject?: () => void;
  onHold?: () => void;
  onError?: (error: Error) => void;
}

export function useInlineRevision(options: UseInlineRevisionOptions = {}) {
  const [status, setStatus] = useState<InlineRevisionStatus>('idle');
  const [proposal, setProposal] = useState<InlineRevisionProposal | null>(null);
  const [diff, setDiff] = useState<InlineRevisionDiff | null>(null);
  const [validationResult, setValidationResult] = useState<InlineRevisionValidationResult | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [action, setAction] = useState<InlineRevisionAction | null>(null);

  const originalTextRef = useRef<string>('');
  const selectionRangeRef = useRef<{ start: number; end: number } | null>(null);
  const documentRef = useRef<HTMLElement | null>(null);

  const generateProposal = useCallback(async (
    originalText: string,
    selectionRange: { start: number; end: number },
    documentElement: HTMLElement,
    prompt: string,
    model: string
  ) => {
    setStatus('generating');
    setError(null);

    try {
      originalTextRef.current = originalText;
      selectionRangeRef.current = selectionRange;
      documentRef.current = documentElement;

      const selectedText = originalText.slice(selectionRange.start, selectionRange.end);

      const response = await fetch('/api/revision/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: selectedText,
          context: originalText,
          prompt,
        }),
      });

      if (!response.ok) {
        throw new Error(`Revision generation failed: ${response.statusText}`);
      }

      const data = await response.json();
      const revisedText = data.revisedText;

      const proposal: InlineRevisionProposal = {
        originalText: selectedText,
        revisedText,
        selectionRange,
        metadata: {
          timestamp: Date.now(),
          model,
          prompt,
        },
      };

      setProposal(proposal);
      setStatus('diff_ready');

      const diff = computeTextDiff(selectedText, revisedText);
      setDiff(diff);
      setStatus('validating');

      const validation = verifySelection(
        originalText,
        selectionRange,
        documentElement
      );

      setValidationResult(validation);

      if (!validation.isValid) {
        setStatus('diff_ready');
      } else {
        setStatus('diff_ready');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      setStatus('error');
      options.onError?.(error);
    }
  }, []);

  const validateAndPrepare = useCallback(() => {
    if (!proposal || !selectionRangeRef.current || !documentRef.current) {
      return false;
    }

    const validation = verifySelection(
      originalTextRef.current,
      selectionRangeRef.current,
      documentRef.current
    );

    setValidationResult(validation);

    if (!validation.isValid) {
      setStatus('diff_ready');
      return false;
    }

    return true;
  }, [proposal]);

  const apply = useCallback(() => {
    if (!proposal || !diff) return;

    const validation = validateAndPrepare();
    if (!validation) {
      setAction('hold');
      return;
    }

    setStatus('applying');
    const fullText = originalTextRef.current;
    const { start, end } = selectionRangeRef.current!;
    const before = fullText.slice(0, start);
    const after = fullText.slice(end);
    const revisedFullText = before + proposal.revisedText + after;

    options.onApply?.(revisedFullText);

    setStatus('applied');
    setAction('apply');
  }, [proposal, diff]);

  const reject = useCallback(() => {
    options.onReject?.();
    setStatus('rejected');
    setAction('reject');
    reset();
  }, []);

  const hold = useCallback(() => {
    options.onHold?.();
    setStatus('held');
    setAction('hold');
  }, []);

  const regenerate = useCallback(async () => {
    if (!proposal) return;
    const { originalText, selectionRange, metadata } = proposal;
    await generateProposal(
      originalTextRef.current,
      selectionRangeRef.current!,
      documentRef.current!,
      metadata.prompt,
      metadata.model
    );
  }, [proposal]);

  const reset = useCallback(() => {
    setProposal(null);
    setDiff(null);
    setValidationResult(null);
    setError(null);
    setAction(null);
    originalTextRef.current = '';
    selectionRangeRef.current = null;
    documentRef.current = null;
    setStatus('idle');
  }, []);

  return {
    status,
    proposal,
    diff,
    validationResult,
    error,
    action,
    generateProposal,
    apply,
    reject,
    hold,
    regenerate,
    reset,
  };
}