# Phase E: アプリ契約バグ修正 実装計画書

## 背景
Phase A-D で CI/統合テスト基盤を安定化し、195 passed / 8 skipped / 12 xfailed / 0 failed に到達。
残る **12 の `xfail` テスト** はインフラ問題ではなく **アプリ側の本質的契約バグ**（API シグネチャ変更、enum 検証不整合、モック配線不一致）であり、段階的修正が必要。

---

## 対象: 12 の `xfail` テスト一覧

| # | ファイル | テスト関数 | 原因分類 | 概要 |
|---|---|---|---|---|
| 1 | `test_erotic_full_pipeline.py` | `test_nocturn_preset_censorship` | Mock契約 | 検閲モック応答に期待する `◆` マーカーが含まれない |
| 2 | `test_erotic_full_pipeline.py` | `test_integrity_checker_clothing` | Mock契約 | 検閲アサーション（`◆` 含有）がモック応答と不一致 |
| 3 | `test_erotic_full_pipeline.py` | `test_refine_erotic_workflow_mock` | API契約 | `generate_json` 戻り値 3タプルだがテスト側で 2値アンパック |
| 4 | `test_erotic_refine_workflow.py` | `test_refine_erotic_workflow_success` | API契約 | `BaseWorkflow.__init__` が `engine` 必須化だがテストは無引数構築 |
| 5 | `test_erotic_refine_workflow.py` | `test_refine_erotic_workflow_failure` | API契約 | 同上 |
| 6 | `test_plot_workflow.py` | `test_plot_langgraph_workflow` | API契約 | `PlotGraphManager` に `node_align_context` 属性なし / langgraph 未インストール |
| 7 | `test_tension_integration.py` | `test_tension_integration_workflow` | Mock配線 | JSON デコードに `AsyncMock` が渡される（モック配線不一致） |
| 8 | `test_tension_integration.py` | `test_tension_integration_success` | Mock配線 | 同上 |
| 9 | `test_workflow.py` | `test_full_auto_workflow_easy_mode` | テスト分離 | 単独実行時 pass、全体実行時 fail（グローバル DB / DI コンテナ漏洩） |
|10 | `test_workflow.py` | `test_full_auto_workflow_normal_mode` | テスト分離 | 同上 |
|11 | `test_workflow.py` | `test_full_auto_workflow_api_failure` | テスト分離 | 同上 |
|12 | `test_verbose_fixture.py` | `test_verbose_fixture_get_verbose_spec` | Enum検証 | `SharpEdgeSpec` が `sharp_conflict` を未知の角として拒否 |

---

## 修正方針・優先度

### Priority 1: API契約不整合（高確実・低リスク）
テストコードのみの修正で解決するもの。実装側の正しいAPIに合わせる。
- **#4, #5** `BaseWorkflow.__init__` への `engine` 引数追加 → テスト側で正しい引数渡す
- **#3** `generate_json` 戻り値 3タプル → テスト側で 3値受け取り
- **#12** `SharpEdgeSpec` に `sharp_conflict` を追加 OR テストで有効な edge_type 使用

### Priority 2: Mock契約・配線不整合（中確実・中リスク）
モック実装とテスト期待値の齟齬。
- **#1, #2** 検閲モックが `◆` を出力するよう `MockGeminiApiClient` のデフォルト応答修正
- **#7, #8** `test_tension_integration` の JSON デコードが `AsyncMock` を受け取る原因を特定（モック返却値の型不一致）し、適切な str を返すよう修正

### Priority 3: 構造的テスト分離不全（高リスク・調査必要）
- **#9-11** `test_workflow` 3本が単独 pass / 全体 fail。グローバル `set_db_manager` / `AppContainer` override のリーク。各テストの `finally` で確実にリセットする `pytest` fixture 化、または `pytest-asyncio` のスコープ制御で解決。

### Priority 4: 機能未実装・未インストール
- **#6** `PlotGraphManager.node_align_context` メソッド未実装 / `langgraph` 未インストール。実装 or テストを skip に格下げ。

---

## 実装ステップ詳細（各 1 ファイル / 1 関数単位）

### Step E-1: BaseWorkflow API 修正（#4, #5）
| アクション | 検証 |
|---|---|
| 1. `src/backend/workflows/base.py` の `BaseWorkflow.__init__` シグネチャ確認 | `engine` 引数必須か確認 |
| 2. `test_erotic_refine_workflow.py` の `RefineEroticWorkflow(...)` 呼び出しに `engine` 渡す | `pytest tests/integration/test_erotic_refine_workflow.py -q` → 2 passed |
| 3. `@pytest.mark.xfail` 除去 | `grep -r xfail tests/integration/test_erotic_refine_workflow.py` → 0 件 |

