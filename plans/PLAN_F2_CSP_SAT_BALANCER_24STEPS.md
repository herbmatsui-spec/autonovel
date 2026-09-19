# PLAN_F2: CSP/SATソルバーアプローチ 実装計画（24ステップ）

## 概要
40話全体を制約充足問題（CSP）として定式化し、OR-Tools CP-SAT で「構造的整合性制約」をハード制約、「品質指標」をソフト制約（ペナルティ）としてモデル化。中盤制約違反時に**最小変更**で再求解し、打破イベントを自動導出。

**入力**: 部分的に確定したプロット状態（確定話・未確定話・キャラ弧・伏線DB）  
**出力**: 全話充足解（未確定話のビートタイプ・テンション・登場キャラ等）

---

## ステップ定義

### Phase 0: 環境・モデル定義 (1-4)

#### Step 1: ドメインモデル・列挙型定義
- **ファイル**: `src/narrative_balancer/csp/models.py`
- **内容**: `BeatType`(SETUP/BATTLE/DISASTER/PAYOFF/DAILY/RECOVERY/CLIMAX), `CharRole`, `ConstraintPriority` 等 Enum
- **テスト**: `tests/unit/test_csp_models.py` - 列挙値網羅・シリアライズ検証

#### Step 2: 変数定義スキーマ（Pydantic）
- **ファイル**: `src/narrative_balancer/csp/variables.py`
- **クラス**: `CSPVariables` - 各話の決定変数定義（テンション 1-10, ビートタイプ, 登場キャラビットマスク, 敗北フラグ, 伏線回収フラグ等）
- **テスト**: `tests/unit/test_csp_variables.py` - 変数数・ドメイン整合性検証

#### Step 3: 制約定義インターフェース
- **ファイル**: `src/narrative_balancer/csp/constraints.py`
- **プロトコル**: `ConstraintBuilder` - `add_hard_constraints(model, vars)`, `add_soft_constraints(model, vars)` 抽象メソッド
- **テスト**: `tests/unit/test_constraints_interface.py` - 実装強制チェック

#### Step 4: 設定スキーマ（YAML）定義
- **ファイル**: `config/csp_balancer.yaml`
- **内容**: 
  - ハード制約: ミッドポイント話数、テンション境界、敗北率範囲、伏線回収最大話数
  - ソフト制約重み: テンション変動滑らかさ、キャラ登場均等性、クォーター平均テンション目標
  - ソルバー設定: `max_time_seconds`, `num_search_workers`, `log_search_progress`
- **テスト**: `tests/unit/test_csp_config.py` - バリデーション・デフォルト値

---

### Phase 1: ハード制約実装 (5-11)

#### Step 5: 構造制約ビルダー（骨子）
- **ファイル**: `src/narrative_balancer/csp/structural_constraints.py`
- **クラス**: `StructuralConstraintBuilder` implements `ConstraintBuilder`
- **制約**:
  - `tension[19] >= 7` (第20話ミッドポイント高テンション)
  - `tension[29] <= 3` (第30話オールイズロスト低谷)
  - `sum(tension[10:20])/10 <= 5.5` (第2クォーター抑制)
  - `tension[39] >= 8` (最終話クライマックス)
- **テスト**: `tests/unit/test_structural_constraints.py` - 充足/違反ケースでモデル検証

#### Step 6: キャラ弧制約ビルダー
- **ファイル**: `src/narrative_balancer/csp/character_constraints.py`
- **クラス**: `CharacterArcConstraintBuilder`
- **制約**:
  - 主人公敗北回数: `6 <= sum(defeat_flags) <= 14`
  - 各主要キャラ登場回数: `min_appear <= sum(char_presence[ep][ch]) <= max_appear`
  - キャラ弧マイルストーン: 導入→葛藤→成長→解決 の順序制約（前後関係）
- **テスト**: `tests/unit/test_character_constraints.py` - 境界値・順序違反検証

#### Step 7: 伏線・回収制約ビルダー
- **ファイル**: `src/narrative_balancer/csp/payoff_constraints.py`
- **クラス**: `PayoffConstraintBuilder`
- **制約**:
  - `SETUP` ビート → 15話以内に `PAYOFF` ビート必須
  - 同一伏線IDの回収は1回のみ
  - 未回収伏線の残存数上限（話数に応じて減少）
- **テスト**: `tests/unit/test_payoff_constraints.py` - 導入・回収・未回収パターン網羅

