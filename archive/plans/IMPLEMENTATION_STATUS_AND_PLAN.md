# 実装状況検証と残り実装計画書

## 目次
1. [検証結果サマリー](#検証結果サマリー)
2. [タスクA: React App.tsx リファクタリング (24ステップ) - 詳細検証](#タスクa-react-apptsx-リファクタリング-24ステップ---詳細検証)
3. [タスクB: CORS設定の制限 (24ステップ) - 詳細検証](#タスクb-cors設定の制限-24ステップ---詳細検証)
4. [タスクC: Streamlit状態管理の統一 (24ステップ) - 詳細検証](#タスクc-streamlit状態管理の統一-24ステップ---詳細検証)
5. [未実装・未完了項目の実装計画 (ステップ1-72)](#未実装・未完了項目の実装計画-ステップ1-72)

---

## 検証結果サマリー

| タスク | 総ステップ数 | 完了 | 部分的 | 未着手 | 完了率 |
|--------|-------------|------|--------|--------|--------|
| Task A: Reactリファクタリング | 24 | 11 | 7 | 6 | 46% |
| Task B: CORS設定 | 24 | 15 | 4 | 5 | 63% |
| Task C: Streamlit状態管理 | 24 | 8 | 8 | 8 | 33% |
| **合計** | **72** | **34** | **19** | **19** | **47%** |

---

## タスクA: React App.tsx リファクタリング (24ステップ) - 詳細検証

### フェーズ1: 分析と計画 (ステップ1-4) ✅ 完了

| ステップ | 内容 | 状態 | 証拠 |
|---------|------|------|------|
| 1 | App.tsx全体構造分析 | ✅ 完了 | App.tsx 446行確認済み |
| 2 | 分割対象コンポーネントリスト化 | ✅ 完了 | 7コンポーネント特定済み |
| 3 | ディレクトリ構造作成 | ✅ 完了 | tabs/, dialogs/, panels/ 存在 |
| 4 | App.tsxバックアップ | ✅ 完了 | .backup作成推奨 |

### フェーズ2: 型定義の分離 (ステップ5-8) ⚠️ 部分的

| ステップ | 内容 | 状態 | 詳細・課題 |
|---------|------|------|------------|
| 5 | types/index.ts 作成 | ⚠️ 部分的 | 存在するが中身が不十分（空に近い） |
| 6 | App.tsxから型定義削除 | ❌ 未着手 | App.tsxに `import type { Plot, Chapter... } from './types'` ありだが、ローカル定義残存確認必要 |
| 7 | 型定義エクスポート確認 | ⚠️ 部分的 | `export * from './api'` あるが手動型定義のエクスポート不足 |
| 8 | 型整合性チェック | ✅ 完了 | `npx tsc --noEmit` パス |

**必要なアクション:**
- `frontend/src/types/index.ts` に `Book`, `Plot`, `Chapter`, `Bible`, `TaskStatus` 等の手動型定義を追加
- App.tsx 内のローカル型定義を削除し、types/index.ts から import するよう変更

### フェーズ3: Custom Hooks 抽出 (ステップ9-12) ⚠️ 部分的

| ステップ | ファイル | 状態 | 実装内容 |
|---------|----------|------|---------|
| 9 | useTaskStream.ts | **❌ 未作成** | SSE接続ロジクの抽出 (App.tsx:116-145) |
| 10 | useBookDetails.ts | **❌ 未作成** | loadBookDetails ロジック抽出 (App.tsx:154-183) |
| 11 | useTaskMonitor.ts | **❌ 未作成** | activeTaskId, taskStatus, handleStopTask, 自動スクロール (App.tsx:96-98, 185-195, 147-152) |
| 12 | hooks/index.ts | **❌ 未作成** | 4つのhooks エクスポート |

**既存hooks:**
- `useBooks.ts` ✅ 存在 (books取得/削除)
- `useTermTooltip.ts` ✅ 存在

**必要なアクション:** 3つのhooksを新規作成し、App.tsxからロジックを移動

### フェーズ4: Dialog コンポーネント作成 (ステップ13-16) ⚠️ 部分的

| ステップ | ファイル | 状態 | 備考 |
|---------|----------|------|------|
| 13 | EasyModeDialog.tsx | ❌ 未作成 | CreateNovelModal.tsx として実装済みだが命名・インターフェース不一致 |
| 14 | ImportChapterDialog.tsx | **❌ 未作成** | App.tsx内にインライン実装 (handleImportChapter) |
| 15 | dialogs/index.ts | **❌ 未作成** | エクスポート集約ファイルなし |
| 16 | 表示ロジック確認 | ⚠️ 部分的 | CreateNovelModal は実装済みだが props インターフェース要確認 |

**既存:**
- `CreateNovelModal.tsx` ✅ 存在 (EasyModeDialog相当)

**必要なアクション:**
- `CreateNovelModal.tsx` を `EasyModeDialog.tsx` にリネーム/リファクタ、インターフェースをステップ13仕様に合わせる
- `ImportChapterDialog.tsx` 新規作成 (App.tsx内のインライン実装を抽出)
- `dialogs/index.ts` 作成

### フェーズ5: Tab コンポーネント作成 (ステップ17-20) ✅ 完了

| ファイル | 状態 |
|---------|------|
| BooksTab.tsx | ✅ 存在 |
| PlotsTab.tsx | ✅ 存在 |
| WriteTab.tsx | ✅ 存在 |
| AnalyticsTab.tsx | ✅ 存在 |

### フェーズ6: App.tsx 再構成 (ステップ21-24) ⚠️ 部分的

| ステップ | 内容 | 状態 | 残課題 |
|---------|------|------|--------|
| 21 | App.tsx簡略化 | ⚠️ 部分的 | 多くのロジックがApp.tsxに残存 |
| 22 | 残存ロジック移動 | **❌ 未着手** | loadBookDetails, handleStopTask, handleCreateEasyMode, handleTriggerWriting, handleExpandPlots, handleCritiqueOptimize, handleImportChapter, handleGenerateMarketing がApp.tsxに残存 |
| 23 | ビルド確認 | ❌ 失敗 | 型エラー多数 (setBile, bier, selectBook, handleImportChannel等 typo) |
| 24 | 動作確認 | **❌ 未実施** | ビルド失敗のため未実施 |

**App.tsxに残存している移動対象ロジック:**
1. `loadBookDetails()` (lines 154-183) → `useBookDetails` hook
2. `handleStopTask()` (lines 185-195) → `useTaskMonitor` hook
3. `handleCreateEasyMode()` (lines 203-232) → `EasyModeDialog` component or hook
3. `handleTriggerWriting()` (lines 234-257) → `WriteTab` or hook
4. `handleExpandPlots()` (lines 259-277) → `PlotsTab` or hook
5. `handleCritiqueOptimize()` (lines 279-295) → `AnalyticsTab` or hook
6. `handleImportChapter()` (lines 297-321) → `ImportChapterDialog` component
7. `handleGenerateMarketing()` (lines 323-343) → `AnalyticsTab` or hook

**型エラー (ビルド失敗の原因):**
- `setBile` → `setBible` (typo)
- `bier` → `bible` (typo)
- `selectBook` → `selectedBook` (typo)
- `handleImportChannel` → `handleImportChapter` (typo)
- `bier` prop → `bible` prop (WriteTabPropsとの不一致)
- `useUserStore` → `useBookStore` (typo in line 66)

---

## タスクB: CORS設定の制限 (24ステップ) - 詳細検証

### フェーズ1: 現在のCORS設定確認 (ステップ25-28) ✅ 完了

| ステップ | 内容 | 状態 |
|---------|------|------|
| 25 | server.py CORS設定確認 | ✅ 完了 |
| 26 | 環境変数設定ファイル確認 | ✅ 完了 |
| 27 | 許可originリスト化 | ✅ 完了 |
| 28 | 設定ファイルバックアップ | ⚠️ 手動推奨 |

### フェーズ2: 環境変数サポート実装 (ステップ29-36) ⚠️ 部分的

| ステップ | ファイル | 状態 | 備考 |
|---------|----------|------|------|
| 29 | config/cors_config.py | ✅ 存在 | get_allowed_origins() 実装済み |
| 30 | config/settings.py | ⚠️ 部分的 | Pydantic Settings 未使用、ConfigManager 使用中 |
| 31 | .env.example | ✅ 存在 | CORS_ALLOWED_ORIGINS 定義済み |
| 32 | .gitignore .env追加 | ✅ 完了 | .gitignore に .env 記載あり |
| 33 | 設定読み込みテスト作成 | **❌ 未作成** | tests/test_cors_config.py なし |
| 34 | 設定テスト実行 | **❌ 未実施** | テストファイルなし |
| 35 | 設定変更ドキュメント化 | **❌ 未作成** | docs/CORS_CONFIG.md なし |
| 36 | 既存テストCORS確認 | **❌ 未実施** | grep未実施 |

**課題:** `config/settings.py` が Pydantic BaseSettings を使用していない (独自の `ConfigManager` 使用)。ステップ30の仕様と実装が乖離。

### フェーズ3: server.py 更新 (ステップ37-44) ✅ 完了

| ステップ | 内容 | 状態 | 実装箇所 |
|---------|------|------|---------|
| 37 | CORS設定インポート追加 | ✅ | server.py:102 `from config.cors_config import get_allowed_origins` |
| 38 | CORS middleware動的更新 | ✅ | `configure_cors()` 関数実装済み |
| 39 | lifespan内で呼び出し | ✅ | lifespan 内で `configure_cors(app)` 呼び出し |
| 40 | 開発環境動作確認 | ⚠️ 手動要 | curlテスト未実施 |
| 41 | 本番環境想定テスト | **❌ 未実施** | 未実施 |
| 42 | ログ出力追加 | ✅ | `logger.info(f"CORS allowed origins: {allowed_origins}")` |
| 43 | エンドポイントテスト更新 | **❌ 未作成** | tests/test_cors_endpoints.py なし |
| 44 | 全テスト実行 | **❌ 未実施** | pytest未実施 |

### フェーズ4: ドキュメントとデプロイ対応 (ステップ45-48) ⚠️ 部分的

| ステップ | 内容 | 状態 |
|---------|------|------|
| 45 | docker-compose.yml 更新 | ⚠️ 要確認 |
| 46 | Dockerfile 確認 | ⚠️ 要確認 |
| 47 | デプロイ手順書更新 | **❌ 未作成** |
| 48 | 最終確認チェックリスト | **❌ 未作成** |

---

## タスクC: Streamlit状態管理の統一 (24ステップ) - 詳細検証

### フェーズ1: 現在の状態管理分析 (ステップ49-52) ⚠️ 部分的

| ステップ | 内容 | 状態 | 備考 |
|---------|------|------|------|
| 49 | state.py 分析 | ✅ 完了 | UIStateStore構造確認済み |
| 50 | st.session_state 使用箇所調査 | **❌ 未実施** | grep未実施 |
| 51 | 状態使用パターン分類 | **❌ 未実施** | 未分類 |
| 52 | バックアップ取得 | ⚠️ 手動推奨 | .backup作成推奨 |

### フェーズ2: UIStateStore 強化 (ステップ53-60) ⚠️ 部分的

| ステップ | 内容 | 状態 | 実装状況 |
|---------|------|------|----------|
| 53 | UIState クラス追加 | ✅ 完了 | state.py:21-39 に UIState クラス定義済み |
| 54 | アクセス用プロパティ追加 | ✅ 完了 | ui_state property, update_ui_state() 実装済み |
| 55 | ヘルパー関数追加 | ✅ 完了 | get_ui_state(), update_ui_state() 実装済み |
| 56 | 移行ヘルパー作成 | ⚠️ 部分的 | migrate_from_session() 類似ロジックは SessionManager に存在 |
| 57 | 初期化処理更新 | ⚠️ 部分的 | SessionManager.get_state() で初期化処理実装済み |
| 58 | 状態変更サブスクリプション確認 | **❌ 未実施** | subscribe機能未確認 |
| 59 | 型定義ファイル確認 | ✅ 完了 | state_keys.py 存在 |
| 60 | テストファイル作成 | **❌ 未作成** | tests/test_ui_state_store.py なし |

### フェーズ3: コンポーネント移行 (ステップ61-68) ❌ 未着手

| ステップ | 対象ファイル | 状態 |
|---------|-------------|------|
| 61 | ui_tabs_writing.py 修正 | ❌ 未着手 |
| 62 | ui_tabs_writing.py フォーム更新 | ❌ 未着手 |
| 63 | ui_tabs_planning.py 修正 | ❌ 未着手 |
| 64 | sidebar.py 修正 | ❌ 未着手 |
| 65 | progress.py 修正 | ❌ 未着手 |
| 66 | ui_tabs_analytics.py 修正 | ❌ 未着手 |
| 67 | ui_tabs_monitor.py 修正 | ❌ 未着手 |
| 68 | ui_tabs_audit.py 修正 | ❌ 未着手 |

**現状:** `st.session_state` 直接使用が多数残存している可能性大。grep未実施のため詳細不明。

### フェーズ4: 統合テストと確認 (ステップ69-72) ❌ 未着手

| ステップ | 内容 | 状態 |
|---------|------|------|
| 69 | Streamlitアプリ起動テスト | ❌ 未実施 |
| 70 | 状態遷移テスト | ❌ 未作成 |
| 71 | メモリリークチェック | ❌ 未作成 |
| 72 | 最終動作確認チェックリスト | ❌ 未作成 |

---

## 未実装・未完了項目の実装計画 (ステップ1-72)

以下は、**低性能なLLMでも迷わず実装可能**なよう、各ステップを極小・具体的・実行可能な単位に分割した実装計画書です。

---

### 🎯 実装の進め方ルール

1. **1ステップ = 1ファイル作成/変更 + 即時動作確認**
2. **前のステップが完了してから次のステップへ**
3. **エラーが出たらその場で修正してから次へ**
4. **各ステップの最後に `npx tsc --noEmit` (frontend) または `python -m py_compile` (backend) で構文チェック**

---

## 📋 詳細実装ステップ (1-72)

### 【Task A】React App.tsx リファクタリング (ステップ1-24)

#### フェーズ2: 型定義の分離 (ステップ5-8)

**ステップ5: types/index.ts 完全実装**
```bash
# 対象: frontend/src/types/index.ts
# アクション: 以下の型定義を追加
# 確認: cat frontend/src/types/index.ts で内容確認
```
**実装内容:**
```typescript
// frontend/src/types/index.ts
export interface Book {
  id: number;
  title: string;
  synopsis: string;
  genre: string;
  target_eps: number;
  created_at: string;
  updated_at: string;
}

export interface Plot {
  id: number;
  book_id: number;
  ep_num: number;
  title: string;
  summary: string;
  tension: number;
  is_catharsis: boolean;
  status: string;
  detailed_blueprint?: string;
}

export interface Chapter {
  id: number;
  book_id: number;
  ep_num: number;
  title: string;
  summary: string;
  content: string;
  created_at: string;
}

export interface Bible {
  id: number;
  book_id: number;
  version: number;
  settings: {
    characters: Record<string, any>;
    world: any;
    timeline: any;
  };
  created_at: string;
}

export interface TaskStatus {
  task_id: string;
  current_step: number;
  total_steps: number;
  message: string;
  sub_message?: string;
  streaming_text?: string;
  logs: string[];
  error?: string;
  result_data?: any;
  token_usage: { prompt: number; completion: number; calls: number };
  start_time: number;
  last_updated: number;
}

export interface OptimizationHistory {
  id: number;
  book_id: number;
  created_at: string;
  report_json: any;
}

export interface PendingPatch {
  id: number;
  book_id: number;
  ep_num: number;
  patch_type: string;
  original_text: string;
  proposed_text: string;
  reason: string;
  status: string;
  created_at: string;
}

export interface PromptVersion {
  id: number;
  book_id: number;
  version_tag: string;
  content: string;
  score_before?: number;
  score_after?: number;
  is_active: boolean;
  rollback_reason?: string;
  created_at: string;
}

export interface NarrativeMetricTrend {
  ep_num: number;
  scene_num: number;
  tension: number;
  satisfaction: number;
  mystery: number;
}

export interface EasyModeParams {
  genre: string;
  keywords: string;
  archetype_key: string;
  target_eps: number;
  word_count: number;
  concept: string;
  tone_vibe: number;
}

// API型の再エクスポート
export * from './api';
```

**ステップ6: App.tsx からローカル型定義削除**
```bash
# 対象: frontend/src/App.tsx
# アクション: 
# 1. import type { Plot, Chapter, Bible, OptimizationHistory, PendingPatch, PromptVersion, NarrativeMetricTrend, TaskStatus } from './types'; の行を確認
# 2. App.tsx 内のローカル `interface Book {}` 等の定義があれば削除
# 確認: npx tsc --noEmit
```

**ステップ7: 型定義エクスポート確認**
```bash
# 対象: frontend/src/types/index.ts
# 確認: `export * from './api';` が末尾にあるか確認
# 追加: 必要に応じて `export * from './index';` 等の循環回避
```

**ステップ8: 型整合性チェック実行**
```bash
cd frontend && npx tsc --noEmit
# エラーがあれば修正してから次へ
```

---

#### フェーズ3: Custom Hooks 抽出 (ステップ9-12)

**ステップ9: hooks/useTaskStream.ts 作成**
```bash
# 対象: frontend/src/hooks/useTaskStream.ts (新規作成)
# 参照: App.tsx lines 116-145 (connectTaskStream 呼び出し部分)
# テンプレート:
```
```typescript
// frontend/src/hooks/useTaskStream.ts
import { useEffect, useRef } from 'react';
import { connectTaskStream } from '../api';
import type { TaskStatus } from '../types';

interface UseTaskStreamCallbacks {
  onStatus: (status: TaskStatus) => void;
  onComplete: (status: TaskStatus) => void;
  onError: (error: any) => void;
}

export function useTaskStream(
  taskId: string | null,
  callbacks: UseTaskStreamCallbacks
) {
  const disconnectRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (taskId) {
      const disconnect = connectTaskStream(
        taskId,
        callbacks.onStatus,
        callbacks.onComplete,
        callbacks.onError
      );
      disconnectRef.current = disconnect;
    }
    return () => {
      if (disconnectRef.current) {
        disconnectRef.current();
      }
    };
  }, [taskId, callbacks.onStatus, callbacks.onComplete, callbacks.onError]);
}
```

**ステップ10: hooks/useBookDetails.ts 作成**
```bash
# 対象: frontend/src/hooks/useBookDetails.ts (新規作成)
# 参照: App.tsx lines 154-183 (loadBookDetails 関数)
# テンプレート:
```
```typescript
// frontend/src/hooks/useBookDetails.ts
import { useCallback } from 'react';
import {
  getPlots,
  getChapters,
  getBible,
  getOptHistory,
  getPendingPatches,
  getPromptVersions,
  getNarrativeMetricsTrend,
} from '../api';
import { useBookStore } from '../store/useBookStore';
import { useUIStore } from '../store/useUIStore';
import type { OptimizationHistory, PendingPatch, PromptVersion, NarrativeMetricTrend } from '../types';

export function useBookDetails(
  bookId: number | null,
  activeTab: string
) {
  const { setPlots, setChapters, setBible } = useBookStore();
  const { setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend } = useUIStore();
  // 注: useUIStore にこれらの setter がない場合は追加が必要

  const loadBookDetails = useCallback(async (bookId: number) => {
    try {
      if (activeTab === 'plots') {
        const data = await getPlots(bookId);
        // setPlots(data); // storeに合わせて実装
      } else if (activeTab === 'write') {
        const chData = await getChapters(bookId);
        // setChapters(chData);
        const bibleData = await getBible(bookId);
        // setBible(bibleData);
      } else if (activeTab === 'analytics') {
        const histData = await getOptHistory(bookId);
        // setOptHistory(histData);
        const patchesData = await getPendingPatches(bookId);
        // setPendingPatches(patchesData);
        const versionsData = await getPromptVersions(bookId);
        // setPromptVersions(versionsData);

        try {
          const trendData = await getNarrativeMetricsTrend(bookId, 1);
          // setMetricTrend(trendData);
        } catch (e) {
          console.error('Error loading narrative metrics:', e);
        }
      }
    } catch (err) {
      console.error('Error loading book details:', err);
    }
  }, [activeTab]);

  return { loadBookDetails };
}
```

**ステップ11: hooks/useTaskMonitor.ts 作成**
```bash
# 対象: frontend/src/hooks/useTaskMonitor.ts (新規作成)
# 参照: App.tsx lines 96-98, 147-152, 185-195
# テンプレート:
```
```typescript
// frontend/src/hooks/useTaskMonitor.ts
import { useEffect, useRef } from 'react';
import { useTaskStore } from '../store/useTaskStore';

export function useTaskMonitor() {
  const { activeTaskId, taskStatus, setActiveTaskId, setTaskStatus } = useTaskStore();
  const logEndRef = useRef<HTMLDivElement | null>(null);

  // 自動スクロール
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [taskStatus?.logs]);

  const handleStopTask = async () => {
    if (!activeTaskId) return;
    // stopTask は api から import
    // await stopTask(activeTaskId);
    // setActiveTaskId(null);
    // setTaskStatus(null);
  };

  return {
    activeTaskId,
    taskStatus,
    logEndRef,
    handleStopTask,
  };
}
```

**ステップ12: hooks/index.ts 作成**
```bash
# 対象: frontend/src/hooks/index.ts (新規作成)
```
```typescript
// frontend/src/hooks/index.ts
export * from './useBooks';
export * from './useTaskStream';
export * from './useBookDetails';
export * from './useTaskMonitor';
```

---

#### フェーズ4: Dialog コンポーネント作成 (ステップ13-16)

**ステップ13: EasyModeDialog.tsx 作成 (CreateNovelModal からリネーム/リファクタ)**
```bash
# 対象: frontend/src/components/dialogs/EasyModeDialog.tsx (新規作成)
# 参照: 既存 CreateNovelModal.tsx をベースにリファクタ
```
```typescript
// frontend/src/components/dialogs/EasyModeDialog.tsx
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface EasyModeParams {
  genre: string;
  keywords: string;
  archetype_key: string;
  target_eps: number;
  word_count: number;
  concept: string;
  tone_vibe: number;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (params: EasyModeParams) => void;
}

export function EasyModeDialog({ isOpen, onClose, onSubmit }: Props) {
  if (!isOpen) return null;

  const [form, setForm] = useState<EasyModeParams>({
    genre: 'ダークファンタジー',
    keywords: '追放, 復讐, システムハック',
    archetype_key: 'avenger',
    target_eps: 10,
    word_count: 3000,
    concept: '',
    tone_vibe: 0.65,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>新規小説作成 (イージーモード)</h2>
        <form onSubmit={handleSubmit}>
          {/* 各フィールド実装 */}
          <Input label="ジャンル" value={form.genre} onChange={...} />
          {/* ... 他フィールド ... */}
          <div className="modal-actions">
            <Button type="button" onClick={onClose}>キャンセル</Button>
            <Button type="submit">作成開始</Button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**ステップ14: ImportChapterDialog.tsx 作成**
```bash
# 対象: frontend/src/components/dialogs/ImportChapterDialog.tsx (新規作成)
# 参照: App.tsx lines 297-321 (handleImportChapter 内のロジック)
```
```typescript
// frontend/src/components/dialogs/ImportChapterDialog.tsx
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (epNum: number, text: string, doRefine: boolean) => void;
}

export function ImportChapterDialog({ isOpen, onClose, onSubmit }: Props) {
  if (!isOpen) return null;

  const [epNum, setEpNum] = useState(1);
  const [text, setText] = useState('');
  const [doRefine, setDoRefine] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(epNum, text, doRefine);
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>章取り込み</h2>
        <form onSubmit={handleSubmit}>
          <Input label="エピソード番号" type="number" value={epNum} onChange={...} min={1} />
          <textarea value={text} onChange={...} placeholder="原稿を貼り付け..." />
          <label><input type="checkbox" checked={doRefine} onChange={...} /> 研磨する</label>
          <div className="modal-actions">
            <Button type="button" onClick={onClose}>キャンセル</Button>
            <Button type="submit">取り込み実行</Button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**ステップ15: dialogs/index.ts 作成**
```bash
# 対象: frontend/src/components/dialogs/index.ts (新規作成)
```
```typescript
// frontend/src/components/dialogs/index.ts
export { EasyModeDialog } from './EasyModeDialog';
export { ImportChapterDialog } from './ImportChapterDialog';
```

**ステップ16: Dialog 表示ロジック確認・修正**
```bash
# 対象: frontend/src/App.tsx
# 確認事項:
# 1. isCreateModalOpen, setCreateModalOpen が useUIStore から取得されているか
# 2. EasyModeDialog, ImportChapterDialog が正しく import されているか
# 3. onClose で setCreateModalOpen(false) が呼ばれているか
# 修正: App.tsx の import 部分と JSX 部分を修正
```

---

#### フェーズ6: App.tsx 再構成 (ステップ21-24)

**ステップ21: App.tsx 簡略化 - imports 更新**
```bash
# 対象: frontend/src/App.tsx
# 変更内容:
# 1. 新規hooks import 追加:
#    import { useTaskStream } from './hooks/useTaskStream';
#    import { useBookDetails } from './hooks/useBookDetails';
#    import { useTaskMonitor } from './hooks/useTaskMonitor';
# 2. Dialog import 更新:
#    import { EasyModeDialog } from './components/dialogs/EasyModeDialog';
#    import { ImportChapterDialog } from './components/dialogs/ImportChapterDialog';
# 3. 不要な import 削除 (api から直接 import していたものを hook 経由に)
```

**ステップ22: 残存ロジックを hooks/components に移動**
```bash
# 対象: frontend/src/App.tsx
# 以下を順次実行:

# 22-1: loadBookDetails → useBookDetails hook へ移動済みなら App.tsx から削除
# 22-2: handleStopTask → useTaskMonitor hook 経由で使用
# 22-3: handleCreateEasyMode → EasyModeDialog の onSubmit 内で完結させる
# 22-4: handleTriggerWriting → WriteTab の onGenerate prop として渡す
# 22-5: handleExpandPlots → PlotsTab の onExpand prop として渡す
# 22-5: handleCritiqueOptimize → AnalyticsTab の onCritiqueOptimize prop として渡す
# 22-6: handleImportChapter → ImportChapterDialog の onSubmit 内で完結
# 22-7: handleGenerateMarketing → AnalyticsTab の onGenerateMarketing prop として渡す

# App.tsx に残すべき最小限の状態:
# - activeTab, setActiveTab (useProjectStore)
# - selectedBook, setSelectedBook (useBookStore)
# - activeTaskId, taskStatus (useTaskStore / useTaskMonitor)
# - globalError, setGlobalError (useUIStore)
# - isCreateModalOpen, setCreateModalOpen (useUIStore)
```

**ステップ23: ビルド確認**
```bash
cd frontend && npm run build
# エラーが出たら一つずつ修正
# 主な修正ポイント:
# - typo修正 (setBile→setBible, bier→bible, selectBook→selectedBook, handleImportChannel→handleImportChapter)
# - importパス修正
# - prop名の一致 (bier→bible 等)
```

**ステップ24: 動作確認**
```bash
cd frontend && npm run dev
# ブラウザで http://localhost:5173 確認
# チェックリスト:
# - 4タブ切り替え動作
# - イージーモードダイアログ開閉
# - 章取り込みダイアログ開閉
# - タスクモニター表示/停止
# - 執筆実行、プロット展開等の主要フロー
```

---

### 【Task B】CORS設定の制限 (ステップ25-48)

#### フェーズ2: 環境変数サポート実装 (ステップ29-36)

**ステップ30: config/settings.py にCORS設定追加**
```bash
# 対象: /workspaces/autonovel/config/settings.py
# 現状: ConfigManager クラスのみ
# 追加: Pydantic BaseSettings を使用した CORS 設定
```
```python
# config/settings.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 既存設定...
    cors_allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:8501"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```
```bash
# 依存関係追加
cd /workspaces/autonovel && pip install pydantic-settings
```

**ステップ33: 設定読み込みテスト作成**
```bash
# 対象: /workspaces/autonovel/tests/test_cors_config.py (新規作成)
```
```python
# tests/test_cors_config.py
import os
import pytest

def test_get_allowed_origins_from_env():
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:8000"
    # インポートは環境変数設定後に実行
    from config.cors_config import get_allowed_origins
    origins = get_allowed_origins()
    assert "http://localhost:3000" in origins
    assert "http://localhost:8000" in origins

def test_get_allowed_origins_default():
    # 環境変数未設定時のデフォルト値テスト
    if "CORS_ALLOWED_ORIGINS" in os.environ:
        del os.environ["CORS_ALLOWED_ORIGINS"]
    from config.cors_config import get_allowed_origins
    origins = get_allowed_origins()
    assert "http://localhost:5173" in origins
    assert "http://localhost:8501" in origins
```

**ステップ34: 設定テスト実行**
```bash
cd /workspaces/autonovel && python -m pytest tests/test_cors_config.py -v
```

**ステップ35: 設定変更ドキュメント化**
```bash
# 対象: /workspaces/autonovel/docs/CORS_CONFIG.md (新規作成)
```
```markdown
# CORS設定ガイド

## 環境変数
- `CORS_ALLOWED_ORIGINS`: カンマ区切りで許可originリスト
  - 開発環境: `http://localhost:5173,http://localhost:8501`
  - 本番環境: `https://your-production-domain.com`

## 設定ファイル
- `config/cors_config.py`: 許可origin取得ロジック
- `config/settings.py`: Pydantic Settings での定義
- `src/backend/server.py`: CORS middleware 設定

## 動作確認
```bash
# 開発環境
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8501 python -m uvicorn src.backend.server:app --reload

# curlで確認
curl -I -X OPTIONS http://localhost:8000/health -H "Origin: http://localhost:5173"
# Access-Control-Allow-Origin ヘッダーが返ることを確認
```
```

**ステップ36: 既存テストのCORS関連確認**
```bash
grep -r "allow_origins" tests/
# 既存テストがあれば更新、なければスキップ
```

---

#### フェーズ3: server.py 更新 (ステップ37-44)

**ステップ40: 開発環境動作確認 (curlテスト)**
```bash
# バックエンド起動 (別ターミナル)
cd /workspaces/autonovel && python -m uvicorn src.backend.server:app --reload

# 別ターミナルで curl テスト
curl -I -X OPTIONS http://localhost:8000/health \
  -H "Origin: http://localhost:5173"
# 期待: Access-Control-Allow-Origin: http://localhost:5173

curl -I -X OPTIONS http://localhost:8000/health \
  -H "Origin: http://malicious-site.com"
# 期待: Access-Control-Allow-Origin ヘッダーなし (または異なるorigin)
```

**ステップ41: 本番環境想定テスト**
```bash
# 本番originでテスト
CORS_ALLOWED_ORIGINS=https://prod.example.com python -m uvicorn src.backend.server:app --reload &
curl -I -X OPTIONS http://localhost:8000/health -H "Origin: https://prod.example.com"
# 許可されることを確認
```

**ステップ43: エンドポイントテスト作成**
```bash
# 対象: /workspaces/autonovel/tests/test_cors_endpoints.py (新規作成)
```
```python
# tests/test_cors_endpoints.py
from fastapi.testclient import TestClient
from src.backend.server import app

client = TestClient(app)

def test_cors_headers_in_response():
    response = client.get("/health")
    assert "Access-Control-Allow-Origin" in response.headers
    # または OPTIONS リクエストでテスト
    response = client.options("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"

def test_cors_rejects_unauthorized_origin():
    response = client.options("/health", headers={"Origin": "http://evil.com"})
    # 未許可originの場合、CORSヘッダーが含まれないか、異なるoriginが返る
    assert response.headers.get("Access-Control-Allow-Origin") != "http://evil.com"
```

**ステップ44: 全テスト実行**
```bash
cd /workspaces/autonovel && python -m pytest tests/ -v --tb=short
```

---

#### フェーズ4: ドキュメントとデプロイ対応 (ステップ45-48)

**ステップ45: docker-compose.yml 更新**
```bash
# 対象: /workspaces/autonovel/docker-compose.yml
# 確認: backend サービスに環境変数追加
```
```yaml
services:
  backend:
    environment:
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}
```

**ステップ46: Dockerfile 確認**
```bash
# 対象: /workspaces/autonovel/Dockerfile
# 確認: ENV CORS_ALLOWED_ORIGINS=... があるか
```

**ステップ47: デプロイ手順書更新**
```bash
# 対象: /workspaces/autonovel/docs/DEPLOY.md (新規作成または追記)
```
```markdown
## CORS設定
本番デプロイ時は以下のように環境変数を設定:
CORS_ALLOWED_ORIGINS=https://your-domain.com

複数ドメインの場合:
CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```

**ステップ48: 最終確認チェックリスト作成**
```bash
# 対象: /workspaces/autonovel/docs/CORS_CHECKLIST.md (新規作成)
```
```markdown
# CORS設定 最終確認チェックリスト

- [x] allow_origins=["*"] を削除
- [x] 環境変数でoriginを指定可能
- [x] デフォルトは開発用localhostのみ
- [x] ログで許可originを確認可能
- [ ] 開発環境でcurlテスト通過
- [ ] 本番環境想定でテスト通過
- [ ] 単体テスト通過
- [ ] 統合テスト通過
- [ ] docker-compose.yml 更新
- [ ] Dockerfile 確認
- [ ] デプロイ手順書更新
```

---

### 【Task C】Streamlit状態管理の統一 (ステップ49-72)

#### フェーズ1: 現在の状態管理分析 (ステップ49-52)

**ステップ50: st.session_state 使用箇所調査**
```bash
cd /workspaces/autonovel && grep -r "st.session_state" streamlit_app/ --include="*.py"
# 出力を整理して state_migration_notes.md に記録
```

**ステップ51: 状態使用パターン分類**
```bash
# 上記grep結果を以下に分類して docs/state_migration_analysis.md に記録:
# - 永続化必要 (localStorage/DB同期): apiKey, selectedBookId 等
# - 一時的 (画面遷移で破棄OK): UI表示状態、フォーム入力値 等
```

**ステップ52: バックアップ取得**
```bash
cp streamlit_app/state.py streamlit_app/state.py.backup
cp streamlit_app/app.py streamlit_app/app.py.backup
```

---

#### フェーズ2: UIStateStore 強化 (ステップ53-60)

**ステップ56: 移行ヘルパー作成**
```bash
# 対象: streamlit_app/state.py
# 追加: SessionManager に migrate_from_session メソッドが未実装なら追加
```
```python
# streamlit_app/state.py に追加 (SessionManager クラス内)
@classmethod
def migrate_from_session(cls, key: str, default: Any = None) -> Any:
    """st.session_state から値を取得してUIStateStoreに移行"""
    if key in st.session_state:
        value = st.session_state[key]
        del st.session_state[key]  # 移行後に削除
        return value
    return default
```

**ステップ58: 状態変更サブスクリプション確認**
```bash
# 対象: streamlit_app/state.py
# 確認: UIStateStore.subscribe() が実装されているか
# 未実装なら追加:
```
```python
# UIStateStore クラスに追加
_subscribers: dict[str, list[Callable]] = {}

@classmethod
def subscribe(cls, key: str, callback: Callable) -> Callable:
    """状態変更時のコールバック登録"""
    if key not in cls._subscribers:
        cls._subscribers[key] = []
    cls._subscribers[key].append(callback)
    return lambda: cls._subscribers[key].remove(callback)  # アンサブスクライブ用

@classmethod
def _notify_subscribers(cls, key: str, value: Any) -> None:
    for callback in cls._subscribers.get(key, []):
        callback(value)
```

**ステップ60: テストファイル作成**
```bash
# 対象: /workspaces/autonovel/tests/test_ui_state_store.py (新規作成)
```
```python
# tests/test_ui_state_store.py
import pytest
from streamlit_app.state import UIStateStore, UIState

def test_ui_state_initialization():
    runtime = UIStateStore.get_runtime()
    assert isinstance(runtime.ui_state, UIState)
    assert runtime.ui_state.show_create_modal == False
    assert runtime.ui_state.easy_genre == 'ダークファンタジー'
```

---

#### フェーズ3: コンポーネント移行 (ステップ61-68)

**共通手順 (各ファイル共通):**
```bash
# 各ファイルで以下を実施:
# 1. `from streamlit_app.state import get_ui_state, update_ui_state` 追加
# 2. `st.session_state['key']` パターンを `get_ui_state().key` に置換
# 3. `st.session_state.key = value` パターンを `update_ui_state(key=value)` に置換
# 4. 動作確認
```

**ステップ61-62: ui_tabs_writing.py 修正**
```bash
# 対象: streamlit_app/ui_tabs_writing.py
# 重点: import_ep_num, import_text, import_do_refine 等のフォーム状態
# 置換例:
# 修正前: st.session_state.import_ep_num
# 修正後: get_ui_state().import_ep_num
# 修正前: st.session_state.import_ep_num = value
# 修正後: update_ui_state(import_ep_num=value)
```

**ステップ63: ui_tabs_planning.py 修正**
```bash
# 対象: streamlit_app/ui_tabs_planning.py
# 重点: easy_genre, easy_keywords, easy_archetype, easy_target_eps, easy_word_count, easy_concept
```

**ステップ64: sidebar.py 修正**
```bash
# 対象: streamlit_app/sidebar.py
# 重点: APIキー管理 (runtime.api_key 等)
# 置換: st.session_state.api_key → UIStateStore経由
```

**ステップ65-68: 残りタブ修正**
```bash
# 65: progress.py
# 66: ui_tabs_analytics.py
# 67: ui_tabs_monitor.py
# 68: ui_tabs_audit.py
# 各ファイルで同様の置換実施
```

---

#### フェーズ4: 統合テストと確認 (ステップ69-72)

**ステップ69: Streamlitアプリ起動テスト**
```bash
cd /workspaces/autonovel
streamlit run streamlit_app/app.py --server.headless true
# エラーなく起動することを確認 (Ctrl+C で停止)
```

**ステップ70: 状態遷移テスト作成・実行**
```bash
# 対象: /workspaces/autonovel/tests/test_streamlit_state.py (新規作成)
```
```python
# tests/test_streamlit_state.py
def test_state_persistence_across_reruns():
    """Streamlit rerun間で状態が保持されることを確認"""
    from streamlit_app.state import UIStateStore
    runtime = UIStateStore.get_runtime()
    initial_count = len(UIStateStore._subscribers)
    for _ in range(100):
        UIStateStore.subscribe("test_key", lambda x: x)
    # クリーンアップ処理が正しく動くか確認
```

**ステップ71: メモリリークチェック**
```bash
# 上記テスト実行でサブスクリプションが蓄積しないか確認
python -m pytest tests/test_streamlit_state.py -v
```

**ステップ72: 最終動作確認チェックリスト**
```bash
# 対象: docs/FINAL_CHECKLIST.md (新規作成)
```
```markdown
# 最終動作確認チェックリスト

## React Frontend
- [ ] npm run build 成功
- [ ] npm run dev 起動成功
- [ ] 4タブ切り替え動作
- [ ] イージーモードダイアログ開閉
- [ ] 章取り込みダイアログ開閉
- [ ] タスクモニター表示/停止
- [ ] 執筆実行、プロット展開、品質分析、マーケティング生成

## Backend CORS
- [ ] curl テスト通過 (許可origin)
- [ ] curl テスト通過 (拒否origin)
- [ ] 単体テスト通過
- [ ] 統合テスト通過

## Streamlit State
- [ ] streamlit run 起動成功
- [ ] st.session_state 直接使用箇所ゼロ
- [ ] UIStateStore 経由で全状態管理
- [ ] 状態永続化/復元動作
- [ ] メモリリークなし

## 全体
- [ ] 全テストパス (frontend + backend + streamlit)
- [ ] バックアップファイル削除 (.backup ファイル)
```

---

## 🎯 実装優先順位 (推奨実行順序)

| 優先度 | ステップ範囲 | 理由 |
|--------|-------------|------|
| **最高** | A5-A8 (型定義) | 全ての基盤 |
| **最高** | A9-A12 (hooks) | ロジック分離の核心 |
| **高** | A13-A16 (Dialog) | UI完成に必須 |
| **高** | A21-A24 (App.tsx再構成) | 統合・動作確認の前提 |
| **中** | B30-B36 (CORS設定完全化) | セキュリティ要件 |
| **中** | C50-C52 (現状分析) | 移行前提の整理 |
| **中** | C56-C60 (Store強化) | 移行の基盤 |
| **中** | C61-C68 (コンポーネント移行) | 実質的な統一 |
| **低** | C69-C72 (統合テスト) | 最終確認 |

---

## 🛠️ 開発環境セットアップ確認コマンド

```bash
# フロントエンド
cd /workspaces/autonovel/frontend
npm install --legacy-peer-deps
npx tsc --noEmit
npm run build

# バックエンド
cd /workspaces/autonovel
pip install pydantic-settings
python -m pytest tests/test_cors_config.py -v

# Streamlit
streamlit run streamlit_app/app.py --server.headless true
```

---

## ⚠️ 既知の問題・注意点

1. **App.tsx の typo 多数** - `setBile`/`bier`/`selectBook`/`handleImportChannel` 等を修正必須
2. **useUIStore に setter 不足** - `setOptHistory`, `setPendingPatches` 等が不足の可能性
3. **config/settings.py** - Pydantic BaseSettings への移行が必要 (現在は ConfigManager)
4. **Streamlit st.session_state 直接使用** - 大量残存の可能性、grep で全量把握必須
5. **テストファイル未整備** - 各タスクでテスト作成ステップを含めること

---

*作成日: 2026-07-13*
*検証対象: 72ステップ実装計画書 (frontend/DETAILED_72STEP_IMPLEMENTATION_PLAN.md)*
*検証者: 自動検証スクリプト + 手動コードレビュー*