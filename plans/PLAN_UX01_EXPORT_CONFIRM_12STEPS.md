# AutoNovel UX改善計画: エクスポート対象明示確認・コピー await 化 (全12ステップ)

**対象**: #8 エクスポート時の「対象明示確認・コピー await 化」
**目的**: 間違ったチャプター・版・ブランチの納品を防ぎ、クリップボードコピーを確実に完了待ちにする
**前提**: 既存 `ExportPanel.tsx`、`PublishExportModal.tsx`、`PublishAssistantModal.tsx` の実装を流用・拡張

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Type | `src/types/export.ts` | [NEW] エクスポート確認用の型定義 (ExportHandoffSummary, ExportTarget) |
| **Step 2** | Component | `src/components/common/ExportConfirmModal.tsx` | [NEW] 出力前確認モーダル (チャプター/ブランチ/版/行き先サマリ表示) |
| **Step 3** | Hook | `src/hooks/useExportConfirm.ts` | [NEW] 確認モーダル開閉・選択状態管理フック |
| **Step 4** | Modify | `src/components/ExportPanel.tsx` | [MODIFY] ZIP出力前に確認モーダル挿入、選択内容を `packageExport` へ渡す |
| **Step 5** | Modify | `src/components/ExportPanel.tsx` | [MODIFY] 出版出力前に確認モーダル挿入、`bookId` だけでなくチャプター/版/ブランチを明示渡し |
| **Step 6** | Modify | `src/components/common/PublishExportModal.tsx` | [MODIFY] デフォルト第1話→確認モーダルで選択可能に、サーバー取得前にローカル版も選択肢へ |
| **Step 7** | Modify | `src/components/common/PublishExportModal.tsx` | [MODIFY] `copyToClipboard` を `await navigator.clipboard.writeText()` 化、成功時のみトースト |
| **Step 8** | Modify | `src/components/publishing/PublishAssistantModal.tsx` | [MODIFY] 同上：クリップボードコピーを await 化、失敗時フォールバック (ダウンロード) 提示 |
| **Step 9** | Utility | `src/utils/clipboard.ts` | [NEW] `copyWithFallback(text, fallbackBlob?)` 共通ユーティリティ (await + フォールバック) |
| **Step 10** | Test | `tests/unit/components/ExportConfirmModal.test.tsx` | [NEW] 確認モーダルの表示・選択・確定フロー単体テスト |
| **Step 11** | Test | `tests/unit/utils/clipboard.test.ts` | [NEW] `copyWithFallback` の成功・失敗・フォールバック経路テスト |
| **Step 12** | E2E | `tests/e2e/export_handoff.test.ts` | [NEW] Playwright: ZIP出力・出版出力・コピーの全フロー確認 (誤チャプター防止検証) |

---

## 🛠️ 各ステップ詳細手順

### Step 1: エクスポート確認用型定義
- **対象ファイル**: `src/types/export.ts` (新規作成)
- **実装内容**:
```typescript
export type ExportVersion = 'saved' | 'current';
export type ExportDestination = 'zip' | 'epub' | 'clipboard' | 'publish';

export interface ExportTarget {
  bookId: string;
  chapterId: string;
  branchId: string;
  version: ExportVersion;
  destination: ExportDestination;
  label: string;          // 表示用 "第3話 (mainブランチ・現在編集版)"
  wordCount: number;
  lastSavedAt: string;    // ISO string
}

export interface ExportHandoffSummary {
  targets: ExportTarget[];
  primaryTarget: ExportTarget;
  warnings: string[];     // 例: ["保存版と現在編集版で 1,200 字の差分があります"]
}
```
- **検証コマンド**: `npx tsc --noEmit --skipLibCheck src/types/export.ts`
- **期待結果**: 型エラーなし

---

