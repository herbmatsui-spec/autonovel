export interface InlineRevisionProposal {
  originalText: string;
  revisedText: string;
  selectionRange: {
    start: number;
    end: number;
  };
  metadata: {
    timestamp: number;
    model: string;
    prompt: string;
  };
}

export interface InlineRevisionDiff {
  operations: DiffOperation[];
  originalLength: number;
  revisedLength: number;
}

export type DiffOperationType = 'equal' | 'insert' | 'delete';

export interface DiffOperation {
  type: DiffOperationType;
  text: string;
  originalIndex?: number;
  revisedIndex?: number;
}

export interface InlineRevisionValidationResult {
  isValid: boolean;
  mismatchReason?: ValidationMismatchReason;
  originalTextSnapshot: string;
  currentTextSnapshot: string;
  diff?: InlineRevisionDiff;
}

export type ValidationMismatchReason =
  | 'text_changed'
  | 'selection_shifted'
  | 'document_modified'
  | 'concurrent_edit';

export type InlineRevisionAction = 'apply' | 'reject' | 'hold' | 'regenerate';

export type InlineRevisionStatus =
  | 'idle'
  | 'generating'
  | 'diff_ready'
  | 'validating'
  | 'applying'
  | 'applied'
  | 'rejected'
  | 'held'
  | 'error';