# AutoNovel Studio 機能⇄UI/UX ズレ是正 実装計画

前段の検証で抽出した14件の不具合を、**36 の小さなステップ**に分割する。
各ステップは1 PR 単位で完結し、コミット・テスト・ロールバックが容易な粒度とする。

凡例: `[F]`=Frontend / `[B]`=Backend / `[FB]`=両方 / `[I]`=Infra/Docs

---

## Phase 0: 事前整理 (Steps 1-3)

### Step 1 `[I]` 不具合一覧を Issue テンプレ化
- `docs/bugs/ui-functionality-gap.md` を新規作成し、本検証の14項目を Checklist 形式で転記
- 各項目に severity・影響範囲・関連ファイルパスを併記
- 検証コマンド: `ls docs/bugs/` で存在を確認

### Step 2 `[I]` 影響ファイル一覧を抽出
- 前回検証で挙げたファイルを `docs/bugs/ui-functionality-gap.md` の「関連ファイル」セクションに集約
- 例: `frontend/src/components/studio/StudioWorkspace.tsx:14-27`, `src/backend/routers/easy_mode.py:88` 等
- 検証コマンド: `rg "AssetPackPanel" frontend/src` で利用箇所を列挙

### Step 3 `[F]` 既存フロント単体テストのベースライン測定
- `cd frontend && npm run test -- --reporter=basic 2>&1 | tail -20` を実行し、現状の pass/fail を `docs/bugs/baseline-frontend.txt` に保存
- 失敗テストは本計画の修正対象外として記録(リグレッション検知用)
- 検証コマンド: `cat docs/bugs/baseline-frontend.txt`

---

## Phase 1: Studio モードのタブ UI 復旧 (Steps 4-7)

> 対象: 検証 #1 「`tab` 状態と UI が不整合」/ #11 「`AssetPackPanel` 到達不能」

### Step 4 `[F]` StudioWorkspace のタブバー UI を新規実装
- `frontend/src/components/studio/StudioWorkspace.tsx` に `tab` 切り替えボタンを追加
- 配置: `<main className="studio-pane">` の先頭(エディタ前)
- デザイン: 既存の `btn-tab` / `btn-tab--active` クラスを踏襲
- 検証コマンド: `grep "btn-tab" frontend/src/components/studio/StudioWorkspace.tsx` で2件以上ヒット

### Step 5 `[F]` タブ状態を localStorage に同期
- `useEffect` で `tab` を `localStorage.setItem("autonovel.studioTab", tab)` に保存
- 初期化時に保存値を読み込んでフォールバック
- 検証コマンド: `grep "autonovel.studioTab" frontend/src/components/studio/StudioWorkspace.tsx`

### Step 6 `[F]` `multimedia` タブの空状態(プレースホルダ)を追加
- `<AssetPackPanel>` を表示する前に `tab === "multimedia"` 用のローディング/エラー境界を追加
- 画像生成未実装の場合でも意味のあるメッセージを表示
- 検証コマンド: `grep "multimedia" frontend/src/components/studio/StudioWorkspace.tsx` で 3件以上

### Step 7 `[F]` StudioWorkspace の単体テスト追加
- `frontend/tests/StudioWorkspace.test.tsx` を新規作成
- タブクリックで `tab` state が切り替わることを検証
- 検証コマンド: `cd frontend && npx vitest run tests/StudioWorkspace.test.tsx`

---

## Phase 2: Promote 仕様の実装整合 (Steps 8-11)

> 対象: 検証 #4 「`promote` の `state_token` / `redirect_url` を無視」

### Step 8 `[B]` `PromotionService` の state_token を DB に保存するメソッドを追加
- `src/services/promotion_service.py` に `save_state_token(book_id, token)` を追加
- テーブル: 新規 `book_promotion_tokens` (book_id PK, expires_at TIMESTAMP)
- マイグレーション: `alembic revision --autogenerate -m "add_book_promotion_tokens"`
- 検証コマンド: `alembic upgrade head` 成功 + `alembic current` で新 revision 表示

### Step 9 `[B]` `/easy_mode/promote` レスポンスの `redirect_url` を `/studio/:book_id` 形式に変更
- `src/services/promotion_service.py:31` の `redirect_url` を `f"/studio/{book_id}"` に変更
- 検証コマンド: `grep "redirect_url" src/services/promotion_service.py` で該当箇所確認

