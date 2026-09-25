import { useMemo } from 'react';
import { countManuscript } from '../utils/manuscriptCount';
import { ManuscriptCountResult } from '../types/manuscript';

export function useManuscriptCount(content: string = ''): ManuscriptCountResult {
  return useMemo(() => {
    if (!content) {
      return {
        body: 0,
        withRuby: 0,
        publishing: 0,
        pages: 0,
        lines: 0,
        readingTimeMinutes: 0,
      };
    }
    return countManuscript(content);
  }, [content]);
}
