# AutoNovel UX改善計画: インライン推敲に Before/After 差分確認を再利用 (全12ステップ)

**対象**: #3 インライン推敲に DiffViewer 再利用・原文検証追加
**目的**: 推敲提案適用前に差分確認・原文一致検証で音声保護・誤適用防止
**前提**: 既存 `InlineAiToolbar.tsx:256-268` (推敲プレビュー)・`EditorialSidebar.tsx:456-461` / `DiffViewer.tsx:43-80` (整合性修正用差分UI実装済み)

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Type | `src/types/inlineRevision.ts` | [NEW] 推敲提案・差分・検証結果の型定義 |
| **Step 2** | Utility | `src/utils/textDiff.ts` | [NEW] 日本語文字レベル diff 算出 (DiffViewer 内部ロジック抽出・汎用化) |
| **Step 3** | Test | `tests/unit/utils/textDiff.test.ts` | [NEW] diff 関数単体テスト (挿入/削除/置換/ルビ含むケース) |
| **Step 4** | Hook | `src/hooks/useInlineRevision.ts` | [NEW] 推敲実行→差分生成→原文検証→適用の状態管理フック |
| **Step 5** | Component | `src/components/editor/InlineRevisionDiffModal.tsx` | [NEW] 推敲専用差分確認モーダル (DiffViewer 再利用・適用/却下/保留) |
| **Step 6** | Modify | `src/components/editor/InlineAiToolbar.tsx` | [MODIFY] 推敲実行フローをフック経由に変更、モーダル開く導線追加 |
| **Step 7** | Modify | `src/components/editor/Editor.tsx` | [MODIFY] ツールバーからの適用要求をフック経由に、選択範囲検証ロジック追加 |
| **Step 8** | Utility | `src/utils/selectionVerify.ts` | [NEW] 適用直前の選択範囲・原文一致検証関数 |
| **Step 9** | Modify | `src/components/editor/InlineRevisionDiffModal.tsx` | [MODIFY] 検証失敗時「原文が変更されています」警告・保留ボタン表示 |
| **Step 10** | Modify | `src/components/editor/DiffViewer.tsx` | [MODIFY] 日本語文字レベルハイライト対応 (既存行ベース→文字ベース拡張) |
| **Step 11** | Test | `tests/unit/components/InlineRevisionDiffModal.test.tsx` | [NEW] モーダル・フック・検証統合テスト |
| **Step 12** | E2E | `tests/e2e/inline_revision.test.ts` | [NEW] Playwright: 推敲→差分確認→検証成功/失敗・保留の全フロー |

---

## 🛠️ 各ステップ詳細手順

### Step 1: 型定義
- **対象ファイル**: `src/types/inlineRevision.ts` (新規作成)
- **実装内容**:
```typescript
export interface RevisionProposal {
  id: string;
  originalText: string;      // 選択されていた元テキスト (HTML含む)
  revisedText: string;       // AI生成推敲案 (HTML含む)
  instruction: string;       // "より感情的に" 等の指示
  timestamp: number;
  selectionRange: {          // 適用対象範囲 (Editor の contentEditable 内オフセット)
    start: number;
    end: number;
  };
}

export interface DiffSegment {
  type: 'equal' | 'insert' | 'delete' | 'replace';
  original: string;
  revised: string;
  // 文字レベル差分用 (replace の場合)
  charDiffs?: Array<{ char: string; type: 'equal' | 'insert' | 'delete' }>;
}

export interface RevisionVerificationResult {
  isMatch: boolean;
  mismatchReason?: 'textChanged' | 'rangeShifted' | 'contentMissing';
  currentTextAtRange: string;
  suggestion: 'apply' | 'reject' | 'hold';
}
```
- **検証コマンド**: `npx tsc --noEmit --skipLibCheck src/types/inlineRevision.ts`
- **期待結果**: 型エラーなし

---

### Step 2: 日本語文字レベル diff 算出
- **対象ファイル**: `src/utils/textDiff.ts` (新規作成)
- **実装内容**:
  - `DiffViewer.tsx` 内部の行ベース diff ロジックを参考に、文字ベース (grapheme cluster 単位) へ拡張
  - 依存: `graphemer` (Unicode グラフェムクラスタ分割) または自前実装
  - アルゴリズム: Myers diff / LCS ベースで文字単位操作列生成
  - 入力: `original: string`, `revised: string` (HTML タグ込み可・タグは不透明トークンとして扱う)
  - 出力: `DiffSegment[]` (Step 1 型)
  - ルビタグ `<ruby>漢<rt>かん</rt></ruby>` は 1 グラフェムとして扱うオプション付き