#### Step 8: テンション物理制約
- **ファイル**: `src/narrative_balancer/csp/tension_constraints.py`
- **クラス**: `TensionPhysicsConstraintBuilder`
- **制約**:
  - 話間テンション差分 ≤ 4（急激変化禁止）
  - 3話移動平均 ≥ 2（持続的低テンション禁止）
  - 局所的極大・極小の最小間隔 ≥ 3話
- **テスト**: `tests/unit/test_tension_constraints.py` - 違反・充足ケース

#### Step 9: クォーターバランス制約
- **ファイル**: `src/narrative_balancer/csp/quarter_constraints.py`
- **クラス**: `QuarterBalanceConstraintBuilder`
- **制約**:
  - 各クォーター(10話)のビートタイプ分布: `BATTLE≥2, DISASTER≥1, PAYOFF≥1, DAILY≤4`
  - クォーター平均テンション: Q1≈4, Q2≈5, Q3≈6, Q4≈7（目標値±1）
- **テスト**: `tests/unit/test_quarter_constraints.py` - 分布・平均値検証

#### Step 10: 制約登録ファクトリ
- **ファイル**: `src/narrative_balancer/csp/constraint_factory.py`
- **関数**: `build_all_constraints(model, vars, config) -> List[ConstraintBuilder]`
- **役割**: 設定に基づき必要なビルダーをインスタンス化・順序実行
- **テスト**: `tests/unit/test_constraint_factory.py` - 全ビルダー呼び出し確認

#### Step 11: 制約充足モデル構築関数
- **ファイル**: `src/narrative_balancer/csp/model_builder.py`
- **関数**: `build_csp_model(partial_state: PartialPlotState, config: CSPConfig) -> tuple[CpModel, CSPVariables]`
- **処理**: 変数作成 → 確定値をヒント/固定制約として追加 → 全制約登録
- **テスト**: `tests/integration/test_model_builder.py` - 部分状態からモデル生成・変数数確認

---

### Phase 2: ソフト制約・目的関数 (12-15)

#### Step 12: 滑らかさペナルティ（ソフト制約）
- **ファイル**: `src/narrative_balancer/csp/soft_constraints.py`
- **関数**: `add_smoothness_penalty(model, vars, weight)`
- **式**: `Σ |tension[i+1] - tension[i]| * weight` → 線形化して補助変数で表現
- **テスト**: `tests/unit/test_smoothness_penalty.py` - 既知系列でペナルティ値手計算比較

#### Step 13: キャラ登場均等性ペナルティ
- **ファイル**: `src/narrative_balancer/csp/soft_constraints.py` (追加)
- **関数**: `add_character_balance_penalty(model, vars, weight)`
- **式**: 各キャラ登場回数の分散最小化（二次式→線形化または CP-SAT の `AddMaxEquality` 利用）
- **テスト**: `tests/unit/test_char_balance_penalty.py` - 偏り大/小でペナルティ差確認

#### Step 14: クォーター目標テンションペナルティ
- **ファイル**: `src/narrative_balancer/csp/soft_constraints.py` (追加)
- **関数**: `add_quarter_target_penalty(model, vars, weight)`
- **式**: `Σ_q |avg_tension_q - target_q| * weight`
- **テスト**: `tests/unit/test_quarter_target_penalty.py` - 目標値乖離でペナルティ比例確認

#### Step 15: 目的関数統合・求解関数
- **ファイル**: `src/narrative_balancer/csp/solver.py`
- **関数**: `solve_csp(model, config) -> tuple[CpSolver, SolveStatus]`
- **処理**: 目的関数 = Σ ソフト制約ペナルティ → `model.Minimize(objective)` → `solver.Solve(model)`
- **テスト**: `tests/integration/test_solver.py` - 既知充足問題で最適解・実行時間検証

---

### Phase 3: 部分状態からの修復・再求解 (16-19)

#### Step 16: 部分状態データ構造
- **ファイル**: `src/narrative_balancer/csp/partial_state.py`
- **クラス**: `PartialPlotState` - 確定済み話インデックス・値辞書、未確定話集合
- **テスト**: `tests/unit/test_partial_state.py` - シリアライズ・マージ操作検証