### Step 2: 出力前確認モーダル作成
- **対象ファイル**: `src/components/common/ExportConfirmModal.tsx` (新規作成)
- **実装内容**:
  - `Modal` コンポーネント再利用 (`src/components/common/Modal.tsx`)
  - Props: `isOpen`, `onClose`, `summary: ExportHandoffSummary`, `onConfirm: (target: ExportTarget) => void`
  - 表示項目: 対象チャプター、ブランチ名、版 (保存/現在編集)、行き先、文字数、最終保存時刻
  - 警告欄: `summary.warnings` があれば黄色バナーで表示
  - アクション: 「キャンセル」「出力実行」 (primary)
  - キーボード: Enter=確定、Escape=キャンセル、フォーカストラップ
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/components/ExportConfirmModal.test.tsx`
- **期待結果**: 型チェック通過、テストグリーン

---

### Step 3: 確認モーダル制御フック
- **対象ファイル**: `src/hooks/useExportConfirm.ts` (新規作成)
- **実装内容**:
```typescript
export function useExportConfirm() {
  const [isOpen, setIsOpen] = useState(false);
  const [summary, setSummary] = useState<ExportHandoffSummary | null>(null);
  const [resolve, setResolve] = useState<((target: ExportTarget) => void) | null>(null);

  const open = (s: ExportHandoffSummary): Promise<ExportTarget> => {
    setSummary(s);
    setIsOpen(true);
    return new Promise(r => setResolve(() => r));
  };

  const confirm = (target: ExportTarget) => {
    resolve?.(target);
    setIsOpen(false);
    setResolve(null);
  };

  const cancel = () => {
    resolve?.(null as any);
    setIsOpen(false);
    setResolve(null);
  };

  return { isOpen, summary, open, confirm, cancel };
}
```
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/hooks/useExportConfirm.test.ts`
- **期待結果**: 型チェック通過、Promise 解決フロー動作確認

---