- **実装方針** (低性能 LLM 対応): `diff` パッケージ (npm) 使用せず、シンプルな LCS 実装で依存ゼロ
```typescript
// シンプル LCS ベース文字 diff (擬似コード)
function charDiff(original: string, revised: string): DiffSegment[] {
  const oChars = [...original]; // graphemer 使用推奨
  const rChars = [...revised];
  // LCS 表構築 → 操作列復元 → セグメント化
}
```
- **検証コマンド**: `npm run test:ci -- tests/unit/utils/textDiff.test.ts`
- **期待結果**: 基本挿入・削除・置換・ルビ含むケースで正確なセグメント生成

---

### Step 3: diff 単体テスト
- **対象ファイル**: `tests/unit/utils/textDiff.test.ts` (新規作成)
- **テストケース**:
  1. 同一文字列 → `[{type:'equal', original:'abc', revised:'abc'}]`
  2. 単純置換: "吾輩は猫" → "吾輩は犬" → replace セグメント (猫→犬)
  3. 挿入: "吾輩は猫" → "吾輩は確かに猫" → insert "確かに"
  4. 削除: "吾輩は確かに猫" → "吾輩は猫" → delete "確かに"
  5. ルビタグ含む: `<ruby>薔薇<rt>ばら</rt></ruby>が咲く` → `<ruby>薔薇<rt>ばら</rt></ruby>が散る` (タグ不変・咲→散)
  6. 混在: "彼は<ruby>剣<rt>けん</rt></ruby>を振るう" → "彼は<ruby>剣<rt>けん</rt></ruby>を振り下ろす" (振る→振り下ろす)
  7. 空文字列対空文字列、片側空
- **検証コマンド**: `npm run test:ci -- tests/unit/utils/textDiff.test.ts`
- **期待結果**: 全ケースパス

---

### Step 4: 推敲状態管理フック
- **対象ファイル**: `src/hooks/useInlineRevision.ts` (新規作成)
- **実装内容**:
```typescript
import { useState, useCallback } from 'react';
import { RevisionProposal, RevisionVerificationResult } from '../types/inlineRevision';
import { charDiff } from '../utils/textDiff';
import { verifySelection } from '../utils/selectionVerify';

export function useInlineRevision() {
  const [proposal, setProposal] = useState<RevisionProposal | null>(null);
  const [diff, setDiff] = useState<DiffSegment[]>([]);
  const [verification, setVerification] = useState<RevisionVerificationResult | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [status, setStatus] = useState<'idle' | 'generating' | 'verifying' | 'ready' | 'held'>('idle');

  const startRevision = useCallback(async (instruction: string, selectionRange, originalText: string) => {
    setStatus('generating');
    // 既存 AI 呼び出しロジック (InlineAiToolbar から移植)
    const revisedText = await callRevisionAPI(instruction, originalText);
    const newProposal: RevisionProposal = {
      id: crypto.randomUUID(),
      originalText,
      revisedText,
      instruction,
      timestamp: Date.now(),
      selectionRange,
    };
    setProposal(newProposal);
    setDiff(charDiff(originalText, revisedText));
    setStatus('verifying');
    // 即時検証
    const result = verifySelection(selectionRange, originalText);
    setVerification(result);
    setStatus(result.isMatch ? 'ready' : 'held');
    setIsModalOpen(true);
  }, []);

  const apply = useCallback(() => {
    if (!proposal || verification?.isMatch !== true) return;
    // Editor.tsx の applyRevision に委譲 (Props または Context でコールバック受け取り)
    onApply?.(proposal);
    reset();
  }, [proposal, verification]);

  const hold = useCallback(() => {
    setStatus('held');
    // 提案をキープ、モーダル開いたまま
  }, []);

  const reject = useCallback(() => reset(), []);

  const reset = useCallback(() => {
    setProposal(null);
    setDiff([]);
    setVerification(null);
    setIsModalOpen(false);
    setStatus('idle');
  }, []);

  return { proposal, diff, verification, isModalOpen, status, startRevision, apply, hold, reject, closeModal: () => setIsModalOpen(false) };
}
```
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/hooks/useInlineRevision.test.ts`
- **期待結果**: 状態遷移 (idle→generating→verifying→ready/held) 正常、検証結果反映

---

### Step 5: 推敲専用差分確認モーダル
- **対象ファイル**: `src/components/editor/InlineRevisionDiffModal.tsx` (新規作成)
- **実装内容**:
  - `Modal` 再利用、`DiffViewer` コンポーネント (既存) を内部使用
  - Props: `proposal`, `diff`, `verification`, `onApply`, `onHold`, `onReject`, `onClose`
  - 表示:
    - ヘッダー: "推敲提案: より感情的に" + 指示文
    - 差分ビュー: `DiffViewer` (左右またはインライン表示)
    - 検証結果バー:
      - OK: 緑「原文一致、適用可能」
      - NG: 赤「原文が変更されています (外部編集等)」+ 差分詳細
    - アクションバー:
      - OK 時: [適用する] (primary) [却下] [保留]
      - NG 時: [保留して再確認] (primary) [最新版で再生成] [却下]
  - キーボード: Enter=適用 (OK時) / 保留 (NG時)、Escape=却下
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/components/InlineRevisionDiffModal.test.tsx`
- **期待結果**: 差分表示・検証バー・アクションすべて動作

