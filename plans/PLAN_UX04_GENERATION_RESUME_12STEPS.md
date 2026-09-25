# AutoNovel UX改善計画: 生成を「中断・部分保持・再開」へ配線 (全12ステップ)

**対象**: #6 生成の中断・部分保持・再開
**目的**: ストリーミング生成の停止・部分出力保持・再試行を UI 完結で実現
**前提**: 既存 `GeneratePanel.tsx:260-265` (ハンドラ実装済み)・`SimpleModePanel.tsx:144-174` (停止ボタン非対応)・`useStreamingWriter.ts:62-94` (リトライ実装済み)・`useStreamingWriter.ts:187-200` (失敗時クリア)

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Type | `src/types/generation.ts` | [NEW] 生成状態・部分出力・制御コマンドの型定義 |
| **Step 2** | Hook | `src/hooks/useGenerationControl.ts` | [NEW] 開始/停止/一時停止/再開/部分保持の統合制御フック |
| **Step 3** | Modify | `src/hooks/useStreamingWriter.ts` | [MODIFY] 部分出力保持・停止フラグ・再開ポイント対応 |
| **Step 4** | Component | `src/components/generate/GenerationStatusBar.tsx` | [NEW] 接続状態・進捗・部分文字数・リトライ回数表示バー |
| **Step 5** | Component | `src/components/generate/PartialOutputPanel.tsx` | [NEW] 失敗時の部分出力表示・保持/破棄/再試行三択 UI |
| **Step 6** | Modify | `src/components/generate/SimpleModePanel.tsx` | [MODIFY] 停止ボタンをストリーム対応化、生成中 UI 差し替え |
| **Step 7** | Modify | `src/components/GeneratePanel.tsx` | [MODIFY] 既存ハンドラをフック経由に、状態同期 |
| **Step 8** | Modify | `src/components/generate/AdvancedModePanel.tsx` | [MODIFY] (存在する場合) 同等の制御導線追加 |
| **Step 9** | Persist | `src/utils/generationPersist.ts` | [NEW] 部分出力・状態を IndexedDB 保存・復元 (ページ離脱対策) |
| **Step 10** | Modify | `src/hooks/useGenerationControl.ts` | [MODIFY] マウント時自動復元・ページ離脱前保存統合 |
| **Step 11** | Test | `tests/unit/hooks/useGenerationControl.test.ts` | [NEW] 制御フック・状態遷移・永続化統合テスト |
| **Step 12** | E2E | `tests/e2e/generation_resume.test.ts` | [NEW] Playwright: 生成→停止→部分保持→再開→完了/失敗→三択の全フロー |

---

## 🛠️ 各ステップ詳細手順

### Step 1: 型定義
- **対象ファイル**: `src/types/generation.ts` (新規作成)
- **実装内容**:
```typescript
export type GenerationPhase = 'idle' | 'connecting' | 'streaming' | 'paused' | 'stopped' | 'completed' | 'failed';

export interface GenerationState {
  phase: GenerationPhase;
  accumulatedText: string;      // これまでに受信した全テキスト
  currentChunk: string;         // 現在受信中のチャンク (表示用)
  totalChars: number;
  totalTokens: number;
  startTime: number;
  lastChunkTime: number;
  retryCount: number;
  error?: string;
  // 停止・一時停止制御
  abortController?: AbortController;
  isPaused: boolean;
  pausePosition: number;        // 累積文字数での一時停止位置
}

export interface GenerationControls {
  start: (params: GenerationParams) => Promise<void>;
  stop: () => void;             // 完全停止・破棄
  pause: () => void;            // 一時停止 (再開可能)
  resume: () => void;           // 再開
  keepDraft: () => void;        // 部分出力を下書き保存
  discardDraft: () => void;     // 破棄
  retry: () => void;            // 最初から再試行
}

export interface GenerationParams {
  bookId: string;
  chapterId: string;
  prompt: string;
  modelConfig: ModelConfig;
  onChunk: (chunk: string) => void;
  onComplete: (fullText: string) => void;
  onError: (error: Error) => void;
}
```
- **検証コマンド**: `npx tsc --noEmit --skipLibCheck src/types/generation.ts`
- **期待結果**: 型エラーなし

---