#### Step 17: ヒント値注入・固定制約追加
- **ファイル**: `src/narrative_balancer/csp/model_builder.py` (拡張)
- **関数**: `apply_partial_state(model, vars, partial: PartialPlotState)`
- **ロジック**: 確定変数は `model.AddHint` + `model.Add(var == value)` で固定
- **テスト**: `tests/unit/test_hint_injection.py` - 固定変数が解に反映されること確認

#### Step 18: 最小変更修復関数
- **ファイル**: `src/narrative_balancer/csp/repair.py`
- **関数**: `repair_midpoint_sag(current_state: PartialPlotState, config) -> PartialPlotState`
- **ロジック**: 
  1. 現状態でモデル構築・求解
  2. UNSAT ならソフト制約緩和・再求解
  3. 解から未確定話の値を抽出し `PartialPlotState` 更新
- **テスト**: `tests/integration/test_repair.py` - 中だるみ状態入力で災厄ビート挿入確認

#### Step 19: 解の Beat シート変換
- **ファイル**: `src/narrative_balancer/csp/converter.py`
- **関数**: `csp_solution_to_beats(solver, vars, n_episodes) -> List[Beat]`
- **テスト**: `tests/unit/test_converter.py` - 全変数値正しくマッピング確認

---

### Phase 4: 統合・CLI・堅牢化 (20-24)

#### Step 20: CSPバランサーメインクラス
- **ファイル**: `src/narrative_balancer/csp/balancer.py`
- **クラス**: `CSPNarrativeBalancer`
- **メソッド**: `balance(partial_state) -> List[Beat]`, `validate_full(beats) -> ValidationResult`
- **テスト**: `tests/integration/test_csp_balancer.py` - エンドツーエンド

#### Step 21: 実行可能 CLI
- **ファイル**: `src/narrative_balancer/csp/cli.py`
- **コマンド**: `csp-balance --state state.json --config config.yaml --output beats.json`
- **テスト**: `tests/integration/test_csp_cli.py` - 実行・出力検証

#### Step 22: インフェアシビリティ診断・説明出力
- **ファイル**: `src/narrative_balancer/csp/diagnostics.py`
- **関数**: `explain_infeasibility(model, solver) -> List[ConflictClause]`
- **活用**: 充足不能時「どの制約が競合か」を人間可読で出力
- **テスト**: `tests/unit/test_diagnostics.py` - 故意に矛盾制約入れて検出確認

#### Step 23: パフォーマンス・スケーラビリティテスト
- **ファイル**: `benchmarks/benchmark_csp.py`
- **測定**: 40話・変数数~2000・制約数~500 で p99 < 500ms
- **CIゲート**: `tests/performance/test_csp_perf.py` で閾値超過失敗

#### Step 24: 回帰テストスイート・CI統合
- **データ**: `tests/fixtures/csp_regression/` - 充足/非充足/境界 30+ ケース
- **プロパティテスト**: `tests/property/test_csp_properties.py` - 単調性・冪等性・対称性
- **CI**: `.github/workflows/csp_balancer.yml` (lint→type→unit→integration→property→perf)
- **カバレッジ**: ≥ 90%、`mypy --strict` パス

---

## 依存関係グラフ

```
1→2→3→4
  ↓
5→6→7→8→9→10→11
           ↓
        12→13→14→15
           ↓
        16→17→18→19
                  ↓
                20→21→22→23→24
```

---

## 実装上の重要ポイント（低性能LLM向け）

| ポイント | 対策 |
|----------|------|
| **CP-SAT 記法の複雑さ** | 各制約を独立したビルダークラスに分離、単体テストで動作確認 |
| **線形化・補助変数** | `soft_constraints.py` に共通ユーティリティ `linearize_abs`, `linearize_max` を集約 |
| **デバッグ困難** | `diagnostics.py` で `solver.SolutionCallback` 実装、探索ログ・矛盾節を JSON 出力 |
| **パラメータ調整** | 設定 YAML 完全外出し、デフォルト値は「過去ヒット作平均」から算出済み値を記載 |
| **部分求解の再利用** | `PartialPlotState` をイミュータブルに、マージ操作で履歴管理可能に |

---

## 完了基準
- [ ] 全 24 ステップ マージ済み
- [ ] `pytest tests/ -k csp -v` 全パス
- [ ] 中だるみ注入テストケースで「第21話に DISASTER 自動挿入」再現
- [ ] `mypy --strict src/narrative_balancer/csp` パス
- [ ] p99 < 500ms、メモリ < 200MB
- [ ] インフェアシビリティ診断が人間可読で出力されること