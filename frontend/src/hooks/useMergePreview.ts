import { useMutation } from '@tanstack/react-query';
import { BranchMergeRequest, MergePreviewResponse } from '@/types/branches';

export function useMergePreview() {
  return useMutation<MergePreviewResponse, Error, BranchMergeRequest>({
    mutationFn: async (payload) => {
      const response = await fetch('/api/branches/merge/preview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to preview merge: ${response.status}`);
      }
      
      return response.json();
    },
  });
}
