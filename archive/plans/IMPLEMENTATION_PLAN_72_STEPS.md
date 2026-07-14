# 未完了タスク 実装計画書（72ステップ）

## 現在の状態検証結果

| カテゴリ | 状態 | 件数 |
|---------|------|------|
| passed | ✅ | 203 |
| skipped | ⏭️ | 8 |
| xfailed | ⚠️ | 4 |
| failed | ❌ | 0 |

### xfailed テスト一覧（修正対象）

| # | ファイル | テスト名 | 原因 |
|---|---------|---------|------|
| E-6a | `tests/integration/test_workflow.py` | `test_full_auto_workflow_easy_mode` | `UltraFastWorldBible` バリデーション失敗 |
| E-6b | `tests/integration/test_workflow.py` | `test_full_auto_workflow_normal_mode` | 同上 |
| E-6c | `tests/integration/test_workflow.py` | `test_full_auto_workflow_api_failure` | 同上 |
| E-7 | `tests/integration/test_plot_workflow.py` | `test_plot_langgraph_workflow` | `langgraph` 未インストール |

---

## Phase 1: 事前確認（Step 1-10）

### Step 1: UltraFastWorldBible モデルの場所を確認
- ファイル: `src/models/bible.py`
- タスク: `class UltraFastWorldBible` の定義を読む
- 検証: `grep -n "class UltraFastWorldBible" src/models/bible.py` で行番号が返る

### Step 2: UltraFastWorldBible の必須フィールドを確認
- タスク: `bible_core` と `full_story_roadmap` が `Field(...)`（必須）であることを確認
- 検証: `sed -n '99,105p' src/models/bible.py` で2つのフィールドが見える

### Step 3: WorldBibleCore モデルの必須フィールドを確認
- ファイル: `src/models/bible.py`
- タスク: `class WorldBibleCore` の必須フィールド一覧を読む
- 検証: `title`, `concept`, `genre`, `style_key` などが必須であることを確認

### Step 4: bible_service.py の UltraFastWorldBible 使用箇所を確認
- ファイル: `src/services/bible_service.py`
- タスク: `UltraFastWorldBible.model_validate(res.metadata)` がどこにあるか確認
- 検証: `grep -n "UltraFastWorldBible.model_validate" src/services/bible_service.py` で行番号が返る

### Step 5: test_workflow.py の LLM モック応答を確認
- ファイル: `tests/integration/test_workflow.py`
- タスク: "世界観設定の生成" に対する `mock_llm.add_json_response` の内容を読む
- 検証: 応答が `world_background`, `magic_system`, `social_structure` のみであることを確認

### Step 6: langgraph のインストール状態を確認
- タスク: `pip show langgraph` を実行
- 検証: エラーになる（未インストール）ことを確認

### Step 7: PlotGraphManager の node_align_context を確認
- ファイル: `src/backend/workflows/plot_langgraph.py`
- タスク: `node_align_context` メソッドの存在を確認
- 検証: `grep -n "def node_align_context" src/backend/workflows/plot_langgraph.py` で行番号が返る

### Step 8: MockEngine の場所を確認
- ファイル: `tests/mocks/mock_engine.py`
- タスク: `class MockEngine` の定義を読む
- 検証: ファイルが存在し、クラス定義がある

### Step 9: 現在の xfailed 一覧を再確認
- コマンド: `pytest tests/integration/test_workflow.py tests/integration/test_plot_workflow.py -v --tb=no 2>&1 | grep XFAIL`
- 検証: 4 件の XFAIL が表示される

### Step 10: 現在のブランチを確認
- コマンド: `git branch --show-current`
- 検証: ブランチ名が表示される

---

## Phase 2: E-6 修正（test_workflow.py 3テスト）（Step 11-40）

