/**
 * ブランチ管理 API クライアント (Step 61)
 */
import {
  BranchResponse,
  BranchForkRequest,
  BranchMergeRequest,
  BranchMergeCommitRequest,
  BranchMergeCommitResponse,
  MergePreviewResponse,
  BranchTreeData,
  ChapterDiffResponse,
} from '../types/branches';

/**
 * ブランチツリーを取得
 */
export async function fetchBranchTree(bookId: number): Promise<BranchTreeData> {
  const res = await fetch(`/api/branches/${bookId}/tree`);
  if (!res.ok) {
    throw new Error(`Failed to fetch branch tree: ${res.status}`);
  }
  return res.json();
}

/**
 * ブランチ一覧を取得
 */
export async function fetchBranches(bookId: number): Promise<BranchResponse[]> {
  const res = await fetch(`/api/branches/${bookId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch branches: ${res.status}`);
  }
  return res.json();
}

/**
 * ブランチをフォーク（分岐作成）
 */
export async function forkBranch(bookId: number, payload: BranchForkRequest): Promise<BranchResponse> {
  const res = await fetch(`/api/branches/${bookId}/fork`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Fork failed with status ${res.status}`);
  }
  return res.json();
}

/**
 * マージプレビューを取得
 */
export async function previewBranchMerge(
  bookId: number,
  payload: BranchMergeRequest
): Promise<MergePreviewResponse> {
  const res = await fetch(`/api/branches/${bookId}/merge/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Merge preview failed with status ${res.status}`);
  }
  return res.json();
}

/**
 * マージを確定コミット (Step 61)
 */
export async function commitBranchMerge(
  bookId: number,
  payload: BranchMergeCommitRequest
): Promise<BranchMergeCommitResponse> {
  const res = await fetch(`/api/branches/${bookId}/merge/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Merge commit failed with status ${res.status}`);
  }
  return res.json();
}
