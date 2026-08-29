# 改善提案 1・2・3 実装計画（72 ステップ分割）

> 対象: `/home/herbmatsui/autonovel`（Hegemony Novel Engine）
> 優先順位: **提案 1（スタイル学習）→ 提案 2（整合性 Guardian 完全統合）→ 提案 3（自動改稿ループ）**
> 方針: 低性能 LLM でも 1 ステップ = 1 ファイル編集 or 1 関数追加 になるよう細分化。
> 各ステップの「完了条件」を満たしてから次へ進むこと。全ステップで `python -m pytest tests/unit -q` が緑であることを確認。

---

## 0. 前提・既存資産（手を付ける前に読む）

- **FS メモリ基盤**: `src/filesystem_memory/{paths,writer,reader,auto_update,sync}.py` 完了済み。ワークスペースは `workspaces/book_{id}/branch_{bid}/` に `SOUL.md / WORLD.md / CHARACTERS.md / OUTLINE.md / STORY_SUMMARY.md / MEMORY.md` を出力。
- **章完了フック**: `src/backend/database/repositories/chapter.py` の `create_chapter` 末尾（L71-87）で `auto_update` を best-effort 呼び出し中。ここが「章生成直後」の唯一の共通フック。
- **整合性エンジン**: `src/consistency/{engine,findings,checkers,filters,dismissed_store,injector,guardian_hook,cache}.py` 完了済み。`get_consistency_prompt_injection(book_id, branch_id, ep_num) -> str` が注入文字列を返す。
- **執筆パイプライン**: `src/services/writing_services.py` の `GenerationLoopManager.execute_generation_loop`（L84-275）。`sys_inst` は `WritingGenerationContext.build_sys_inst()`（L54）で組み立てられる。`ctx.book.id` / `ctx.branch_id` が取得可能（`src/models/writing.py:122` `WritingContext`）。
- **設定 API**: `config/project_context.py` の `ProjectContext.get_setting(key, default)` / `set_setting(key, value)` をトグル用に使う。

---

## 1. 共通ルール（全ステップ）

1. 一度に編集するファイルは **原則 1 つ**。複数にまたがる場合はステップを分割済み。
2. 新規モジュールは `src/` 配下の既存パッケージに置く（import パス `src.xxx`）。
3. すべての新規関数に `try/except` は付けない（呼び出し側の best-effort ブロックで吸収）。ただしチェック本体は失敗しても全体を止めないよう `engine.py` の既存パターンを踏襲。
4. テストは `tests/unit/` に `test_<対象>.py` で作成。`config/settings.py` の `ConfigManager` 不足で収集エラーになる既知 issue は無視（実装側 bug ではない）。

---

## Phase A — 提案 1: スタイル学習の即時実装（Step 1-24）

文体特徴を LLM なし（純 Python）で章から抽出し `STYLE_LEARNED.md` に蓄積、次章生成時に `sys_inst` へ注入。新規 DB 不要。

- **Step 1**: `src/filesystem_memory/templates/SOUL.md.j2` を Read し、現在のセクション構成（文体ガイド／トーン／禁則）をメモ。変更はまだしない。
- **Step 2**: `src/filesystem_memory/templates/STYLE_LEARNED.md.j2` を新規作成。内容は以下の 5 セクション骨子のみ（値はプレースホルダ）。
  ```
  # 学習済み文体: {{ book.title }}
  ## 頻出語（上位N）
  <!-- learned:top_words -->
  ## 平均文長
  <!-- learned:avg_len -->
  ## 助詞傾向
  <!-- learned:particles -->
  ## 禁則語（検出履歴）
  <!-- learned:banned -->
  ## 直近サンプル文
  <!-- learned:sample -->
  ```
