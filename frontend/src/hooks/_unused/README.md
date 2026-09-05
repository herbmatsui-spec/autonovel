# _unused/

このディレクトリには、現状の UI から呼び出されていないが将来復活予定の React hook を隔離しています。

- `useCollabSync.ts` - 共同編集同期 hook (UI 統合待ち)
- `usePatchReviews.ts` - パッチレビュー hook (UI 統合待ち)

復活時は `frontend/src/hooks/` 直下に戻し、呼び出し側の import パスを修正してください。
新規実装で必要な hook は **絶対に** このディレクトリに置かないでください。