### Step 11: "世界観設定の生成" 応答に bible_core を追加（easy_mode）
- ファイル: `tests/integration/test_workflow.py`
- タスク: 29-33行目の `mock_llm.add_json_response("世界観設定の生成", {...})` の内容を `bible_core` 形式に変更
- 変更内容:
  ```python
  mock_llm.add_json_response("世界観設定の生成", {
      "bible_core": {
          "title": "テスト用の異世界",
          "concept": "剣と魔法が支配する世界",
          "genre": "ファンタジー",
          "style_key": "dark_fantasy",
          "keywords": ["剣", "魔法"],
          "engine_key": "novel",
          "world_settings": {"tension_threshold": 0.5, "tension_gain": 0.3},
          "mc_profile": {"name": "主人公", "surface_persona": "一見平凡", "inner_conflict": "野望", "iron_constraint": "ルール遵守"},
          "arcs": [{"title": "追放", "summary": "主人公が追放される"}]
      },
      "full_story_roadmap": [{"ep_num": 1, "title": "理不尽な追放", "synopsis": "アレンはギルドから追放される"}]
  })
  ```
- 検証: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_easy_mode -q --tb=short` → 別のエラーになる（期待通り）

### Step 12: "世界観設定の生成" 応答に bible_core を追加（normal_mode）
- ファイル: `tests/integration/test_workflow.py`
- タスク: 138-142行目の同じ応答を同じ形式に変更
- 検証: 編集内容が easy_mode と一致することを確認

### Step 13: "世界観設定の生成" 応答に bible_core を追加（api_failure）
- ファイル: `tests/integration/test_workflow.py`
- タスク: api_failure テストは "世界観設定の生成" で例外を発生させるため、この変更は不要
- 検証: `grep -A3 "test_full_auto_workflow_api_failure" tests/integration/test_workflow.py` で例外設定のみであることを確認

### Step 14: easy_mode テストを単体実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_easy_mode -q --tb=short`
- 検証: 別のエラーが発生（bible_core 追加で UltraFastWorldBible 検証は通った）

### Step 15: easy_mode の次のエラーを確認
- タスク: エラーメッセージを読んで次の問題を特定
- 予想: プロット生成やその他のステップで失敗する可能性

### Step 16: easy_mode の失敗理由を分析
- タスク: トレースバックを確認し、どこで失敗しているか特定
- 検証: エラー行番号とメッセージを記録

### Step 17: easy_mode に追加のモック応答が必要か確認
- タスク: ワークフローが要求する全ての LLM プロンプトに対してモック応答があるか確認
- 検証: `mock_llm.add_json_response` / `add_text_response` の数を数える

### Step 18: 必要な追加モックを特定
- タスク: エラーから、どのプロンプト応答が不足しているか特定
- 検証: 不足しているプロンプト名をリストアップ

### Step 19: easy_mode に不足モックを追加
- ファイル: `tests/integration/test_workflow.py`
- タスク: 特定した不足プロンプトに対するモック応答を追加
- 検証: 編集後にテストを実行し、次のエラーに進む

### Step 20: easy_mode を再実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_easy_mode -q --tb=short`
- 検証: 別のエラーになる、または PASS

### Step 21: easy_mode が still fail の場合、エラーを確認
- タスク: 新しいエラーを読む
- 検証: エラー内容を記録

### Step 22: normal_mode にも同じ bible_core 修正を適用
- ファイル: `tests/integration/test_workflow.py`
- タスク: normal_mode の "世界観設定の生成" 応答も同じ形式に変更
- 検証: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_normal_mode -q --tb=short`

### Step 23: normal_mode の不足モックを特定
- タスク: easy_mode と同じパターンで不足モックを特定
- 検証: エラーから不足プロンプトをリストアップ

### Step 24: normal_mode に不足モックを追加
- ファイル: `tests/integration/test_workflow.py`
- タスク: 不足プロンプトに対するモック応答を追加
- 検証: テストを再実行

### Step 25: normal_mode を再実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_normal_mode -q --tb=short`
- 検証: PASS または次のエラー

