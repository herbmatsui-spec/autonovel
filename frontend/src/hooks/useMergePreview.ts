import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BranchMergeRequest,
  MergePreviewResponse,
  BranchMergeCommitRequest,
  BranchMergeCommitResponse,
} from '../types/branches';
import { previewBranchMerge, commitBranchMerge } from '../api/branches';

export interface MergePreviewParams {
  bookId: number;
  payload: BranchMergeRequest;
}

export interface CommitMergeParams {
  bookId: number;
  payload: BranchMergeCommitRequest;
}

/**
 * マージプレビュー取得フック
 */
export function useMergePreview(bookId?: number) {
  return useMutation<MergePreviewResponse, Error, BranchMergeRequest | MergePreviewParams>({
    mutationFn: async (args) => {
      if ('payload' in args && 'bookId' in args) {
        return previewBranchMerge(args.bookId, args.payload);
      }
      const bId = bookId ?? 1;
      return previewBranchMerge(bId, args as BranchMergeRequest);
    },
  });
}

/**
 * マージ確定コミットフック (Step 62)
 */
export function useCommitBranchMerge() {
  const queryClient = useQueryClient();

  return useMutation<BranchMergeCommitResponse, Error, CommitMergeParams>({
    mutationFn: async ({ bookId, payload }) => {
      return commitBranchMerge(bookId, payload);
    },
    onSuccess: (_data, variables) => {
      // マージ完了に伴いブランチツリーやブランチ一覧のキャッシュを無効化
      queryClient.invalidateQueries({ queryKey: ['branchTree', variables.bookId] });
      queryClient.invalidateQueries({ queryKey: ['branches', variables.bookId] });
    },
  });
}