### Step 10 `[F]` `ExportPanel` の `handlePromote` で `redirect_url` を `history.push` する
- `frontend/src/components/ExportPanel.tsx:60-66` を修正
- `import { useNavigate } from "react-router-dom"` を追加(ルータ未導入なら最小導入)
- `res.redirect_url` を `navigate(res.redirect_url + "?token=" + res.state_token)` で遷移
- 検証コマンド: `grep "navigate(" frontend/src/components/ExportPanel.tsx`

### Step 11 `[F]` `/studio/:book_id?token=` 用の新ルートを `App.tsx` に追加
- `react-router-dom` の `<Route path="/studio/:bookId" element={<StudioWorkspace />} />` を追加
- クエリパラメータ `token` を `localStorage` に保存して以後の API 呼び出しに付与
- 検証コマンド: `grep "Route" frontend/src/App.tsx`

---

## Phase 3: 単一本文ソース化 (Steps 12-17)

> 対象: 検証 #3 「Easy ⇄ Studio の本文二重管理」/ #14 「state 共有による意図せぬ上書き」

### Step 12 `[F]` `NovelContext` から `generationState.currentOutput` を `currentChapterText` へ統合
- `frontend/src/context/NovelContext.tsx` で `currentOutput` を派生 getter に変更
- `generationState.currentOutput` フィールドを deprecated マーク(コメント)
- 検証コマンド: `grep "currentOutput" frontend/src/context/NovelContext.tsx` で setter 呼び出し箇所ゼロ

### Step 13 `[F]` `ExportPanel` 内 `<Editor>` の `onChange` を `setCurrentChapterText` 経由に変更
- `frontend/src/components/ExportPanel.tsx:140-145` の `onChange` を `setCurrentChapterText` に統一
- `syncGenerationToEditor` 呼び出しは維持
- 検証コマンド: `grep "setGenerationState" frontend/src/components/ExportPanel.tsx`

### Step 14 `[F]` `useStreamingWriter` の完了時更新を `currentChapterText` のみに変更
- `frontend/src/hooks/useStreamingWriter.ts:111-116` から `currentOutput: finalText` を削除
- 検証コマンド: `grep "currentOutput" frontend/src/hooks/useStreamingWriter.ts` で参照0件

### Step 15 `[F]` `useNovelGeneration` も同様に統合
- `frontend/src/hooks/useNovelGeneration.ts` で `currentOutput` setter を `currentChapterText` 経由に
- 検証コマンド: `grep "currentOutput" frontend/src/hooks/useNovelGeneration.ts`

### Step 16 `[F]` `displayOutput` 参照箇所を `currentChapterText` に置換
- `ExportPanel.tsx:39` の `displayOutput = output !== undefined ? output : generationState.currentOutput` を `currentChapterText` 参照に変更
- 検証コマンド: `rg "displayOutput" frontend/src` で0件

### Step 17 `[F]` `GenerationState` 型から `currentOutput` を削除
- `frontend/src/types/index.ts:34-42` の interface から `currentOutput: string` を削除
- TypeScript 型エラーが0になるまで呼び出し側を修正
- 検証コマンド: `cd frontend && npx tsc --noEmit`

---

## Phase 4: 嘘 UI の是正 (Steps 18-20)

> 対象: 検証 #8 「`Ctrl+S` の嘘トースト」/ #12 「旧仕様のヒント」/ #10 「SSE フォールバックの無音失敗」

### Step 18 `[F]` `Ctrl+S` トーストを撤去
- `frontend/src/components/editor/Editor.tsx:117-119` の `onToast` 呼び出しを削除
- 未実装の永続化コードを追加するか、ショートカット自体を撤去(判断: 撤去)
- 検証コマンド: `grep "Ctrl+S" frontend/src/components/editor/Editor.tsx` で0件

### Step 19 `[F]` SSE フォールバックを明示エラー化
- `frontend/src/hooks/useStreamingWriter.ts:135-153` の `catch` ブロックを改修
- `onError?.(\`❌ 接続エラー: ${err.message}\`)` を呼び、`isStreaming` を `false` にして即終了
- フォールバックタイプライターを完全削除
- 検証コマンド: `grep "fallbackText" frontend/src/hooks/useStreamingWriter.ts` で0件

### Step 20 `[F]` ヘッダのキャッチコピーを実機能と整合
- `frontend/src/App.tsx:34-37` の `<h1>` / `<p>` を機能説明に変更
- 例: 「AI 執筆・設定管理・矛盾診断スタジオ」
- 検証コマンド: `grep "Notion AI" frontend/src/App.tsx` で0件

---

