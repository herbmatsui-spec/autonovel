# フロントエンド改善・品質向上 実装計画書

## 1. 目的
本計画は、フロントエンドの保守性、パフォーマンス、および信頼性を向上させるため、状態管理の刷新、テスト基盤の構築、およびドキュメントの整備を行うものである。

## 2. 全体戦略
- **状態管理**: `Zustand` を採用しグローバル状態を簡素化。`TanStack Query (React Query)` でサーバー状態を分離し、キャッシュと同期を自動化する。
- **テスト**: `Vitest` + `React Testing Library` でコンポーネントの正当性を保証し、`Playwright` でクリティカルパスの E2E テストを構築する。
- **ドキュメント**: `Storybook` を導入し、UI コンポーネントをカタログ化。開発者が迷わず導入できるオンボーディング資料を整備する。

---

## 3. 詳細実装ステップ (Step 1-36)

### フェーズ 1: 状態管理の刷新 (Step 1-12)
**【グローバル状態の移行 - Zustand】**
1. `zustand` のインストールと基本設定
2. ユーザー設定 (UserSettings) ストアの定義と実装
3. 現在編集中のプロジェクト (ProjectContext) ストアの定義と実装
4. `App.tsx` 等での既存の `useState` によるグローバル管理箇所の特定
5. ユーザー設定の移行と `props` ドリリングの解消 (Step A)
6. プロジェクトコンテキストの移行と `props` ドリリングの解消 (Step B)
7. Zustand ストアの永続化 (persist middleware) の導入 (設定保存用)

**【サーバー状態の移行 - React Query】**
8. `@tanstack/react-query` および `devtools` のインストール
9. `QueryClientProvider` のルートへの配置
10. `src/api.ts` の関数を `useQuery` / `useMutation` に適合する形式に整理
11. 主要なデータ取得処理 (例: プロジェクト一覧、書籍データ) の `useQuery` 化
12. キャッシュ更新ロジック (invalidateQueries) の実装による自動リフェッチの実現

### フェーズ 2: テストカバレッジの向上 (Step 13-24)
**【ユニットテスト基盤 - Vitest & RTL】**
13. `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom` のインストール
14. `vite.config.ts` へのテスト設定追加および `vitest.setup.ts` の作成
15. `package.json` へのテストスクリプト (`test`, `test:coverage`) の追加
16. `src/components/ui/button.tsx` の基本ユニットテスト作成
17. `src/components/ui/input.tsx` の基本ユニットテスト作成
18. `src/components/Sidebar.tsx` のレンダリングとインタラクションテスト作成
19. フォームコンポーネントのバリデーションおよび送信テスト作成
20. カスタムフック (`useBooks` 等) のロジックテスト作成
21. テストカバレッジの計測と不足箇所の特定
22. エッジケース（APIエラー時、データ空時）の UI 表示テスト追加

**【E2E テスト基盤 - Playwright】**
23. `playwright` のインストールと初期セットアップ (`npm init playwright@latest`)
24. 主要シナリオの自動化テスト作成 (ログイン → プロジェクト選択 → 編集 → 保存)

### フェーズ 3: ドキュメントとオンボーディングの充実 (Step 25-36)
**【Storybook 導入とコンポーネントカタログ化】**
25. `storybook` のインストールと初期化 (`npx storybook@latest init`)
26. Storybook のビルド設定および起動確認
27. `src/components/ui` 配下の全コンポーネントの `.stories.tsx` 作成
28. `Sidebar` コンポーネントの Story 作成 (状態別: 展開/折りたたみ)
29. `NarrativeGraph` などの複雑なコンポーネントの Mock データを用いた Story 作成
30. 各 Story への JSDoc によるプロパティ説明の追加
31. Storybook 上でのインタラクティブな Controls 設定の最適化

**【開発ドキュメントの整備】**
32. `frontend/README.md` の刷新 (環境構築手順の最新化)
33. 利用可能な npm スクリプトの詳細説明の追加
34. フロントエンドのディレクトリ構造とアーキテクチャ設計の記述
35. コンポーネント作成ガイドライン (命名規則、ディレクトリ配置) の策定と追記
36. 全体的な動作確認と最終的なドキュメントレビュー
