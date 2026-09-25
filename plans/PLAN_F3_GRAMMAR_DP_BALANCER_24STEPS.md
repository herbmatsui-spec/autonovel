# PLAN_F3: 物語文法オートマトン＋DP 実装計画（24ステップ）

## 概要
物語構造を文脈自由文法（CFG）で定義し、Earleyパーサで現在のビート列を**部分構文解析** → 未完了非終端記号（未回収伏線・未適用必須構造）を検出 → 動的計画法（DP）で「残り話数で完全構文木完成させる最小コスト」を計算 → コスト閾値超過時に**文法書き換え規則**で中盤へ必須ビート（MIDPOINT_DISASTER等）を強制挿入。

**入力**: `beats_so_far: List[Beat]`（第1話～現在話）  
**出力**: `corrected_beats: List[Beat]`（必要に応じて現話以降を書き換え）

---

## ステップ定義

### Phase 0: 文法定義・基盤 (1-4)

#### Step 1: 終端記号・非終端記号定義
- **ファイル**: `src/narrative_balancer/grammar/symbols.py`
- **内容**: 
  - `Terminal`: `SETUP, RISING, MIDPOINT_DISASTER, FALLOUT, STAGNATION, RECOVERY, CLIMAX, RESOLUTION, DAILY, BATTLE, PAYOFF, ...`
  - `NonTerminal`: `STORY, QUARTER, ACT1, ACT2A, ACT2B, ACT3, MIDPOINT_DISASTER_RULE, STAGNATION_RULE, ...`
- **テスト**: `tests/unit/test_symbols.py` - 列挙値網羅・文字列変換

#### Step 2: 文法規則定義（BNF→Python辞書）
- **ファイル**: `src/narrative_balancer/grammar/rules.py`
- **データ**: `GRAMMAR: Dict[NonTerminal, List[List[Symbol]]]`
- **主要規則** (抜粋):
  ```
  STORY → QUARTER QUARTER QUARTER QUARTER
  QUARTER → SETUP RISING MIDPOINT_DISASTER FALLOUT   # 正常
         | SETUP RISING STAGNATION RECOVERY          # 中だるみ許容（RECOVERY必須）
  MIDPOINT_DISASTER → BASE_COLAPSE | ALLY_BETRAYAL | FALSE_VICTORY
  STAGNATION → REPEAT_QUEST | SLICE_OF_LIFE | FAKE_PROGRESS
  ACT2A → QUARTER QUARTER  # 第2・3クォーター = 中盤
  ```
- **テスト**: `tests/unit/test_grammar_rules.py` - 規則数・非終端記号到達可能性検証

#### Step 3: Earleyパーサラッパー実装
- **ファイル**: `src/narrative_balancer/grammar/parser.py`
- **クラス**: `EarleyParser` （`lark` または自前実装 `earley-parser` ライブラリ使用）
- **メソッド**: 
  - `parse_prefix(terminals: List[Terminal]) -> ParseForest`
  - `get_pending_nonterminals(forest) -> Set[NonTerminal]`
  - `get_completed_trees(forest) -> List[ParseTree]`
- **テスト**: `tests/unit/test_earley_parser.py` - 既知文法で正常/エラー/部分解析ケース検証

#### Step 4: 構文解析結果データ構造
- **ファイル**: `src/narrative_balancer/grammar/parse_forest.py`
- **クラス**: `ParseForest`, `ParseNode`, `PendingNonterminal`
- **フィールド**: `pending: Set[NonTerminal]`, `completed: List[ParseTree]`, `consumed_terminals: int`
- **テスト**: `tests/unit/test_parse_forest.py` - シリアライズ・マージ操作検証

---

### Phase 1: DPコスト計算エンジン (5-10)