### Step 26: api_failure テストを確認
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_api_failure -q --tb=short`
- 検証: エラー内容を確認

### Step 27: api_failure の bible_core 修正
- ファイル: `tests/integration/test_workflow.py`
- タスク: api_failure は "世界観設定の生成" で例外を発生させるため、例外発生前に bible_core 形式が必要
- 検証: モック例外設定の前に bible_core 形式の応答を追加

### Step 28: api_failure を再実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_api_failure -q --tb=short`
- 検証: PASS または次のエラー

### Step 29: 3テストをまとめて実行
- コマンド: `pytest tests/integration/test_workflow.py -q --tb=short`
- 検証: 3 passed

### Step 30: xfail マーカーを除去（easy_mode）
- ファイル: `tests/integration/test_workflow.py`
- タスク: 26行目の `@pytest.mark.xfail(...)` を削除
- 検証: `grep -n "xfail" tests/integration/test_workflow.py` で2件になる

### Step 31: xfail マーカーを除去（normal_mode）
- ファイル: `tests/integration/test_workflow.py`
- タスク: 135行目の `@pytest.mark.xfail(...)` を削除
- 検証: `grep -n "xfail" tests/integration/test_workflow.py` で1件になる

### Step 32: xfail マーカーを除去（api_failure）
- ファイル: `tests/integration/test_workflow.py`
- タスク: 247行目の `@pytest.mark.xfail(...)` を削除
- 検証: `grep -n "xfail" tests/integration/test_workflow.py` で0件になる

### Step 33: 3テストを xfail なしで実行
- コマンド: `pytest tests/integration/test_workflow.py -q --tb=short`
- 検証: 3 passed

### Step 34: 他のテストへの影響を確認
- コマンド: `pytest tests/integration/test_workflow.py tests/integration/test_erotic_refine_workflow.py tests/integration/test_erotic_full_pipeline.py -q --tb=short`
- 検証: 全て PASS

---

## Phase 3: E-7 修正（test_plot_workflow.py）（Step 35-50）

### Step 35: langgraph のインストールを試みる
- コマンド: `pip install langgraph`
- 検証: `pip show langgraph` でバージョンが表示される

### Step 36: langgraph インストール後のテスト実行
- コマンド: `pytest tests/integration/test_plot_workflow.py -q --tb=short`
- 検証: エラー内容が変わる（langgraph 関連以外）

### Step 37: エラー内容を確認
- タスク: 新しいエラーを読む
- 予想: `MockEngine` に `node_align_context` がない、または他のモック不足

### Step 38: MockEngine の実装を確認
- ファイル: `tests/mocks/mock_engine.py`
- タスク: `class MockEngine` のメソッド一覧を確認
- 検証: `grep "def " tests/mocks/mock_engine.py` でメソッドリスト

### Step 39: node_align_context が必要か確認
- タスク: `PlotGraphManager.__init__` で `self.ctx_mgr` を使っている箇所を確認
- 検証: `grep -n "self.ctx_mgr" src/backend/workflows/plot_langgraph.py`

### Step 40: node_align_context の実装を確認
- ファイル: `src/backend/workflows/plot_langgraph.py`
- タスク: `def node_align_context` の定義を読む
- 検証: `grep -n "def node_align_context" src/backend/workflows/plot_langgraph.py` で行番号

### Step 41: node_align_context が engine の何を使うか確認
- タスク: メソッド内で `self.engine.xxx` や `self.ctx_mgr.xxx` を呼んでいる箇所を確認
- 検証: 必要な属性をリストアップ

### Step 42: MockEngine に不足メソッドを追加
- ファイル: `tests/mocks/mock_engine.py`
- タスク: `node_align_context` が必要とするメソッドを `MockEngine` に追加
- 検証: 編集後にテストを実行

### Step 43: test_plot_workflow.py を再実行
- コマンド: `pytest tests/integration/test_plot_workflow.py -q --tb=short`
- 検証: 別のエラーになる、または PASS

### Step 44: 残存エラーを確認
- タスク: エラー内容を読む
- 検証: エラー行番号とメッセージを記録

### Step 45: モック応答の追加が必要か確認
- タスク: LLM モック応答が不足していないか確認
- 検証: ワークフローが LLM に要求するプロンプトと、テストのモック応答を比較