- **Step 3**: `src/filesystem_memory/paths.py` の `WORKSPACE_FILES` リストに `"STYLE_LEARNED.md"` を追加（末尾）。
- **Step 4**: `src/services/workspace_service.py` の `_TEMPLATE_FILES` dict に `"STYLE_LEARNED.md": "STYLE_LEARNED.md.j2"` を追加。
- **Step 5**: `tests/unit/test_workspace_style_file.py` を新規作成。`init_workspace(1, {"title":"t"})` を呼び、`workspaces/book_1/branch_1/STYLE_LEARNED.md` が存在し、5 セクション見出しを含むことを `assert`。
- **Step 6**: `src/services/style_learning.py` を新規作成。関数 `split_sentences(text: str) -> list[str]` を実装（`.！？!?\n` で分割、空要素除去）。
- **Step 7**: 同じファイルに `count_particles(text) -> dict` を実装。対象助詞 `はがをにでへとばもで`（正規表現 `[はがをにへとばもで]` の出現数を `collections.Counter` で集計）。
- **Step 8**: 同じファイルに `top_words(text, n=15) -> list[str]` を実装。形態素解析なしで `re.findall(r"[一-龠々]{2,}|[ァ-ヶー]{2,}", text)` で 2 文字以上の語を抽出し `Counter` 上位 n。
- **Step 9**: 同じファイルに `avg_sentence_length(sentences) -> float` を実装（文字数平均、空なら 0.0）。
- **Step 10**: 同じファイルに `detect_banned(text, banned: list[str]) -> list[str]` を実装（banned の各語が text に含まれれば収集）。banned は呼び出し側が SOUL.md から渡す。
- **Step 11**: 同じファイルに `read_banned_from_soul(book_id, branch_id=1) -> list[str]` を実装。`SOUL.md` の `## 禁則事項` セクションを `writer.read_file_safe` + セクション抽出で読み、ハイフン行を収集。
- **Step 12**: 同じファイルに `analyze_style(content, book_id, branch_id=1) -> dict` を実装。Step6-11 を呼び、`{"top_words":[], "avg_len":0.0, "particles":{}, "banned_hits":[]}` を返す。
- **Step 13**: 同じファイルに `update_style_learned(book_id, ep_num, content, branch_id=1) -> Path` を実装。`analyze_style` 結果を `writer.update_section` で 5 セクションへ書き込み、`## 直近サンプル文` には最初の 1 文を追記（過去分は残す）。戻り値はファイル Path。
- **Step 14**: `tests/unit/test_style_learning.py` を新規作成。短い日本語段落（3 文）を `analyze_style` に渡し、`avg_len>0` かつ `top_words` が非空・`particles` に `は` 等を含むことを `assert`。
- **Step 15**: 同じテストに `update_style_learned` のケースを追加。書き込み後 `STYLE_LEARNED.md` を Read し、`## 平均文長` セクションに数値文字列が含まれることを `assert`。
- **Step 16**: `src/filesystem_memory/auto_update.py` を Read。`update_style_learned` を import し、`update_story_summary` の直後（L38-42 付近）から呼べるよう関数シグネチャを確認（book_id, ep_num, summary, branch_id を受け取るので content が必要）。
- **Step 17**: `src/backend/database/repositories/chapter.py` の `create_chapter` 内 try ブロック（L72-87）で、`update_story_summary` の直後に `from src.services.style_learning import update_style_learned` を import し、`update_style_learned(book_id, ep_num, content, branch_id=branch_id)` を呼ぶ。既存の `try/except` に内包。
- **Step 18**: `tests/unit/test_chapter_style_hook.py` を新規作成。`ChapterRepository` をモック DB で動かすのは重いので、代わりに `update_style_learned` が `content` 無しで落ちないこと、`create_chapter` のフック行に到達することを `monkeypatch` で検証（関数が呼ばれた回数を数える）。
- **Step 19**: `src/services/style_prompt.py` を新規作成。関数 `build_style_injection(book_id, branch_id=1) -> str` を実装。`STYLE_LEARNED.md` を Read し、`## 頻出語` / `## 平均文長` / `## 助詞傾向` / `## 禁則語` の 4 セクション本文を抜き出して `[学習済み文体]` ブロックに整形。ファイル不在時は `""` を返す。
- **Step 20**: `tests/unit/test_style_prompt.py` を新規作成。`STYLE_LEARNED.md` を用意して `build_style_injection` を呼び、戻り文字列が `頻出語` と `禁則語` を含むことを `assert`。
- **Step 21**: `src/services/writing_services.py` の `_phase_prepare_context`（L277）冒頭で、`book_id = ctx.book.id if ctx.book else (ctx.book_id or 0)` と `branch_id = ctx.branch_id` を取得。
- **Step 22**: 同じ関数内で `from src.services.style_prompt import build_style_injection` し、`injection = build_style_injection(book_id, branch_id)` を計算。`if injection: sys_inst = sys_inst + "\n\n" + injection`（L281 の `sys_inst` 引数を上書き）。
- **Step 23**: `src/backend/routers/workspace.py` に `POST /api/workspace/{book_id}/learn_style` を追加。body で `ep_num`, `content` を受け取り `update_style_learned` を呼ぶ（手動学習用）。既存ルータの `APIRouter` に追記。
- **Step 24**: `docs/style_learning.md` を新規作成。仕組み・出力ファイル・注入タイミング・手動 API を 20 行程度で記述。