#### Step 5: コストモデル定義
- **ファイル**: `src/narrative_balancer/grammar/cost_model.py`
- **クラス**: `CostModel`（設定可能な重み付きコスト関数）
- **コスト項目**:
  - `rule_expansion_cost[NonTerminal][production]`: 規則展開コスト
  - `terminal_insertion_cost[Terminal]`: 終端記号挿入コスト
  - `terminal_deletion_cost[Terminal]`: 終端記号削除コスト
  - `terminal_substitution_cost[Terminal][Terminal]`: 置換コスト
  - `constraint_penalty`: キャラ放置・伏線腐敗・テンション単調化等ペナルティ
- **設定**: `config/grammar_cost.yaml` で全重み外出し
- **テスト**: `tests/unit/test_cost_model.py` - 既知展開で手計算比較

#### Step 6: DPテーブル構築関数
- **ファイル**: `src/narrative_balancer/grammar/dp.py`
- **関数**: `build_dp_table(forest: ParseForest, remaining_eps: int, cost_model: CostModel) -> DPTable`
- **状態**: `dp[nonterminal][remaining_episodes] = min_cost`
- **遷移**: 
  ```
  for each production A → α:
    cost = rule_cost[A][α] + Σ dp[B][eps_allocated] for B in α
  ```
- **テスト**: `tests/unit/test_dp_table.py` - 小文法で手動DPトレース比較

#### Step 7: 最小完結コスト計算
- **ファイル**: `src/narrative_balancer/grammar/dp.py` (追加)
- **関数**: `min_completion_cost(forest: ParseForest, remaining: int, cost_model: CostModel) -> float`
- **ロジック**: `dp[STORY][remaining]` または森の各根非終端記号の最小和
- **テスト**: `tests/unit/test_min_cost.py` - 正常/中だるみ/破綻ケースでコスト差確認

#### Step 8: 最適展開経路復元（バックトラック）
- **ファイル**: `src/narrative_balancer/grammar/dp.py` (追加)
- **関数**: `reconstruct_optimal_expansion(dp_table, forest, remaining) -> List[Production]`
- **出力**: 適用すべき文法規則の系列（どの非終端記号をどう展開するか）
- **テスト**: `tests/unit/test_backtrack.py` - 復元経路がコスト最小になること検証

#### Step 9: 制約ペナルティ統合（キャラ・伏線・テンション）
- **ファイル**: `src/narrative_balancer/grammar/constraint_penalties.py`
- **関数**: 
  - `char_neglect_penalty(forest, remaining, char_states) -> float`
  - `payoff_decay_penalty(forest, remaining, payoff_states) -> float`
  - `tension_monotony_penalty(forest, remaining, tension_curve) -> float`
- **統合**: `CostModel` に加算登録
- **テスト**: `tests/unit/test_constraint_penalties.py` - 各ペナルティ単体・合成で単調増加確認

#### Step 10: DPエンジン統合クラス
- **ファイル**: `src/narrative_balancer/grammar/dp_engine.py`
- **クラス**: `DPEngine`
- **メソッド**: 
  - `analyze(beats: List[Beat]) -> AnalysisResult` (森・コスト・未完了非終端記号)
  - `suggest_corrections(analysis) -> List[CorrectionAction]`
- **テスト**: `tests/integration/test_dp_engine.py` - エンドツーエンド解析・提案

---

### Phase 2: 文法書き換え・補正機構 (11-16)

#### Step 11: 書き換え規則定義
- **ファイル**: `src/narrative_balancer/grammar/rewrite_rules.py`
- **データ**: `REWRITE_RULES: List[RewriteRule]`
- **主要規則**:
  - `STAGNATION → MIDPOINT_DISASTER` (コスト減少見込み時、優先度高)
  - `RISING RISING → RISING MIDPOINT_DISASTER` (2連続RISINGなら第2を災厄化)
  - `DAILY DAILY DAILY → DAILY DAILY MIDPOINT_DISASTER` (日常3連なら3話目強制災厄)
  - `MISSING_PAYOFF → INSERT_PAYOFF_BEFORE_CLMAX` (未回収伏線がクライマックス前なら直前挿入)
- **テスト**: `tests/unit/test_rewrite_rules.py` - 規則マッチ・適用前後コスト比較