### Step 46: 不足モックがあれば追加
- ファイル: `tests/integration/test_plot_workflow.py`
- タスク: 不足しているプロンプト応答を追加
- 検証: テストを再実行

### Step 47: test_plot_workflow.py を再実行
- コマンド: `pytest tests/integration/test_plot_workflow.py -q --tb=short`
- 検証: PASS または次のエラー

### Step 48: xfail マーカーを除去
- ファイル: `tests/integration/test_plot_workflow.py`
- タスク: 8行目の `@pytest.mark.xfail(...)` を削除
- 検証: `grep -n "xfail" tests/integration/test_plot_workflow.py` で0件

### Step 49: xfail なしで再実行
- コマンド: `pytest tests/integration/test_plot_workflow.py -q --tb=short`
- 検証: 1 passed

### Step 50: xfail 全除去を確認
- コマンド: `grep -rn "xfail" tests/integration/ | grep -v __pycache__`
- 検証: 0 件（または状態テスト等の別目的 xfail のみ）

---

## Phase 4: 統合検証（Step 51-60）

### Step 51: unit テスト実行
- コマンド: `pytest tests/unit -q --tb=short`
- 検証: 129 passed, 0 failed

### Step 52: integration テスト実行
- コマンド: `pytest tests/integration -q --ignore=tests/integration/state_tests --tb=short`
- 検証: 0 failed

### Step 53: zamaa テスト実行
- コマンド: `pytest tests/test_zamaa_generation.py tests/test_zamaa_injection.py -q --tb=short`
- 検証: 2 passed

### Step 54: vector_store / verbose_fixture / config テスト実行
- コマンド: `pytest tests/test_vector_store_lifecycle.py tests/test_verbose_fixture.py tests/test_config*.py -q --tb=short`
- 検証: 全て PASS

### Step 55: フルスイート実行
- コマンド: `pytest tests/unit tests/integration tests/test_zamaa_generation.py tests/test_zamaa_injection.py tests/test_vector_store_lifecycle.py tests/test_verbose_fixture.py tests/test_config*.py --ignore=tests/integration/state_tests --ignore=tests/ui -q`
- 検証: 207 passed, 8 skipped, 0 xfailed, 0 failed

### Step 56: CI lint 確認
- コマンド: `ruff check tests/integration/test_workflow.py tests/integration/test_plot_workflow.py tests/mocks/mock_engine.py`
- 検証: エラーなし（または既知の警告のみ）

### Step 57: CI typecheck 確認
- コマンド: `mypy tests/integration/test_workflow.py tests/integration/test_plot_workflow.py tests/mocks/mock_engine.py`
- 検証: エラーなし

### Step 58: git status 確認
- コマンド: `git status --short`
- 検証: 変更ファイルが正しくリストされる

### Step 59: git diff 確認
- コマンド: `git diff tests/integration/test_workflow.py tests/integration/test_plot_workflow.py tests/mocks/mock_engine.py`
- 検証: 変更内容が正しい

### Step 60: git add 実行
- コマンド: `git add tests/integration/test_workflow.py tests/integration/test_plot_workflow.py tests/mocks/mock_engine.py`
- 検証: `git status` で staged になる

---

## Phase 5: ドキュメント更新（Step 61-65）

### Step 61: IMPLEMENTATION_PLAN_PHASE_E_APP_CONTRACT_BUGS.md 更新
- ファイル: `IMPLEMENTATION_PLAN_PHASE_E_APP_CONTRACT_BUGS.md`
- タスク: E-6, E-7 を「完了」に変更
- 検証: ファイル末尾の進捗レポートが更新されている

### Step 62: IMPLEMENTATION_PLAN_CI_INTEGRATION.md 更新
- ファイル: `IMPLEMENTATION_PLAN_CI_INTEGRATION.md`
- タスク: 最終検証結果を 207 passed / 0 xfailed に更新
- 検証: `grep "passed" IMPLEMENTATION_PLAN_CI_INTEGRATION.md` で新しい数字