**Phase A 完了条件**: `init_workspace` で `STYLE_LEARNED.md` が出る / 章生成で自動追記される / 生成 `sys_inst` に `[学習済み文体]` が入る / 単体テスト 6 本が緑。

---

## Phase B — 提案 2: 決定論的整合性エンジンの LLM Guardian 完全統合（Step 25-42）

生成時の `sys_inst` へ整合性指摘を「強制注入」。却下済みは除外。既存 `guardian_hook` を 1 箇所で呼ぶだけ。

- **Step 25**: `src/consistency/guardian_hook.py` を Read。`get_consistency_prompt_injection(book_id, branch_id=1, ep_num=None)` のシグネチャと戻り（空なら `""`）を確認。
- **Step 26**: `src/consistency/checkers/base.py` の `CheckContext` が `book_id/branch_id/ep_num` を持つことを確認（提案 3 で content 渡しが必要ならここを拡張するが、今回は既存のまま）。
- **Step 27**: `config/project_context.py` を Read。`SETTINGS` 既定値 dict（または `get_setting` のデフォルト）に `"consistency_guardian_enabled": True` を追加（既存 key の並びの末尾へ 1 行）。
- **Step 28**: `src/services/writing_services.py` の `_phase_prepare_context` 内（Step21-22 の直後）で `from src.consistency.guardian_hook import get_consistency_prompt_injection` を import。
- **Step 29**: 同じ位置で `if ProjectContext.get_setting("consistency_guardian_enabled", True):` を評価し、`cinjection = get_consistency_prompt_injection(book_id, branch_id, ep_num)` を取得。`ep_num` は引数の `ep_num` をそのまま渡す。
- **Step 30**: `if cinjection: sys_inst = sys_inst + "\n\n" + cinjection`（Step22 の style 注入より後に連結。順序: 文体 → 整合性）。
- **Step 31**: `src/services/writing_services.py` の `build_sys_inst`（L54）は変更なし。Step30 で渡ってきた `sys_inst` 文字列がそのまま組み込まれることを確認（既に `parts=[self.sys_inst]` で含まれる）。
- **Step 32**: `tests/unit/test_consistency_guardian_injection.py` を新規作成。`monkeypatch.setattr("src.consistency.guardian_hook.get_consistency_prompt_injection", lambda *a, **k: "[整合性チェック結果]\n1. [HIGH] x: y")` で差し替え。
- **Step 33**: 同じテストで `GenerationLoopManager` を軽量構築（repo/llm/pm/critique/narrative/config はダミー）し、`_phase_prepare_context(ep_num=1, ctx=dummy_ctx, sys_inst="BASE", fw_prompt="", is_easy_mode=False, reporter=None)` を呼び、`gen_ctx.sys_inst` に `"[整合性チェック結果]"` が含まれることを `assert`。
- **Step 34**: 同じテストで `get_consistency_prompt_injection` が `""` を返す場合、`sys_inst` が `"BASE"` のまま（余計な文字が付かない）ことを `assert`。
- **Step 35**: `config/project_context.py` の `consistency_guardian_enabled` を `False` にして（テスト内 `set_setting` で）注入されないことを Step33 と同様に `assert`（トグル検証）。
- **Step 36**: `src/backend/routers/consistency.py` を Read。`GET /api/consistency/{book_id}/inject` を追加（既存ルータに 1 エンドポイント）。`ep_num` をクエリで受け `get_consistency_prompt_injection` の結果を `{"injection": str}` で返す。
- **Step 37**: `src/backend/server.py` の `router_modules` に `"src.backend.routers.consistency"` が未登録なら追加（既に登録済みならスキップ。登録確認のみ）。
- **Step 38**: `tests/unit/test_consistency_router_inject.py` を新規作成。`fastapi.TestClient` で `/api/consistency/1/inject?ep_num=2` を叩き、200 と `injection` キーを `assert`（エンジンは実ファイルなしで空文字を返す想定）。
- **Step 39**: `src/consistency/injector.py` の `format_findings_for_prompt` を Read。`max_findings=20` の制限を確認（トークン爆発防止）。変更なし。
- **Step 40**: `docs/consistency.md`（または既存 `docs/implementation_report.md` の該当節）に「生成時強制注入」の記述を追記（10 行）。
- **Step 41**: `pytest tests/unit -q` を実行し、Phase A/B 関連が全て緑であることを確認。赤字が `config/settings.py` の `ConfigManager` 絡みのみであることを確認（それ以外は Bug）。
- **Step 42**: `CHANGELOG.md` に「提案 2: 整合性 Guardian を執筆 sys_inst へ強制注入（フラグ `consistency_guardian_enabled`）」の 1 行を追加。