### Step 2: 統合制御フック
- **対象ファイル**: `src/hooks/useGenerationControl.ts` (新規作成)
- **実装内容**:
```typescript
import { useState, useCallback, useRef, useEffect } from 'react';
import { GenerationState, GenerationControls, GenerationParams, GenerationPhase } from '../types/generation';
import { useStreamingWriter } from './useStreamingWriter';
import { saveGenerationState, loadGenerationState, clearGenerationState } from '../utils/generationPersist';

export function useGenerationControl(): [GenerationState, GenerationControls] {
  const [state, setState] = useState<GenerationState>({
    phase: 'idle',
    accumulatedText: '',
    currentChunk: '',
    totalChars: 0,
    totalTokens: 0,
    startTime: 0,
    lastChunkTime: 0,
    retryCount: 0,
    isPaused: false,
    pausePosition: 0,
  });

  const { writeStream, abort, reset } = useStreamingWriter({
    onChunk: (chunk) => setState(s => ({
      ...s,
      accumulatedText: s.accumulatedText + chunk,
      currentChunk: chunk,
      totalChars: s.totalChars + chunk.length,
      lastChunkTime: Date.now(),
    })),
    onComplete: (fullText) => setState(s => ({ ...s, phase: 'completed', currentChunk: '' })),
    onError: (error) => setState(s => ({ ...s, phase: 'failed', error: error.message })),
    onRetry: (count) => setState(s => ({ ...s, retryCount: count, phase: 'connecting' })),
  });

  // 定期保存 (5秒ごと・ストリーミング中のみ)
  useEffect(() => {
    if (state.phase !== 'streaming' && state.phase !== 'paused') return;
    const id = setInterval(() => saveGenerationState(state), 5000);
    return () => clearInterval(id);
  }, [state]);

  const start = useCallback(async (params: GenerationParams) => {
    const restored = loadGenerationState();
    if (restored && restored.phase === 'paused') {
      // 一時停止からの再開
      setState({ ...restored, phase: 'streaming', isPaused: false });
      await writeStream(params, restored.pausePosition);
    } else {
      // 新規開始
      const controller = new AbortController();
      setState({
        phase: 'connecting',
        accumulatedText: '',
        currentChunk: '',
        totalChars: 0,
        totalTokens: 0,
        startTime: Date.now(),
        lastChunkTime: Date.now(),
        retryCount: 0,
        abortController: controller,
        isPaused: false,
        pausePosition: 0,
      });
      await writeStream(params, 0);
    }
  }, [writeStream]);

  const stop = useCallback(() => {
    abort();
    clearGenerationState();
    setState(s => ({ ...s, phase: 'stopped', isPaused: false }));
  }, [abort]);

  const pause = useCallback(() => {
    abort(); // ストリーム切断だが状態保持
    setState(s => ({ ...s, phase: 'paused', isPaused: true, pausePosition: s.totalChars }));
    saveGenerationState({ ...state, phase: 'paused', isPaused: true });
  }, [abort, state]);

  const resume = useCallback(() => {
    setState(s => ({ ...s, phase: 'connecting', isPaused: false }));
    // writeStream 内部で pausePosition から再開
  }, []);

  const keepDraft = useCallback(() => {
    saveGenerationState({ ...state, phase: 'stopped' });
    setState(s => ({ ...s, phase: 'stopped' }));
  }, [state]);

  const discardDraft = useCallback(() => {
    clearGenerationState();
    setState(s => ({ ...s, phase: 'idle', accumulatedText: '' }));
  }, []);

  const retry = useCallback(() => {
    clearGenerationState();
    setState(s => ({ ...s, phase: 'idle', accumulatedText: '', retryCount: 0 }));
    // 親コンポーネントで再度 start() 呼び出し
  }, []);

  return [state, { start, stop, pause, resume, keepDraft, discardDraft, retry }];
}
```
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/hooks/useGenerationControl.test.ts`
- **期待結果**: 状態遷移 (idle→connecting→streaming⇄paused→completed/failed/stopped) 正常

---

### Step 3: useStreamingWriter 部分出力保持対応
- **対象ファイル**: `src/hooks/useStreamingWriter.ts` (修正)
- **変更箇所**: L62-94 (リトライ)・L187-200 (失敗時クリア)
- **実装内容**:
  1. `writeStream` に `resumeFrom: number` 引数追加 (バイト/文字オフセット)
  2. サーバー側 API が `Range` ヘッダー対応済みなら `Range: bytes=X-` 送信、未対応なら全量再取得後ローカルでスキップ
  3. 失敗時 `accumulatedText` をクリアせず保持 (`onError` で phase='failed' へ)
  4. `AbortSignal` 受け取り `fetch` に渡し、`abort()` で即座切断
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 一時停止→再開で続きからストリーム再開、失敗時に累積テキスト保持

---

### Step 4: 生成ステータスバー
- **対象ファイル**: `src/components/generate/GenerationStatusBar.tsx` (新規作成)
- **実装内容**:
  - Props: `state: GenerationState`, `controls: GenerationControls`
  - 表示項目 (左→右):
    - フェーズバッジ: 接続中/ストリーミング中/一時停止/完了/失敗 (色分け)
    - 累積文字数: "12,345 字"
    - 推定トークン数: "≈ 3,200 tok"
    - 経過時間: "2分 14秒"
    - リトライ回数: "再試行 2 回" (retryCount > 0 時のみ)
    - 接続品質: 🟢/🟡/🔴 (lastChunkTime から 5秒以上途切れ→黄、30秒→赤)
  - アクションボタン (フェーズ別):
    - streaming: [一時停止] [停止]
    - paused: [再開] [停止して下書き保存] [破棄]
    - failed: [再試行] [下書き保存] [破棄]
    - completed: (完了表示のみ)
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/components/GenerationStatusBar.test.tsx`
- **期待結果**: 状態に応じた表示・ボタン切替、リアルタイム更新

