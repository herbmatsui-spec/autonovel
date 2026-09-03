import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from "@tanstack/react-query";
import { patchReviewApi, PatchReview, ReviewActionRequest, ReviseReviewRequest } from "../api/patchReviewApi";

export function usePatchReviews(bookId: number | null, enabled = true): UseQueryResult<PatchReview[], Error> {
  return useQuery({
    queryKey: ["patchReviews", bookId],
    queryFn: () => patchReviewApi.getPendingReviews(bookId!),
    enabled: enabled && bookId !== null,
    refetchInterval: 10000, // Poll every 10 seconds
    staleTime: 5000,
  });
}

export function usePatchReview(reviewId: number | null, enabled = true): UseQueryResult<PatchReview, Error> {
  return useQuery({
    queryKey: ["patchReview", reviewId],
    queryFn: () => patchReviewApi.getReviewDetail(reviewId!),
    enabled: enabled && reviewId !== null,
    refetchInterval: 5000,
    staleTime: 2000,
  });
}

export function useApproveReview(): UseMutationResult<{ message: string }, Error, { reviewId: number; data: ReviewActionRequest }, unknown> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ reviewId, data }: { reviewId: number; data: ReviewActionRequest }) =>
      patchReviewApi.approveReview(reviewId, data),
    onSuccess: (_: { message: string }, { reviewId }: { reviewId: number; data: ReviewActionRequest }) => {
      queryClient.invalidateQueries({ queryKey: ["patchReview", reviewId] });
      queryClient.invalidateQueries({ queryKey: ["patchReviews"] });
    },
  });
}

export function useRejectReview(): UseMutationResult<{ message: string }, Error, { reviewId: number; data: ReviewActionRequest }, unknown> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ reviewId, data }: { reviewId: number; data: ReviewActionRequest }) =>
      patchReviewApi.rejectReview(reviewId, data),
    onSuccess: (_: { message: string }, { reviewId }: { reviewId: number; data: ReviewActionRequest }) => {
      queryClient.invalidateQueries({ queryKey: ["patchReview", reviewId] });
      queryClient.invalidateQueries({ queryKey: ["patchReviews"] });
    },
  });
}

export function useReviseReview(): UseMutationResult<{ message: string }, Error, { reviewId: number; data: ReviseReviewRequest }, unknown> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ reviewId, data }: { reviewId: number; data: ReviseReviewRequest }) =>
      patchReviewApi.reviseReview(reviewId, data),
    onSuccess: (_: { message: string }, { reviewId }: { reviewId: number; data: ReviseReviewRequest }) => {
      queryClient.invalidateQueries({ queryKey: ["patchReview", reviewId] });
      queryClient.invalidateQueries({ queryKey: ["patchReviews"] });
    },
  });
}

// WebSocket-based real-time updates (when available)
export function useWebSocketPatchReviews(bookId: number | null) {
  // TODO: Implement WebSocket connection for real-time updates
  // This would replace polling with push notifications
  // For now, return the polling-based hook
  return usePatchReviews(bookId);
}