**Phase B 完了条件**: 章生成の system prompt に整合性指摘が入る / フラグで on-off / 却下済みは `filters.filter_intentional` 経由で除外済み / 単体テスト 4 本が緑。

---

## Phase C — 提案 3: 章単位の自動改稿ループ（Step 43-72）

生成直後に整合性チェック→指摘があれば同一プロンプトで最大 2 回リライト→再チェック→合格で確定。Story Maker 方式の簡易版（スコアなし、指摘ベース）。

- **Step 43**: `src/services/writing_services.py` の `execute_generation_loop`（L84-275）を通読。`final_content` が `_phase_drafting`（L326）の戻りで確定し、その後 `_phase_audit`（L366）へ渡る構造をメモ。
- **Step 44**: `src/consistency/checkers/base.py` の `CheckContext` に `content: Optional[str] = None` フィールドを追加（L8-14）。これで「草稿を FS に書かずにメモリ内チェック」が可能になる。
- **Step 45**: `src/consistency/findings.py` を Read。`Finding.key()` で重複排除されることを確認（提案 3 の「改善したか」判定に使う）。
- **Step 46**: `src/consistency/engine.py` を Read。既存 `run(context)` は `content` を使わないが、各チェッカーが `context.content` を見る場合に備え何も壊さないことを確認（read only）。
- **Step 47**: `src/services/consistency_revision.py` を新規作成。関数 `check_draft(findings_filter, book_id, branch_id, ep_num, content) -> list[Finding]` を実装。`ConsistencyEngine(get_default_checkers())` で `CheckContext(book_id, branch_id, ep_num, content)` を走らせ、`filter_intentional` + `get_all_dismissals` で絞る。
- **Step 48**: 同じファイルに `format_findings_for_rewrite(findings) -> str` を実装。`injector.format_findings_for_prompt` を呼び、接頭辞を `[改稿指示]` に変えて返す（使い回し）。
- **Step 49**: 同じファイルに `MAX_REVISIONS = 2` 定数を追加。
- **Step 50**: 同じファイルに `build_rewrite_prompt_suffix(findings) -> str` を実装。「以下の整合性指摘を修正して全文を書き直してください（プロット・世界観は維持）：」＋指摘を返す。
- **Step 51**: `tests/unit/test_consistency_revision.py` を新規作成。`monkeypatch` で `ConsistencyEngine.run` が 1 回目は指摘 1 件、2 回目は `[]` を返すようにし、`check_draft` の戻り件数を `assert`。
- **Step 52**: `src/services/writing_services.py` に `_phase_consistency_revision(self, ep_num, ctx, content, gen_ctx, temp, reporter) -> tuple[str, bool]` を新規メソッドとして追加（L365 の `_phase_audit` 直前あたり）。
- **Step 53**: `_phase_consistency_revision` 内で `from src.services.consistency_revision import check_draft, build_rewrite_prompt_suffix, MAX_REVISIONS` を import。
- **Step 54**: ループ骨子を書く：`revised = content; ok = True; for attempt in range(MAX_REVISIONS): findings = check_draft(...); if not findings: break; suffix = build_rewrite_prompt_suffix(findings); revised = await self._rewrite_once(ep_num, revised, suffix, gen_ctx, temp, reporter)`。
- **Step 55**: `_rewrite_once` メソッドを追加。`revised` を `gen_ctx.build_fw_prompt(suffix)` の `suffix` として `_draft_episode_parts` に渡し、さらに `_polishing_pass` を通す（既存メソッドの再利用）。戻りは修正後文字列。
- **Step 56**: `_phase_consistency_revision` の戻りを `(revised, len(findings_for_final)==0)` とする。`findings_for_final` は最終ループ後の `check_draft` 結果。
- **Step 57**: `execute_generation_loop` 内で、`_phase_drafting` の戻り `final_content` を取得した直後（L364 の後）に、`_phase_consistency_revision` を呼ぶよう 1 行追加：`if ProjectContext.get_setting("auto_revision_enabled", False): final_content, rev_ok = await self._phase_consistency_revision(ep_num, ctx, final_content, gen_ctx, temp, reporter)`。
- **Step 58**: `config/project_context.py` に `"auto_revision_enabled": False` と `"auto_revision_max": 2` を追加（既定オフ。危険なので明示オプトイン）。
- **Step 59**: `_phase_consistency_revision` で `reporter` があり `rev_ok` が False の場合、「⚠️ 自動改稿で指摘を全消去できませんでした（N 件残存）」を `warning` 報告。
- **Step 60**: 同じく `reporter` があり修正が 0 件で通過した場合、「✅ 自動改稿: 整合性指摘なし」を `info` 報告（任意だが可観測性のため）。
- **Step 61**: `_phase_consistency_revision` のループに `try/except` を 1 つだけ置き、例外時は元の `content` を返して `ok=True`（安全フォールバック、生成を止めない）。
- **Step 62**: `tests/unit/test_auto_revision_loop.py` を新規作成。`GenerationLoopManager` をダミー LLM（決まった文字列を返す）で構築。`monkeypatch` で `check_draft` が [指摘1件]→[指摘1件]→[] を返すよう順次切替。
- **Step 63**: 同じテストで `_phase_consistency_revision` を直接呼び、`_rewrite_once`（＝LLM 呼び出し）が **2 回** 発生し、最終 `ok=True` になることを `assert`（モック呼び出し回数を数える）。
- **Step 64**: 同じテストで `check_draft` が常に指摘なしを返す場合、`_rewrite_once` が **0 回** で `ok=True` になることを `assert`（無駄な生成なし）。
- **Step 65**: `auto_revision_enabled=False` のとき `execute_generation_loop` が `_phase_consistency_revision` を呼ばない（LLM 追加呼び出し 0）ことを `assert`。
- **Step 66**: `src/backend/routers/workspace.py`（または `consistency.py`）に `POST /api/workspace/{book_id}/auto_revision_preview` を追加。body で `ep_num`, `content` を受け、`check_draft` 結果を JSON で返す（手動プレビュー・デバッグ用）。
- **Step 67**: `tests/unit/test_auto_revision_preview.py` を新規作成。TestClient で preview を叩き、指摘リストが `list` で返ることを `assert`。
- **Step 68**: `src/frontend/src/components/BookWorkspace.tsx` を Read。タブに「自動改稿（β）」の小ボタンを 1 つ追加（既存タブ追加パターンに倣う）。
- **Step 69**: `src/frontend/src/hooks/useAutoRevision.ts` を新規作成。`auto_revision_preview` を呼ぶフック（既存 `useConsistencyCheck.ts` の構造をコピー改変）。
- **Step 70**: `docs/auto_revision.md` を新規作成。仕組み（最大 2 回・指摘ベース・スコアなし）、フラグ `auto_revision_enabled` の既定オフ、手動プレビュー API を 25 行で記述。
- **Step 71**: `pytest tests/unit -q` を実行。Phase A/B/C 全て緑、かつ `config/settings.py` 以外の収集エラーが 0 であることを確認。
- **Step 72**: `CHANGELOG.md` に「提案 3: 章単位自動改稿ループ（最大 2 回、フラグ `auto_revision_enabled` 既定オフ）」の 1 行を追加。`README.md` の機能一覧に 3 機能を追記。