#### Step 12: 書き換え適用エンジン
- **ファイル**: `src/narrative_balancer/grammar/rewriter.py`
- **クラス**: `GrammarRewriter`
- **メソッド**: 
  - `apply_rule(beats: List[Beat], rule: RewriteRule, position: int) -> List[Beat]`
  - `apply_best_correction(beats, analysis) -> List[Beat]` (DPコスト最小化する規則選択)
- **テスト**: `tests/unit/test_rewriter.py` - 適用前後で未完了非終端記号減少確認

#### Step 13: ビート↔終端記号マッピング
- **ファイル**: `src/narrative_balancer/grammar/beat_mapping.py`
- **関数**: 
  - `beat_to_terminal(beat: Beat) -> Terminal`
  - `terminal_to_beat_template(terminal: Terminal) -> BeatTemplate`
- **テンプレート**: 各終端記号に対応するビート雛形（テンション範囲・必須要素・禁止要素）
- **テスト**: `tests/unit/test_beat_mapping.py` - 相互変換・情報保持確認

#### Step 14: 強制挿入・差し替えロジック
- **ファイル**: `src/narrative_balancer/grammar/corrector.py`
- **関数**: `force_midpoint_correction(beats: List[Beat], ep: int) -> List[Beat]`
- **ロジック**: 
  1. `ep` 付近で `STAGNATION` または `RISING` 連続検出
  2. `MIDPOINT_DISASTER` 規則で書き換え
  3. `beat_mapping` で実ビート生成（テンション 8-9、必須要素: 拠点崩壊/相棒離脱/偽勝利）
- **テスト**: `tests/unit/test_force_correction.py` - 第20-25話窓で災厄ビート確実挿入確認

#### Step 15: クォーター境界整合性チェック
- **ファイル**: `src/narrative_balancer/grammar/quarter_validator.py`
- **関数**: `validate_quarter_boundaries(beats: List[Beat]) -> List[Violation]`
- **チェック**: 
  - 各クォーターに `MIDPOINT_DISASTER` または `RECOVERY` 含むこと
  - Q2・Q3 平均テンション ≥ 5
  - 伏線導入→回収がクォーター跨ぎで腐敗していない
- **テスト**: `tests/unit/test_quarter_validator.py` - 違反/充足ケース網羅

#### Step 16: 文法バランサーメインクラス
- **ファイル**: `src/narrative_balancer/grammar/balancer.py`
- **クラス**: `GrammarNarrativeBalancer`
- **メソッド**: 
  - `balance(beats: List[Beat]) -> BalancedResult` (解析→DP→書き換え→検証)
  - `analyze_only(beats) -> AnalysisResult` (診断のみ)
- **テスト**: `tests/integration/test_grammar_balancer.py` - 正常/中だるみ/破綻入力で期待補正確認

---

### Phase 3: 可視化・診断・CLI (17-20)

#### Step 17: 構文木可視化（DOT/GraphViz）
- **ファイル**: `src/narrative_balancer/grammar/visualize.py`
- **関数**: `parse_forest_to_dot(forest: ParseForest) -> str`
- **出力**: 非終端記号=楕円、終端記号=箱、未完了=赤枠、完了=緑枠
- **テスト**: `tests/unit/test_visualize.py` - DOT 文法妥当性・ノード数確認

#### Step 18: コスト内訳レポート生成
- **ファイル**: `src/narrative_balancer/grammar/report.py`
- **関数**: `generate_cost_report(analysis: AnalysisResult) -> str`
- **内容**: DPテーブル抜粋、未完了非終端記号リスト、適用推奨書き換え規則・期待コスト減少量
- **テスト**: `tests/unit/test_report.py` - 必須セクション存在・数値整合性

#### Step 19: CLI エントリーポイント
- **ファイル**: `src/narrative_balancer/grammar/cli.py`
- **コマンド**: 
  - `grammar-balance --input beats.json --output corrected.json`
  - `grammar-analyze --input beats.json --dot output.dot`
  - `grammar-report --input beats.json --md report.md`