---

### Step 5: 部分出力パネル (失敗時三択)
- **対象ファイル**: `src/components/generate/PartialOutputPanel.tsx` (新規作成)
- **実装内容**:
  - 表示条件: `state.phase === 'failed' || state.phase === 'stopped'` かつ `accumulatedText.length > 0`
  - UI:
    - ヘッダー: "生成が中断されました (12,345 字まで生成済み)"
    - プレビュー領域: 累積テキスト読み取り専用表示 (スクロール可)
    - 三択ボタン (等幅横並び):
      1. [下書きとして保存] → `keepDraft()` → エディタに反映 or IndexedDB 保存
      2. [再試行] → `retry()` → 最初から再生成
      3. [破棄] → `discardDraft()` → クリア
  - キーボード: 1/2/3 キーで選択、Enter で確定
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/components/PartialOutputPanel.test.tsx`
- **期待結果**: 失敗時に自動表示、三択すべて動作

---

### Step 6: SimpleModePanel ストリーム対応停止ボタン
- **対象ファイル**: `src/components/generate/SimpleModePanel.tsx` (修正)
- **変更箇所**: L144-174 (生成ボタン群)・L209-241 (部分テキスト表示)
- **実装内容**:
  1. `useGenerationControl` フック導入、既存生成ロジック置換
  2. 生成中: 「生成中…」+ [一時停止] [停止] ボタン表示
  3. 部分テキスト表示: `state.accumulatedText` 常時表示 (ストリーム中も完了後も)
  4. 完了時: 既存「完了」トースト + エディタ反映導線
  5. 失敗時: `PartialOutputPanel` 自動表示
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 従来「生成のみ」→「停止・一時停止・部分表示・失敗時三択」完全動作

---

### Step 7: GeneratePanel 既存ハンドラ統合
- **対象ファイル**: `src/components/GeneratePanel.tsx` (修正)
- **変更箇所**: L260-265 (ハンドラ渡し)
- **実装内容**:
  1. `useGenerationControl` フック導入、状態・制御を子パネルへ Props 渡し
  2. 既存 `onCancel`, `onPause`, `onResume` 削除 (フック内包)
  3. 高度モードパネル (存在すれば) にも同一制御オブジェクト渡し
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 親・子パネル間で生成状態完全同期

---

### Step 8: AdvancedModePanel 同等導線 (存在時)
- **対象ファイル**: `src/components/generate/AdvancedModePanel.tsx` (修正・存在確認後)
- **実装内容**: Step 6 と同等の制御導線追加。存在しない場合はスキップ。
- **検証コマンド**: `npm run typecheck` (ファイル存在時のみ)
- **期待結果**: 両モードで同一制御体験

---

### Step 9: IndexedDB 永続化ユーティリティ
- **対象ファイル**: `src/utils/generationPersist.ts` (新規作成)
- **実装内容**:
```typescript
import { GenerationState } from '../types/generation';

