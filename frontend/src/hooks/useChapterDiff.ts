import { useQuery } from '@tanstack/react-query';
import { ChapterDiffResponse } from '@/types/branches';

export function useChapterDiff(bookId: number, branchAId: number, branchBId: number, chapterNumber: number) {
  return useQuery<ChapterDiffResponse, Error>({
    queryKey: ['chapterDiff', bookId, branchAId, branchBId, chapterNumber],
    queryFn: async () => {
      const response = await fetch(
        `/api/branches/diff?bookId=${bookId}&branchA=${branchAId}&branchB=${branchBId}&chapter=${chapterNumber}`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch chapter diff: ${response.status}`);
      }
      return response.json();
    },
    enabled: !!bookId && !!branchAId && !!branchBId && !!chapterNumber,
  });
}