- **テスト**: `tests/integration/test_grammar_cli.py` - 3サブコマンド正常動作

#### Step 20: ゴールデンマスタ統合テスト
- **ファイル**: `tests/integration/test_grammar_golden.py`
- **フィクスチャ**: `tests/fixtures/grammar_golden/` - 10+ ケース
  - 正常40話、第20話欠落災厄、第15-25話停滞、伏線腐敗、キャラ放置
- **検証**: 入力→出力のハッシュ比較でリグレッション防止

---

### Phase 4: 堅牢化・拡張・CI (21-24)

#### Step 21: あいまい文法対応（複数構文木）
- **課題**: Earleyパーサは曖昧文法で指数的森生成
- **対策**: 
  - `forest.prune(max_trees=100)` で上位コスト順に枝刈り
  - `dp` 計算時に森全体の期待値コストで近似
- **テスト**: `tests/unit/test_ambiguity.py` - 故意に曖昧文法で枝刈り動作確認

#### Step 22: 増分解析（話追加ごとの差分更新）
- **ファイル**: `src/narrative_balancer/grammar/incremental.py`
- **クラス**: `IncrementalParser` - 前回の `ParseForest` を再利用し、新終端記号1つ分だけ更新
- **効果**: 40話フル解析 → 1話追加で O(1) 更新
- **テスト**: `tests/unit/test_incremental.py` - フル解析結果と増分解析結果一致確認

#### Step 23: パフォーマンスベンチマーク
- **ファイル**: `benchmarks/benchmark_grammar.py`
- **測定**: 
  - フル解析 40話: p99 < 10ms
  - 増分解析 1話: p99 < 1ms
  - メモリ: < 50MB
- **CI**: `tests/performance/test_grammar_perf.py`

#### Step 24: 回帰テスト・CI統合・ドキュメント
- **プロパティテスト**: `tests/property/test_grammar_properties.py`
  - 単調性: 話追加でコスト非増加
  - 冪等性: 同一入力→同一出力
  - 収束性: 書き換え適用繰り返しで未完了非終端記号=∅ に収束
- **CI**: `.github/workflows/grammar_balancer.yml` (lint→type→unit→integration→property→perf)
- **ドキュメント**: `docs/grammar_balancer.md` - 文法設計指針・コスト調整ガイド・拡張方法
- **完了**: `v0.1.0-grammar` タグ

---

## 依存関係グラフ

```
1→2→3→4
  ↓
5→6→7→8→9→10
           ↓
        11→12→13→14→15→16
                    ↓
                  17→18→19→20
                          ↓
                        21→22→23→24
```

---

## 実装上の重要ポイント（低性能LLM向け）

| 課題 | 対策 |
|------|------|
| **Earleyパーサ自作の複雑さ** | `lark` (LALR) または `earley-parser` (PyPI) ライブラリ利用、ラッパーのみ自作 |
| **DPテーブル次元爆発** | 非終端記号数 ~20、残り話数 ≤40 → テーブル 800 セル、極小。配列で実装 |
| **コスト重み調整の難しさ** | 設定 YAML 完全分離、デフォルト値は「古典的名作40話」を手動解析して逆算した値を同梱 |
| **書き換え規則の優先度競合** | 規則に `priority: int` 付与、DPコスト減少量 × priority でスコアリング |
| **ビートテンプレートの表現力** | `BeatTemplate` を JSON Schema 化、`jsonschema` でバリデーション、LLM不要で生成 |

---

## 完了基準
- [ ] 全 24 ステップ マージ済み
- [ ] `pytest tests/ -k grammar -v` 全パス
- [ ] 中だるみ入力（第15-25話フラット）で「第21話に BASE_COLLAPSE 自動挿入」再現
- [ ] `mypy --strict src/narrative_balancer/grammar` パス
- [ ] フル解析 p99 < 10ms、増分 p99 < 1ms
- [ ] ゴールデンマスタ 10ケース 100% 一致
- [ ] 可視化 DOT 出力が GraphViz でレンダリング可能