const DB_NAME = 'autonovel-generation';
const STORE_NAME = 'drafts';
const KEY = 'current-generation';

function getDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE_NAME);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function saveGenerationState(state: GenerationState): Promise<void> {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).put(state, KEY);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function loadGenerationState(): Promise<GenerationState | null> {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const req = tx.objectStore(STORE_NAME).get(KEY);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

export async function clearGenerationState(): Promise<void> {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).delete(KEY);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
```
- **検証コマンド**: `npm run test:ci -- tests/unit/utils/generationPersist.test.ts`
- **期待結果**: 保存・読み込み・削除動作、ページリロード後復元確認

---

### Step 10: フックへ永続化統合
- **対象ファイル**: `src/hooks/useGenerationControl.ts` (修正・Step 2 追加)
- **実装内容**: Step 2 実装時に `useEffect` マウント時に `loadGenerationState()` 実行、一時停止状態なら自動的に `paused` フェーズで復元し「再開」ボタン表示
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 生成中にブラウザリロード→再開ボタン表示→続きから生成再開

---

### Step 11: 制御フック統合テスト
- **対象ファイル**: `tests/unit/hooks/useGenerationControl.test.ts` (新規作成)
- **テストケース** (MSW でストリーミング API モック):
  1. 正常完了フロー: start→streaming(chunks)→completed
  2. 一時停止・再開: streaming→pause→paused→resume→streaming→completed
  3. 停止・下書き保存: streaming→stop→stopped (累積テキスト保持)
  4. 失敗・三択: streaming→error→failed→keepDraft/retry/discard
  5. リトライ: failed→retry→idle→start→streaming...
  6. ページリロード復元: save→unload→load→paused 状態復元
- **検証コマンド**: `npm run test:ci -- tests/unit/hooks/useGenerationControl.test.ts`
- **期待結果**: 全状態遷移・永続化経路パス

---

### Step 12: E2E 実操作確認
- **対象ファイル**: `tests/e2e/generation_resume.test.ts` (新規作成)
- **シナリオ** (Playwright):
  1. 簡易モードで長文生成開始 → 10秒後 [一時停止] → 累積文字数確認
  2. [再開] → 続きから生成継続 → 完了確認
  3. 生成中 [停止] → 部分出力パネル表示 → [下書き保存] → エディタ反映確認
  4. 生成中ネットワーク遮断 (DevTools) → 失敗検知 → 部分出力パネル → [再試行] → 完了
  5. 生成中ブラウザリロード (F5) → 再開ボタン表示 → 続きから生成
  6. 部分出力破棄 → 完全クリア確認
- **検証コマンド**: `npm run test:e2e -- tests/e2e/generation_resume.test.ts`
- **期待結果**: 全シナリオパス、ユーザー操作で中断・再開・部分保持が直感的動作

---

## 🔗 依存関係グラフ
```
Step 1 → Step 2 → Step 3
              ↓
         Step 4 → Step 5
              ↓
         Step 6 → Step 7 → Step 8
              ↓
         Step 9 → Step 10
              ↓
         Step 11 → Step 12
```

---

## ✅ 完了判定基準
1. 全 12 ステップ検証コマンド通過
2. 既存テストスイート ALL GREEN
3. 手動確認: 生成→一時停止→再開→完了 / 生成→停止→部分保持 / 生成→失敗→三択 / リロード復元
4. TypeScript 型チェック・Lint エラーなし
5. 既存 `useStreamingWriter` のリトライ機能 (指数バックオフ等) 損なわれていないこと

---

## 📝 備考
- サーバー側 `Range` 対応有無で再開方式分岐 (Step 3)。未対応時は全量再取得→ローカル skip で代用
- IndexedDB は `autonovel-generation` 専用 DB、既存 `autonovel.*` キー規約と分離
- `PartialOutputPanel` の「下書き保存」はエディタ反映 or 専用下書きストアへ。まずはエディタ反映 (既存 `setChapterContent` 等利用) で最小実装
- 簡易/高度モード両対応で統一 UX 実現