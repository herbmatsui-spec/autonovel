# 残存課題修正 実装計画書 (Frontend)

## 目的
第1フェーズの実装で復活させた lint / 型チェックの土台の上で、**未解消の残存課題**を丁寧に修正し、
`npm run lint` が clean になること、および `tsc --noEmit` がエラー 0 になることをゴールとする。

現状 (`npx eslint .` と `tsc --noEmit` の出力) をもとに、修正箇所をカテゴリ別に整理する。

---

## A. 型チェック (TypeScript) エラー

### A-1. `App.tsx(144)` — `_setLoading` の型不一致
- 現象: `useAppActions(_setLoading)` にて `_setLoading` は `useState` のタプル `[boolean, Dispatch<...>]`
  だが、`useAppActions` は `setLoading: (b: boolean) => void` を期待する。
- 修正: `App.tsx:81` の `const _setLoading = React.useState<boolean>(false);` を
  `const [_, setLoadingState] = React.useState<boolean>(false);` とし、
  `useAppActions(setLoadingState)` を渡す。不要な変数名 `_setLoading` を廃止し、意図を明確にする。

---

## B. ESLint `@typescript-eslint/no-explicit-any` エラー

### B-1. App.tsx (109, 113, 124) — タスク SSE コールバックの `any`
- `handleTaskStatus(status: any)` / `handleTaskComplete(status: any)` / `handleTaskError(error: any)`
- 修正: これらは `useTaskStream` のコールバック型 `UseTaskStreamCallbacks` (`onStatus`, `onComplete`
  は `TaskStatus` を引数に取る) に対応するので、引数型を `TaskStatus` にする。
  `handleTaskError` の引数は `Event | unknown` にして `console.error(error)` のみ呼ぶ。
- 影響: `status.error` など既存のアクセスは `TaskStatus` の `error?: string` で型安全になる。

### B-2. api.ts (118) — `connectTaskStream` の `onError: (error: any) => void`
- 修正: 引数型を `unknown` にする（呼び出し側 `handleTaskError` も合わせる）。

### B-3. api.ts (211, 212) — `CommercialPipelineParams` の `any`
- `config?: Record<string, any>` / `samples?: any[]`
- 修正: 型が不明なため `config?: Record<string, unknown>` とし、
  `samples?: unknown[]` とする（運用上の制約がない範囲で未知を `unknown` に格上げ）。

### B-4. api.ts (285, 286) — `getIssues` の `any`
- `Promise<any[]>` と `data.issues?: any[]` を `NarrativeMetricTrend` 等と同じく
  専用の `Issue` 型を `types/api.ts` に定義し、`Promise<Issue[]>` / `issues?: Issue[]` とする。
  定義が困難な場合は `unknown` へ格下げ。

### B-5. easyModeApi.ts (26, 46, 66) — `catch (error: any)`
- 3 関数とも `catch (error: any)` で `error.message` を参照。
- 修正: `catch (error: unknown)` とし、`error instanceof Error ? error.message : String(error)`
  でメッセージを取得するユーティリティ (`lib/utils.ts` に `getErrorMessage` を追加) を利用する。

### B-6. NarrativeGraph.tsx (73, 167, 171) — chart.js コールバックの `any`
- `targetDatasets: any[]` → `ChartDataset<'line'>[]` (chart.js の型をインポート) へ。
- `label: (context: any)` → `context: DefaultDataPoint<'line'>` または
  `ChartContext` を利用。簡易的には `context: { dataset: { label?: string }; parsed: { y: number } }`
  程度の局所型でも可。
- `onClick: (_event: any, elements: any[])` →
  `onClick: (_event: React.MouseEvent, elements: Element[])` を chart.js の `Element` 型で指定。

### B-7. PatchReviewPanel.tsx (22, 36, 56) — `catch (e: any)`
- 修正: `catch (e: unknown)` + `getErrorMessage(e)` ユーティリティで `e.message` を取得。