### Step 63: CHANGELOG.md または実装レポート更新
- ファイル: `IMPLEMENTATION_PLAN_PHASE_E_APP_CONTRACT_BUGS.md`（実装レポートセクション）
- タスク: E-6, E-7 の修正内容を記載
- 検証: レポートに記載内容がある

### Step 64: コミットメッセージ作成
- タスク: 以下のコミットメッセージを作成
  ```
  fix: resolve 4 xfailed integration tests (E-6, E-7)

  - E-6: fix UltraFastWorldBible mock responses in test_workflow.py
    (3 tests: easy_mode, normal_mode, api_failure)
  - E-7: install langgraph + fix MockEngine for PlotGraphManager
    (1 test: test_plot_langgraph_workflow)
  ```
- 検証: コミットメッセージが適切

### Step 65: コミット実行
- コマンド: `git commit -m "fix: resolve 4 xfailed integration tests (E-6, E-7)"
- 検証: `git log --oneline -1` でコミットメッセージが表示

---

## Phase 6: 最終確認（Step 66-72）

### Step 66: コミット後のテスト再実行
- コマンド: `pytest tests/unit tests/integration tests/test_zamaa_generation.py tests/test_zamaa_injection.py tests/test_vector_store_lifecycle.py tests/test_verbose_fixture.py tests/test_config*.py --ignore=tests/integration/state_tests --ignore=tests/ui -q`
- 検証: 207 passed, 8 skipped, 0 xfailed, 0 failed

### Step 67: CI yml の unit-test / integration-test ジョブ確認
- ファイル: `.github/workflows/ci.yml`
- タスク: 両ジョブが blocking（continue-on-error なし）であることを確認
- 検証: `grep -A5 "unit-test:" .github/workflows/ci.yml` で `continue-on-error` がない

### Step 68: CI yml の xfail 許容確認
- タスク: CI が xfail を失敗と判定しないことを確認
- 検証: `grep -i "xfail\|xpass" .github/workflows/ci.yml`

### Step 69: 全テストの安定性確認（2回実行）
- コマンド: 2回連続でフルスイート実行
- 検証: 両方とも 207 passed, 8 skipped, 0 xfailed, 0 failed

### Step 70: ファイル変更数の確認
- コマンド: `git diff --stat HEAD~1`
- 検証: 変更ファイルが想定通り（3ファイル程度）

### Step 71: ブランチの状態確認
- コマンド: `git log --oneline -3`
- 検証: 最新コミットが E-6/E-7 fix である

### Step 72: タスク完了サマリー作成
- タスク: 以下のサマリーを `IMPLEMENTATION_PLAN_PHASE_E_APP_CONTRACT_BUGS.md` に追記
  ```
  ## 完了サマリー（2026-07-13）

  ### 修正テスト一覧
  | ステップ | テスト | 修正内容 | 結果 |
  |---------|--------|---------|------|
  | E-6a | test_full_auto_workflow_easy_mode | bible_core モック応答修正 | ✅ PASS |
  | E-6b | test_full_auto_workflow_normal_mode | bible_core モック応答修正 | ✅ PASS |
  | E-6c | test_full_auto_workflow_api_failure | bible_core モック応答修正 | ✅ PASS |
  | E-7 | test_plot_langgraph_workflow | langgraph インストール + MockEngine 補完 | ✅ PASS |

  ### 最終検証結果
  - 207 passed, 8 skipped, 0 xfailed, 0 failed
  - CI: green（全ジョブ passing）
  ```
- 検証: サマリーがファイル末尾に追加されている

---

## 実行上の注意

1. **1ステップずつ実行**: 各ステップ完了後に検証コマンドを実行し、PASS してから次へ
2. **エラー時は戻る**: 検証が FAIL したら直前のステップに戻り、変更を確認
3. **ファイルパスは絶対パス**: `cd /workspaces/autonovel && ...` で実行
4. **git commit は最終段階**: Step 65 まで全て PASS してからコミット
5. **不明点は Plan を参照**: 各ステップに検証コマンドが書いてあるので、それを実行