## Phase 5: ジャンル ⇄ Preset マッピング修正 (Steps 21-24)

> 対象: 検証 #6 「UI ジャンルと preset のマッピング不備」

### Step 21 `[B]` ジャンル文字列 → preset key マッピング辞書を `easy_mode.py` に追加
- `src/backend/routers/easy_mode.py:88` の決め打ちを `GENRE_TO_PRESET = {...}` 辞書に置換
- マッピング: `ざまぁ→zarma`, `令嬢→aku_reijo`, `VRMMO→vrmmo`, `スローライフ→slow_life`, `追放後スローライフ→slow_life`, `ループ→loop`, `ダンジョン→dungeon_admin`, `テンセイ→cheat_tensei`, `現代チート→modern_cheat`, `異世界転生→cheat_tensei`
- 検証コマンド: `grep "GENRE_TO_PRESET" src/backend/routers/easy_mode.py`

### Step 22 `[B]` `easy_mode.py:88` のフォールバックを `genre_key` 未知時に `cheat_tensei` ではなく**警告ログ + 空 StyleProfile** に変更
- 例外を握りつぶさず、`logger.warning("Unknown genre: %s", genre)`
- 検証コマンド: `grep "Unknown genre" src/backend/routers/easy_mode.py`

### Step 23 `[B]` `tests/test_genre_mapping.py` を新規作成
- 各 UI ジャンル文字列が正しい preset key に解決されることを検証
- 検証コマンド: `cd autonovel && python -m pytest tests/test_genre_mapping.py -v`

### Step 24 `[F]` `GeneratePanel.tsx` の `<select>` 選択肢を `BACKEND_GENRES` 配列ベースに変更
- `frontend/src/components/GeneratePanel.tsx:280-287` の `<option>` を定数配列 `.map()` に置換
- 配列は `frontend/src/constants/genres.ts` に分離
- 検証コマンド: `grep "BACKEND_GENRES" frontend/src/components/GeneratePanel.tsx`

---

## Phase 6: ReversePlot データ保護 (Steps 25-27)

> 対象: 検証 #7 「既存章データが消える可能性」

### Step 25 `[F]` `handleReversePlotComplete` のマージロジックを保護型に変更
- `frontend/src/components/GeneratePanel.tsx:154-173` を改修
- 既存章の `content` が空でなく、かつ新構造の同 `ep_num` に元データがある場合**は保持**
- 上書き前に確認ダイアログを表示(`window.confirm` で十分)
- 検証コマンド: `grep "window.confirm" frontend/src/components/GeneratePanel.tsx`

### Step 26 `[F]` `ReversePlotBuilder` の単体テスト追加
- `frontend/tests/ReversePlotBuilder.test.tsx` を新規作成
- 既存章保持・新規章追加・空チャンタ上書きの各ケースをカバー
- 検証コマンド: `cd frontend && npx vitest run tests/ReversePlotBuilder.test.tsx`

### Step 27 `[F]` バックエンド `ReversePlotGeneratePayload.answers` のキー制約を TypedDict 化
- `frontend/src/types/reversePlot.ts` に `ReversePlotAnswers` interface を定義
- 最低10個の主要キーを明示 (`protagonist`, `genre`, `tone`, `goal`, `inciting_incident`, ...)
- 検証コマンド: `grep "ReversePlotAnswers" frontend/src/types/reversePlot.ts`

---

## Phase 7: 未使用 hook の整理 (Steps 28-30)

> 対象: 検証 #13 「未使用 hook の放置」

### Step 28 `[I]` 未使用 hook の利用状況を `grep` で確認
- `rg "useCollabSync\|useLocalDraft\|usePatchReviews" frontend/src` で参照箇所を抽出
- 結果を `docs/bugs/ui-functionality-gap.md` の #13 セクションに記録
- 検証コマンド: コマンド出力を保存

### Step 29 `[F]` 使用予定がない hook を `frontend/src/hooks/_unused/` へ隔離
- `mkdir frontend/src/hooks/_unused && mv ...`
- 復活時に参照しやすいよう README を `_unused/README.md` に残す
- 検証コマンド: `ls frontend/src/hooks/_unused/`

### Step 30 `[F]` `useLocalDraft` を `Editor.tsx` の `Ctrl+S` 廃止後の代替として実装
- `Editor.tsx` に `useLocalDraft(content, "chapter_<bookId>_<epNum>")` を組み込み
- 500ms デバウンスで `localStorage` に保存
- 検証コマンド: `grep "useLocalDraft" frontend/src/components/editor/Editor.tsx`

