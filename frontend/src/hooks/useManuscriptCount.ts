import { useMemo } from 'react';
import { countManuscript, ManuscriptCountResult } from '../utils/manuscriptCount';

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