### Step 4: ExportPanel ZIP出力に確認挿入
- **対象ファイル**: `src/components/ExportPanel.tsx` (修正)
- **変更箇所**: `handlePackageExport` (L56-61 付近)
- **実装内容**:
  1. `useExportConfirm` フック導入
  2. 現在のチャプター/ブランチ/版情報で `ExportHandoffSummary` 構築
  3. `open(summary)` で確認モーダル表示
  4. 確定時に `packageExport(bookId, confirmedTarget)` 呼び出し
  5. `confirmedTarget.version === 'current'` なら現在のエディタテキスト、`'saved'` ならサーバー取得
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/components/ExportPanel.test.tsx`
- **期待結果**: ZIP出力ボタン→確認モーダル→確定→ダウンロードのフロー動作

---

### Step 5: ExportPanel 出版出力に確認挿入
- **対象ファイル**: `src/components/ExportPanel.tsx` (修正)
- **変更箇所**: `handlePublishExport` (L249-254 付近)
- **実装内容**:
  1. Step 4 と同様に確認モーダル表示
  2. `PublishExportModal` 呼び出し時に `chapterId`, `branchId`, `version` を明示渡し
  3. 複数チャプター対象の場合は配列で渡し、モーダル側で単一選択させる
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 出版出力ボタン→確認モーダル→PublishExportModal へ正しいパラメータ渡し

---

### Step 6: PublishExportModal チャプター選択・版選択対応
- **対象ファイル**: `src/components/common/PublishExportModal.tsx` (修正)
- **変更箇所**: L24-42 (初期状態・プレビュー取得)
- **実装内容**:
  1. Props に `initialChapterId?`, `initialBranchId?`, `initialVersion?`, `availableChapters[]` 追加
  2. デフォルト第1話 → 受け取った `initialChapterId` または最初のチャプター
  3. チャプターセレクタ追加 (ドロップダウン)
  4. 版セレクタ追加 (ラジオ: "保存版" / "現在編集版")
  5. プレビュー取得前に選択内容反映
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 親から渡されたチャプター・版でプレビュー表示

---

### Step 7: PublishExportModal クリップボードコピー await 化
- **対象ファイル**: `src/components/common/PublishExportModal.tsx` (修正)
- **変更箇所**: L60-64 (`handleCopyToClipboard`)
- **実装内容**:
```typescript
const handleCopyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(previewText);
    addToast('クリップボードにコピーしました', 'success');
  } catch (e) {
    addToast('コピーに失敗しました。手動でコピーしてください', 'error');
    // フォールバック: textarea にフォーカス・選択
    const ta = document.createElement('textarea');
    ta.value = previewText;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
  }
};
```
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: コピー完了まで待機、成功時のみ成功トースト、失敗時エラートースト+フォールバック

---

### Step 8: PublishAssistantModal クリップボードコピー await 化
- **対象ファイル**: `src/components/publishing/PublishAssistantModal.tsx` (修正)
- **変更箇所**: L77-80 (コピー処理)
- **実装内容**: Step 7 と同等の `await navigator.clipboard.writeText()` + フォールバック実装
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 同等の確実なコピー動作

---

### Step 9: 共通クリップボードユーティリティ
- **対象ファイル**: `src/utils/clipboard.ts` (新規作成)
- **実装内容**:
```typescript
export async function copyWithFallback(
  text: string,
  fallbackBlob?: Blob
): Promise<{ success: boolean; usedFallback: boolean }> {
  try {
    await navigator.clipboard.writeText(text);
    return { success: true, usedFallback: false };
  } catch {
    if (fallbackBlob) {
      const url = URL.createObjectURL(fallbackBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'export.txt';
      a.click();
      URL.revokeObjectURL(url);
      return { success: true, usedFallback: true };
    }
    // textarea フォールバック
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    return { success: true, usedFallback: true };
  }
}
```
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/utils/clipboard.test.ts`
- **期待結果**: 成功・フォールバック両経路でテスト通過

---

### Step 10: ExportConfirmModal 単体テスト
- **対象ファイル**: `tests/unit/components/ExportConfirmModal.test.tsx` (新規作成)
- **テストケース**:
  1. `summary` 渡しで正しく表示される
  2. 警告配列があるとき黄色バナー表示
  3. 「出力実行」クリックで `onConfirm` に正しい `ExportTarget` 渡る
  4. Escape キーで `onClose` 呼ばれる
  5. フォーカストラップ動作 (Tab でモーダル内循環)
- **検証コマンド**: `npm run test:ci -- tests/unit/components/ExportConfirmModal.test.tsx`
- **期待結果**: 全ケースパス

---

### Step 11: clipboard.ts 単体テスト
- **対象ファイル**: `tests/unit/utils/clipboard.test.ts` (新規作成)
- **テストケース** (JSDOM + `navigator.clipboard` モック):
  1. `navigator.clipboard.writeText` 成功 → `{success:true, usedFallback:false}`
  2. `writeText` 失敗 + `fallbackBlob` あり → ダウンロード発火・`{success:true, usedFallback:true}`
  3. `writeText` 失敗 + `fallbackBlob` なし → `execCommand('copy')` 呼び出し・`{success:true, usedFallback:true}`
  4. `execCommand` も失敗 → `{success:false, usedFallback:true}`
- **検証コマンド**: `npm run test:ci -- tests/unit/utils/clipboard.test.ts`
- **期待結果**: 全ケースパス

---

### Step 12: E2E エクスポート全フロー確認
- **対象ファイル**: `tests/e2e/export_handoff.test.ts` (新規作成)
- **シナリオ** (Playwright):
  1. 作品作成 → 第1話・第2話生成 → ブランチ作成・編集
  2. ZIP出力ボタン → 確認モーダルで「第2話・featureブランチ・現在編集版」選択 → ダウンロード → 中身検証
  3. 出版出力ボタン → 確認モーダル → PublishExportModal でチャプター切替 → プレビュー確認
  4. コピーボタン → クリップボード内容検証 (Playwright `page.evaluate(() => navigator.clipboard.readText())`)
  5. 失敗シミュレーション (HTTPS 非対応環境) → フォールバック ダウンロード発火確認
- **検証コマンド**: `npm run test:e2e -- tests/e2e/export_handoff.test.ts`
- **期待結果**: 全シナリオパス、誤チャプター出力なし

---

## 🔗 依存関係グラフ
```
Step 1 → Step 2 → Step 3
              ↓
         Step 4 → Step 5
              ↓
         Step 6 → Step 7
              ↓
         Step 8 ← Step 9
              ↓
         Step 10 → Step 11 → Step 12
```

---

## ✅ 完了判定基準
1. 全 12 ステップの検証コマンドがエラーなく通る
2. 既存テストスイート (`npm run test:ci`) が ALL GREEN
3. 手動確認: ZIP出力・出版出力・コピーで確認モーダル表示、await コピー動作、誤チャプター防止確認
4. TypeScript 型チェック (`npm run typecheck`) エラーなし
5. Lint (`npm run lint`) エラーなし

---

## 📝 備考
- 既存 `Modal`・`Toast`・`useNovelContext` を再利用し、新規依存なし
- `navigator.clipboard` は HTTPS 必須 → 開発環境 (localhost) でも動作、フォールバックで完全カバー
- Step 9 のユーティリティは将来的に他のコピー機能 (生成結果コピー等) でも再利用可能