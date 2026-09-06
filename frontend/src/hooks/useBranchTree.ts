import { useQuery } from '@tanstack/react-query';
import { BranchTreeData } from '../types/branches';

export function useBranchTree(bookId: number) {
  return useQuery<BranchTreeData, Error>({
    queryKey: ['branchTree', bookId],
    queryFn: async () => {
      const response = await fetch(`/api/branches/${bookId}/tree`);
      if (!response.ok) {
        throw new Error(`Failed to fetch branch tree: ${response.status}`);
      }
      return response.json();
    },
    // Enable caching and automatic refetching
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });
}