---

## Phase 8: AssetPackPanel 到達経路の恒久化 (Steps 31-33)

> 対象: 検証 #1, #5, #11 のマルチメディア経路問題

### Step 31 `[F]` ヘッダに「🖼️ 画像生成」ボタンを追加
- `frontend/src/App.tsx:60-79` の相関図ボタン群に「🖼️ 画像生成」を追加
- `Studio` モード時のみ表示
- 検証コマンド: `grep "画像生成" frontend/src/App.tsx`

### Step 32 `[F]` `App.tsx` に `showMedia` state と `<AssetPackPanel>` モーダル表示を追加
- 既存の `showGraph` パターンを踏襲
- `StudioWorkspace` のタブ実装と整合(どちらでも開ける)
- 検証コマンド: `grep "showMedia" frontend/src/App.tsx`

### Step 33 `[B]` `/multimedia/generate-image` エンドポイントのフロント対応状況を確認
- `rg "AssetPackPanel" frontend/src/components/AssetPackPanel.tsx` で API 呼び出しを一覧化
- 未実装エンドポイントを `docs/bugs/asset-pack-todo.md` に記録
- 検証コマンド: 出力ファイル確認

---

## Phase 9: 検証・ドキュメント整備 (Steps 34-36)

### Step 34 `[FB]` E2E スモークテスト追加
- `tests/e2e/test_ui_functionality_gap.py` を新規作成
- 検証対象: かんたんモード→Studio昇格→タブ切替→画像生成ボタン表示
- Playwright ヘッドレスで `npm run build && python -m pytest tests/e2e/`
- 検証コマンド: `python -m pytest tests/e2e/test_ui_functionality_gap.py -v`

### Step 35 `[I]` 本計画の完了チェックリストを `docs/bugs/ui-functionality-gap.md` に追記
- 36 ステップすべてにチェックボックスと検証コマンドを併記
- 完了したステップは `[x]` 化
- 検証コマンド: `grep -c "\[x\]" docs/bugs/ui-functionality-gap.md` が段階的に増える

### Step 36 `[FB]` リリースノート草案を `CHANGELOG.md` に追記
- セクション: `## [Unreleased] - UI/UX ⇄ Functionality Alignment`
- 14 件の修正概要を 1 行ずつ列挙
- 検証コマンド: `head -50 CHANGELOG.md` で新セクションが見える

---

## スケジュール目安(1ステップ ≒ 0.5〜1日)

| Phase | ステップ範囲 | 想定工数 |
|-------|------------|---------|
| 0 準備 | 1-3 | 0.5日 |
| 1 Studioタブ | 4-7 | 1.5日 |
| 2 Promote | 8-11 | 2日 |
| 3 単一ソース | 12-17 | 2日 |
| 4 嘘UI是正 | 18-20 | 0.5日 |
| 5 ジャンル | 21-24 | 1日 |
| 6 ReversePlot | 25-27 | 1日 |
| 7 hook整理 | 28-30 | 0.5日 |
| 8 AssetPack | 31-33 | 1日 |
| 9 検証 | 34-36 | 1日 |
| **合計** | **36ステップ** | **約11日** |

## リスクと緩和策

| リスク | 影響 | 緩和 |
|--------|------|------|
| `react-router-dom` 未導入(#11) | Promote 実装が膨らむ | Step 11 で最小導入。既存 `App.tsx` を `<BrowserRouter>` でラップ |
| `GenerationState.currentOutput` 削除時のデグレ(#17) | 既存コンポーネントが型エラー | Phase 3 を 6 ステップに分け、Step 12→13→14→15→16→17 の順で漸進 |
| Alembic マイグレーション失敗(#8) | 本番 DB 影響 | Step 8 を develop 環境で先行適用。`alembic downgrade -1` で戻せるよう冪等性確保 |
| バックエンドテストが無い箇所の修正(#21-23) | リグレッション検知不能 | Step 23 で必ず新規テストを追加してから #21 をマージ |

## 各 PR のチェックリスト(共通)

- [ ] 検証コマンド(ステップごとに記載)が全て pass
- [ ] 既存の単体テスト・型チェックが pass (`cd frontend && npx tsc --noEmit`, `python -m pytest tests/`)
- [ ] `docs/bugs/ui-functionality-gap.md` の該当項目に `[x]`
- [ ] 関連 issue に進捗コメント
- [ ] CHANGELOG.md の `[Unreleased]` に追記(該当 Phase のみ)