---

### Step 6: InlineAiToolbar 推敲フロー接続
- **対象ファイル**: `src/components/editor/InlineAiToolbar.tsx` (修正)
- **変更箇所**: L71-79 (スナップショット取得)・L256-268 (プレビュー表示・適用)
- **実装内容**:
  1. `useInlineRevision()` フック導入
  2. `handleRevision` 内で `startRevision(instruction, selectionRange, selectedText)` 呼び出し
  3. 既存 120px プレビュー表示削除 → モーダル開くのみ
  4. ツールバー UI: 推敲ボタン押下時ローディング表示 (`status === 'generating'`)
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 推敲ボタン→生成中表示→モーダル表示のフロー動作

---

### Step 7: Editor.tsx 適用処理接続・選択検証
- **対象ファイル**: `src/components/editor/Editor.tsx` (修正)
- **変更箇所**: L244-259 (applyRevision 周辺)
- **実装内容**:
  1. `useInlineRevision` から `onApply` コールバック受け取り、既存 `applyRevision` 置換
  2. 適用直前の選択範囲検証ロジックを `selectionVerify.ts` へ切り出し (Step 8)
  3. `contentEditable` 内の現在選択範囲テキスト取得・元テキストと比較
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: モーダル「適用」→検証通過→本文置換、検証失敗時は適用スキップ

---

### Step 8: 選択範囲・原文検証ユーティリティ
- **対象ファイル**: `src/utils/selectionVerify.ts` (新規作成)
- **実装内容**:
```typescript
import { RevisionVerificationResult } from '../types/inlineRevision';

export function verifySelection(
  range: { start: number; end: number },
  expectedOriginal: string,
  editorRef: React.RefObject<HTMLDivElement>
): RevisionVerificationResult {
  if (!editorRef.current) {
    return { isMatch: false, mismatchReason: 'contentMissing', currentTextAtRange: '', suggestion: 'hold' };
  }
  // contentEditable から range でテキスト抽出
  const walker = document.createTreeWalker(editorRef.current, NodeFilter.SHOW_TEXT);
  let currentOffset = 0;
  let foundText = '';
  let node: Node | null = null;
  while ((node = walker.nextNode())) {
    const nodeLen = node.textContent?.length || 0;
    if (currentOffset + nodeLen > range.start) {
      const startInNode = Math.max(0, range.start - currentOffset);
      const endInNode = Math.min(nodeLen, range.end - currentOffset);
      foundText = node.textContent?.slice(startInNode, endInNode) || '';
      break;
    }
    currentOffset += nodeLen;
  }
  const isMatch = foundText === expectedOriginal;
  return {
    isMatch,
    mismatchReason: isMatch ? undefined : 'textChanged',
    currentTextAtRange: foundText,
    suggestion: isMatch ? 'apply' : 'hold',
  };
}
```
- **検証コマンド**: `npm run test:ci -- tests/unit/utils/selectionVerify.test.ts`
- **期待結果**: 同一テキスト→match、編集後→mismatch (textChanged)

---