**Phase C 完了条件**: `auto_revision_enabled=True` で指摘あり時のみ最大 2 回リライト／指摘なし時は 0 回／例外時は元稿フォールバック／単体テスト 4 本が緑。

---

## 2. 受け入れ基準（全体）

1. `workspaces/book_{id}/branch_{bid}/STYLE_LEARNED.md` が章生成ごとに更新される。
2. 執筆 `sys_inst` に `[学習済み文体]` と `[整合性チェック結果]` の両方が入る（フラグ on 時）。
3. `auto_revision_enabled=True` のときのみ、整合性指摘を含む章が自動で最大 2 回リライトされる。
4. すべての新機能に単体テストがあり、`pytest tests/unit -q` が緑（既知の `ConfigManager` issue 除く）。
5. 新規 DB マイグレーション不要。新規外部依存なし（形態素解析ライブラリ未使用）。

---

## 3. リスクとロールバック

- **トークン増**: 注入が重なると `sys_inst` が長くなる。`injector.max_findings=20` と `auto_revision_max=2` で上限固定。必要なら `consistency_guardian_enabled` / `auto_revision_enabled` を `False` に戻すだけで即無効化。
- **無限リライト**: `MAX_REVISIONS=2` のハードキャップと `try/except` フォールバックで防止済み。
- **文体学習の汚染**: `STYLE_LEARNED.md` は別ファイルなので `SOUL.md` を壊さない。壊れても `init_workspace` で再生成可能（ただし学習履歴は失われる）。
- **ロールバック手順**: 各 Phase は独立。Phase C を止めたければ `auto_revision_enabled=False` のみ。Phase B は `consistency_guardian_enabled=False`。Phase A は `chapter.py` の hook 行 1 行を削除。
