import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BranchTreeData } from '../types/branches';

export function useBranchTree(bookId: number) {
  const query = useQuery<BranchTreeData, Error>({
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

  const { refetch } = query;

  // WebSocket 経由でのブランチ更新通知リスナー (Step 65)
  useEffect(() => {
    if (!bookId || typeof window === 'undefined') return;

    let ws: WebSocket | null = null;
    let isMounted = true;

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/branches/${bookId}/ws`;

      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(event.data);
          // branch.merged イベントまたは関連イベントを受信したらブランチツリーを再取得
          if (
            data.event === 'branch.merged' ||
            data.type === 'branch.merged' ||
            data.event === 'branch.updated'
          ) {
            refetch();
          }
        } catch {
          // 非JSONメッセージは無視
        }
      };

      ws.onerror = () => {
        // 開発環境や未接続時もエラーでクラッシュさせない
      };
    } catch {
      // WebSocket接続不可環境（SSRやテスト時等）の安全フォールバック
    }

    return () => {
      isMounted = false;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [bookId, refetch]);

  return query;
}