### Step 9: モーダル検証失敗ハンドリング
- **対象ファイル**: `src/components/editor/InlineRevisionDiffModal.tsx` (修正・Step 5 追加)
- **実装内容**:
  - `verification.isMatch === false` 時:
    - 警告バナー表示: "⚠ 元の文章が変更されています。適用すると意図しない箇所が書き換わる可能性があります。"
    - 現在の範囲テキスト (`verification.currentTextAtRange`) を小さく表示
    - Primary ボタン: "保留して再確認" (hold)
    - Secondary: "最新版で再生成" (再生成トリガー), "却下"
  - `status === 'held'` 時: バッジ "保留中" 表示、ツールバーに再開導線 (オプション)
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 検証失敗時に適切な警告・アクション表示

---

### Step 10: DiffViewer 文字レベルハイライト対応
- **対象ファイル**: `src/components/editor/DiffViewer.tsx` (修正)
- **変更箇所**: L43-80 (既存行ベース表示)
- **実装内容**:
  - 既存: 行単位 diff → 左右ペイン表示
  - 拡張: `DiffSegment.charDiffs` 存在時、インライン文字レベルハイライト表示
  - CSS クラス: `.diff-char-insert` (緑背景), `.diff-char-delete` (赤打ち消し), `.diff-char-replace` (橙下線)
  - ルビタグ内部の文字差分も正しくネスト表示
  - Props `granularity: 'line' | 'char'` 追加、デフォルト 'line' (既存互換)
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 既存整合性修正は行ベース維持、推敲モーダルのみ文字レベル表示

---

### Step 11: 統合単体テスト
- **対象ファイル**: `tests/unit/components/InlineRevisionDiffModal.test.tsx` (新規作成)
- **テストケース**:
  1. 提案生成→差分計算→検証OK→適用ボタンで `onApply` 発火
  2. 外部編集シミュレーション (editorRef 書き換え) → 検証NG→警告・保留ボタン表示
  3. 保留→再検証 (最新テキストで再度 verify) → OK になれば適用可能
  4. キーボード操作: Enter/Escape で適切なアクション発火
  5. ルビ含む HTML で差分正しく表示 (DiffViewer granularity='char')
- **検証コマンド**: `npm run test:ci -- tests/unit/components/InlineRevisionDiffModal.test.tsx`
- **期待結果**: 全ケースパス

---

### Step 12: E2E 実操作確認
- **対象ファイル**: `tests/e2e/inline_revision.test.ts` (新規作成)
- **シナリオ** (Playwright):
  1. エディタで段落選択 → ツールバー「推敲: より感情的に」クリック
  2. 生成待機→モーダル表示→差分確認 (削除赤・挿入緑・文字レベル) → 「適用」
  3. 本文置換確認、Undo (Ctrl+Z) で元に戻る確認
  4. 別タブ/別ウィンドウで同チャプター編集 → 元タブで推敲実行 → 検証NG 警告表示確認
  5. 「保留」→ 元タブで Undo → 再検証 → OK になり適用成功
  6. 「最新版で再生成」→ 新提案生成→差分確認→適用
- **検証コマンド**: `npm run test:e2e -- tests/e2e/inline_revision.test.ts`
- **期待結果**: 全シナリオパス、音声保護・誤適用防止が実操作で確認

---

## 🔗 依存関係グラフ
```
Step 1 → Step 2 → Step 3
              ↓
         Step 4 → Step 5
              ↓    ↓
         Step 6 → Step 7
              ↓
         Step 8 → Step 9
              ↓
         Step 10 ← (DiffViewer 既存改修)
              ↓
         Step 11 → Step 12
```

---

## ✅ 完了判定基準
1. 全 12 ステップ検証コマンド通過
2. 既存テストスイート ALL GREEN
3. 手動確認: 推敲→差分モーダル→適用/保留/再生成の全フロー動作
4. TypeScript 型チェック・Lint エラーなし
5. 既存整合性修正フロー (EditorialSidebar) に影響なし (DiffViewer 共用だが granularity 切替で分離)

---

## 📝 備考
- `DiffViewer` 既存資産を最大限再利用 (Step 10 で拡張のみ)
- `graphemer` 導入時は `package.json` 追加、未導入時は自前 split (配列展開 `...str` で代用可・サロゲートペア注意)
- 原文検証は「適用直前」のみ実施。生成中に編集されたケースをカバー
- 保留状態はセッション内のみ保持 (ページ遷移で破棄)。将来的に IndexedDB 永続化拡張可