### B-8. PromptVersionTimeline.tsx (25) — `catch (e: any)`
- 修正: `catch (e: unknown)` + `getErrorMessage(e)`。

### B-9. EasyModeContainer.tsx (37, 57, 80) — `catch (err: any)`
- 修正: `catch (err: unknown)` + `getErrorMessage(err)`。

### B-10. EasyModeDialog.tsx (402, 415) — `e.target.value as any`
- `illustrationType` は store 上 `'cover' | 'episode' | 'both'`、
  `illustrationModel` は `'fast' | 'quality'` と既に型付けされているため `as any` 不要。
- 修正: `setIllustrationType(e.target.value)` / `setIllustrationModel(e.target.value)` とする。
  （select の option value と union が一致するため型推論が効く。）

---

## C. ESLint `jsx-a11y` エラー

### C-1. Sidebar.tsx (49) — `jsx-a11y/no-redundant-roles`
- `<aside role="complementary">` は暗黙の role と重複。
- 修正: `role="complementary"` を削除。

### C-2. Tooltip.tsx (20) — 非インタラクティブ要素の click
- `<span onClick onMouseEnter onMouseLeave>` に対して
  `click-events-have-key-events` / `no-static-element-interactions` が発火。
- 修正: `role="button"` + `tabIndex={0}` + `onKeyDown` (Enter/Space で toggle) を追加し、
  キーボード操作をサポートする。または `Tooltip` を `<button type="button">` で包む。

### C-3. EasyModeDialog.tsx (188) / ImportChapterDialog.tsx (36) — オーバーレイ click
- `role="dialog"` の div に `onClick={handleOverlayClick}` で `no-noninteractive-element-interactions`。
- 修正: オーバーレイのクリックは dialog 自身ではなく、専用の `backdrop` 要素へ分離するか、
  `handleOverlayClick` 側で `e.target === e.currentTarget` の判定を入れ、
  コメント + `/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */` を
  最小限に付与（推奨: backdrop 要素分離）。

### C-4. GachaCard.tsx (24) — カードの click
- `<div onClick onSelect>` で `click-events-have-key-events`。
- 修正: `role="button"` + `tabIndex={0}` + `onKeyDown` (Enter/Space) を追加。

---

## D. ESLint `react-hooks/rules-of-hooks` エラー

### D-1. NarrativeGraph.tsx (58, 63) — 早期 return 後のフック呼び出し
- `if (!data || data.length === 0) return (...)` の **後** に `useEffect` / `useMemo` を呼んでいる。
- 修正: 早期 return をフック呼び出し **の後** に移動する。すなわち
  `const [state] = ...`、`useEffect(...)`、`const filtered = useMemo(...)` を先に宣言し、
  その後に `if (empty) return`。フックの呼び出し順序を毎回同一にする。

---

## E. ESLint `@typescript-eslint/no-unused-vars` エラー

### E-1. HealthGate.tsx (18) — `catch (e)` の未使用
- `catch (e) { setHealth(null); }` で `e` が未使用。
- 修正: `catch {` とする（バインド不要の場合は省略）。

---

## 実施手順 (推奨順)

1. `lib/utils.ts` に `getErrorMessage(e: unknown): string` を追加（B-5〜B-9 で共用）。
2. `types/api.ts` に `Issue` 型を追加（B-4）。
3. A-1: `App.tsx` の loading state を修正。
4. B-1〜B-10: `any` を順次排除。
5. C-1〜C-4: a11y 修正。
6. D-1: NarrativeGraph のフック順序修正。
7. E-1: HealthGate の未使用変数修正。
8. 検証: `npx tsc -p tsconfig.app.json --noEmit` と `npx eslint .` と `npx vitest run`。

## 検証基準
- `npx tsc -p tsconfig.app.json --noEmit` → エラー 0
- `npx eslint .` → エラー 0 (warning は許容だが今回は 0 を目標)
- `npx vitest run` → 全テスト pass (28)
- `npx vite build` → 成功