### Step E-2: generate_json タプル長修正（#3）
| アクション | 検証 |
|---|---|
| 1. `src/core/llm_gateway.py` の `generate_json` 戻り値確認（`GenerateResult, str, Usage` 等 3タプル） | 仕様確認 |
| 2. `test_erotic_full_pipeline.py::test_refine_erotic_workflow_mock` のアンパック修正 | `pytest tests/integration/test_erotic_full_pipeline.py::test_refine_erotic_workflow_mock -q` → passed |
| 3. `xfail` 除去 | 同上 |

### Step E-3: SharpEdgeSpec enum 追加（#12）
| アクション | 検証 |
|---|---|
| 1. `src/models/sharp_edge.py` の `SharpEdgeSpec.edge_type` バリデータ確認（許可リスト） | 許可リストに `sharp_conflict` 追加 OR テストで有効値使用 |
| 2. `test_verbose_fixture.py` の `edge_type="sharp_conflict"` → 有効値（例: `protagonist_flaw`）に変更 OR enum 追加 | `pytest tests/test_verbose_fixture.py::test_verbose_fixture_get_verbose_spec -q` → passed |
| 3. `xfail` 除去 | 同上 |

### Step E-4: 検閲マーカー `◆` モック応答修正（#1, #2）
| アクション | 検証 |
|---|---|
| 1. `tests/mocks/mock_llm.py` の `MockGeminiApiClient.default_text_response` に `◆` 含める | 文字列に `◆` を含める |
| 2. `test_erotic_full_pipeline.py::test_nocturn_preset_censorship` & `test_integrity_checker_clothing` 実行 | `pytest tests/integration/test_erotic_full_pipeline.py -k "censorship or clothing" -q` → 2 passed |
| 3. `xfail` 除去 | 同上 |

### Step E-5: tension_integration モック配線修正（#7, #8）
| アクション | 検証 |
|---|---|
| 1. `test_tension_integration.py` で `JSONDecodeError` / `TypeError: AsyncMock` が出る箇所特定 | `pytest tests/integration/test_tension_integration.py -v` |
| 2. `MockGeminiApiClient.generate_json` が返す値（3タプル）とテスト側の受け取り方不一致修正 | 同上 |
| 3. `xfail` 除去 | 同上 |

### Step E-6: test_workflow テスト分離修正（#9-11）
| アクション | 検証 |
|---|---|
| 1. `test_workflow.py` 各テストの `finally` ブロックで `AppContainer.llm.reset_override()` / `AppContainer.db.reset_override()` 確実実行 | ログ確認 |
| 2. `set_db_manager(None)` / `AppContainer.repo.reset_override()` 等のクリーンアップ追加 | `pytest tests/integration/test_workflow.py -v` |
| 4. `pytest tests/integration/test_workflow.py -q` → 3 passed | 3 passed |
| 5. `xfail` 除去 | 同上 |

### Step E-7: PlotGraphManager / langgraph 対応（#6）
| アクション | 検証 |
|---|---|
| 1. `src/backend/workflows/plot_langgraph.py` の `PlotGraphManager` に `node_align_context` メソッド実装 OR テストを `skip` 格下げ | 判断 |
| 2. `langgraph` を CI 依存に追加 (`pip install langgraph`) | `pip install langgraph` |
| 3. `pytest tests/integration/test_plot_workflow.py -q` → passed | passed |

---

## 進捗管理チェックリスト

```
[ ] E-1  BaseWorkflow API 修正（#4, #5）
[ ] E-2  generate_json タプル長修正（#3）
[ ] E-3  SharpEdgeSpec enum 追加（#12）
[ ] E-4  検閲マーカー `◆` モック応答修正（#1, #2）
[ ] E-5  tension_integration モック配線修正（#7, #8）
[ ] E-6  test_workflow テスト分離修正（#9-11）
[ ] E-7  PlotGraphManager / langgraph 対応（#6）
```

---

## 完了基準
- `pytest tests/unit tests/integration tests/test_zamaa_*.py tests/test_vector_store_lifecycle.py tests/test_verbose_fixture.py tests/test_config*.py --ignore=tests/integration/state_tests --ignore=tests/ui -q`
  → **すべて passed / skipped、xfail 0 件、failed 0 件**

---

## 注意事項
- 各ステップは「1 テスト関数 = 1 ステップ」で独立検証可能にする
- 修正後は必ず `pytest 対象テスト -q` で単体確認、その後全結合で回帰確認
- `xfail` 除去後は PR 単位でマージ、CI 緑を確認して次へ
- Priority 1-2 から着手し、Priority 3-4 は調査時間を見込む