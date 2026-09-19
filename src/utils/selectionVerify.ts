import { InlineRevisionValidationResult, ValidationMismatchReason } from '../types/inlineRevision';

export interface SelectionVerificationOptions {
  tolerance?: number;
  ignoreWhitespace?: boolean;
}

export function verifySelection(
  fullText: string,
  selectionRange: { start: number; end: number },
  documentElement: HTMLElement,
  options: SelectionVerificationOptions = {}
): InlineRevisionValidationResult {
  const { tolerance = 0, ignoreWhitespace = true } = options;

  const currentText = documentElement.innerText || documentElement.textContent || '';
  const expectedSelectedText = fullText.slice(selectionRange.start, selectionRange.end);

  if (ignoreWhitespace) {
    const normalizedCurrent = currentText.replace(/\s+/g, ' ').trim();
    const normalizedFull = fullText.replace(/\s+/g, ' ').trim();
    const normalizedSelected = expectedSelectedText.replace(/\s+/g, ' ').trim();

    if (normalizedCurrent !== normalizedFull) {
      return {
        isValid: false,
        mismatchReason: 'document_modified',
        originalTextSnapshot: fullText,
        currentTextSnapshot: currentText,
      };
    }

    const currentSelection = window.getSelection();
    if (!currentSelection || currentSelection.rangeCount === 0) {
      return {
        isValid: false,
        mismatchReason: 'selection_shifted',
        originalTextSnapshot: fullText,
        currentTextSnapshot: currentText,
      };
    }

    const currentSelectionText = currentSelection.toString().replace(/\s+/g, ' ').trim();
    if (currentSelectionText !== normalizedSelected) {
      return {
        isValid: false,
        mismatchReason: 'selection_shifted',
        originalTextSnapshot: fullText,
        currentTextSnapshot: currentText,
      };
    }

    return {
      isValid: true,
      originalTextSnapshot: fullText,
      currentTextSnapshot: currentText,
    };
  }

  const currentSelection = window.getSelection();
  if (!currentSelection || currentSelection.rangeCount === 0) {
    return {
      isValid: false,
      mismatchReason: 'selection_shifted',
      originalTextSnapshot: fullText,
      currentTextSnapshot: currentText,
    };
  }

  const currentSelectionText = currentSelection.toString();
  const actualStart = currentText.indexOf(currentSelectionText);
  const actualEnd = actualStart + currentSelectionText.length;

  const startDiff = Math.abs(selectionRange.start - actualStart);
  const endDiff = Math.abs(selectionRange.end - actualEnd);

  if (startDiff > tolerance || endDiff > tolerance) {
    return {
      isValid: false,
      mismatchReason: 'selection_shifted',
      originalTextSnapshot: fullText,
      currentTextSnapshot: currentText,
    };
  }

  if (fullText !== currentText) {
    const firstDiffIndex = findFirstDifference(fullText, currentText);
    if (firstDiffIndex >= selectionRange.start && firstDiffIndex < selectionRange.end) {
      return {
        isValid: false,
        mismatchReason: 'text_changed',
        originalTextSnapshot: fullText,
        currentTextSnapshot: currentText,
      };
    }
  }

  return {
    isValid: true,
    originalTextSnapshot: fullText,
    currentTextSnapshot: currentText,
  };
}

function findFirstDifference(str1: string, str2: string): number {
  const minLength = Math.min(str1.length, str2.length);
  for (let i = 0; i < minLength; i++) {
    if (str1[i] !== str2[i]) {
      return i;
    }
  }
  return minLength;
}

export function createTextSnapshot(text: string): string {
  return text;
}

export function compareSnapshots(
  original: string,
  current: string,
  selectionRange: { start: number; end: number }
): ValidationMismatchReason | null {
  if (original === current) return null;

  const firstDiff = findFirstDifference(original, current);
  if (firstDiff >= selectionRange.start && firstDiff < selectionRange.end) {
    return 'text_changed';
  }

  if (original.length !== current.length) {
    return 'document_modified';
  }

  return 'concurrent_edit';
}

function findFirstDifference(str1: string, str2: string): number {
  const minLength = Math.min(str1.length, str2.length);
  for (let i = 0; i < minLength; i++) {
    if (str1[i] !== str2[i]) {
      return i;
    }
  }
  return minLength;
}