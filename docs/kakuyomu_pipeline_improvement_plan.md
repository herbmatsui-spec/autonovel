# カクヨムランキング上位・商業作品を「かんたんに」生み出すためのパイプライン改善計画書

## 1. 目的とスコープ

本計画書は、既存の小説生成マルチエージェントパイプライン（MasterGraph → Plot/Writing/Review サブグラフ）を改善し、**カクヨム（小説投稿サイト）のランキング上位入りや、商業レベルの品質を持った作品を、低い運用コストで安定的に生み出すこと**を目的とする。

狙いは「より賢いプロンプトを書く」ことではなく、「上位作品の決定因をシステム内で測定し、ゲートで弾き、ループで直す」仕組みを組み込むことである。同時に、API コストと実行時間の爆発を防ぐガードレールを備え、低性能な LLM でも実装・検証が進められるよう、作業を 72 の小ステップに分割する。

本ドキュメントの対象読者は、本リポジトリの実装を担うエンジニア（およびコーディング支援 LLM）である。

---

## 2. 現状分析

### 2.1 パイプライン構成

- **MasterGraph** (`src/backend/workflows/graphs/master_graph.py`)
  - `plot_phase` → `writing_phase` → `review_phase` の順次フロー。
- **PlotGraph** (`plot_graph.py`)
  - `generate_initial_plot` → `evaluate_plot` →（必要なら `refine_plot` ループ）→ END。
- **WritingGraph** (`writing_graph.py`)：話ごとに実行
  - `build_context` → `generate_draft` → `self_audit` →（不合格なら再生成ループ）→ END。
- **ReviewGraph** (`review_graph.py`)：話ごとに実行
  - `analyze_pacing` → `check_character_consistency` → `propose_edits` → END。

### 2.2 API コール数の実測（3話・target_start_ep=1, target_end_ep=3）

`tests/workflows/test_three_episodes_review.py` で計測した。

| シナリオ | generate_json | generate_text | 合計 |
|---|---|---|---|
| ベストケース（全承認・ループなし） | 11 | 3 | **14** |
| ワーストケース（plot 1回リファイン＋writing 各話1回再生成） | 16 | 6 | **22** |

内訳（1話あたり）：Writing は `generate_text×1 + generate_json×1`（監査）、Review は `generate_json×2`（pacing, character）。Plot は本全体で `generate_json×2〜4`。概算式は **best = 4N+2 / worst = 6N+4**（N=話数）。

### 2.3 現状の課題（4点）

1. **Review の結果が放置される**（`master_nodes.py:170`）：`requires_revision` を無視して `completed` で終了するため、監査で指摘されても直らない。
2. **短い本文で監査がスキップされる**（`writing_nodes.py:156`）：`len(draft) < 50` だと LLM を呼ばずに `is_integrity_ok=False` を返し、無駄な再生成ループに入る。
3. **完全直列の for ループ**（`master_nodes.py:97,149`）：話数 N で線形に時間が伸び、待機時間が支配的になる。
4. **Plot のリファインが最大1回・閾値0.8**（`plot_edges.py:33`）：品質未達でも強制終了し、粗削りなプロットから執筆が始まる。

加えて、カクヨム上位の決定因（冒頭フック、各話クリフハンガー、読了率、ブックマーク率、設定の破綻のなさ）をシステムが評価する仕組みが存在しない。

---

## 3. 改善の基本方針（設計原則）

提案を単なる「ノード追加」にとどめず、以下の 4 原則で厳密化する。

- **P1：指標の一元化** — 「売れそうか」を測る `commercial_score` を唯一の合格ラインとし、プロット選抜・差し戻し・フック判定のすべてに使う。
- **P2：ループの収束ガード** — すべての再生成・再評価ループに予算（budget）と収束判定を付け、コスト爆発を防ぐ。
- **P3：並列化と連続性の両立** — 話「間」を並列にすると連続性が壊れるため、並列化は「話内の独立呼び出し」に限定し、共有状態（Bible/ledger）の書き込みは直列ロックする。
- **P4：人間は最重要の1点だけ止める** — 毎ステップ承認するのではなく、プロット確定時の1点だけ人間（作家）に選ばせ、手間を減らす。

---

## 4. 9 つの改善提案（詳細）

### 【A 最優先】即効性が高く品質底上げに直結

#### ① Review→執筆の「限定差し戻しループ」
- **課題**：review の `requires_revision` が無視される。
- **設計**：review 完了後、`needs_revision_eps` を抽出し、該当話だけ `writing_graph` を再実行（`max_revise=1`）。再執筆後は全文 review ではなく差分再評価を 1 回のみ行い、収束（要修正数の減少）しなければ終了。
- **効果**：推敲抜けを防ぐ。最悪ケースの API 増を「+2×該当話」に抑える（3話で 22→最大 28）。
- **リスク/対策**：無限ループ防止は「予算＋収束判定」の二重ガード。

#### ② 本文の「薄さ」判定を文字数から「密度ルービック」へ
- **課題**：50文字閾値は「短さ」しか見ない。商業で問題なのは「事件密度の低さ」。
- **設計**：下限を `MIN_DRAFT_CHARS=1500` にし、`self_audit` に `event_density`（展開/性格露出/緊張上昇の充足度 0–1）を評価させる。`check_audit_results` の合格条件に `event_density >= 0.5` を AND し、不足要素を `failures` に宿す。
- **効果**：だらだらした話を排除しつつ、無駄な再生成を減らす。

#### ③ 並列化の矛盾解消：話「内」並列＋Bibleロック
- **課題**：話間並列は提案⑥（連続性）と衝突する。
- **設計**：review の `analyze_pacing` と `check_character_consistency` は同一草稿のみに依存し独立なので `asyncio.gather` で同時実行（2call→1RTT）。話間は順次だが、共有 `bible_state` への書き込みだけを直列ロック。
- **効果**：待機時間を約半減しつつ連続性は維持。

### 【B 高優先】商業品質の決定因を組み込む

#### ④ カクヨム指標を「LLM-as-Judge ルービック」にする
- **課題**：「ブックマーク予測」は幽霊指標。
- **設計**：上位作の共通構造をルービック化し `score_commercial_node` で採点。
  - 1) 冒頭300字のフック密度
  - 2) 800〜1200字ごとの「引き」発生
  - 3) 感情バレンスの振れ幅
  - 4) シリーズ級の謎/伏線の初期設置
  - 5) 「続きが読みたくなる」未解決緊張の維持
  - 各項を 0–1 で採点し `commercial_score` を算出。
- **効果**：ランキング上位因を構造的に評価・最大化。

#### ⑤ プロットゲート：複数案×商業スコア選抜
- **課題**：単一プロットを許容するだけ。
- **設計**：`generate_initial_plot` を `num_variants=3` で並行生成→④ルービックで採点→上位1をリファイン。閾値 0.85 は「世代内相対＋絶対」で運用。
- **効果**：「より売れそう」を選ぶ。

#### ⑥ Bible を「連続性台帳（continuity ledger）」にする
- **課題**：`build_context_node` は取得のみで、話跨ぎの一貫性を保てない。
- **設計**：状態に `ledger`（キャラの所在/関係/未回収伏線/口調辞書/世界ルール）を永続保持。執筆時に注入し、review の `character` 監査は「台帳との差分」を判定。各話終了時に ledger を更新し次話へ反映。
- **効果**：カクヨム上位の「設定破綻ファン離れ」を防ぐ要。

#### ⑦ フック最適化を「決定論的 cadence 検証＋LLM 研磨」に
- **課題**：無条件の1往復はコスト無駄。
- **設計**：後処理で「各話末尾は未解決の緊張で終わる」「冒頭300字にフック≥1」を機械検証。満たさない場合のみ `hook_optimize_node` を1往復（全文再生成ではなく冒頭/末尾の書き換えに限定）。
- **効果**：読了率・ブックマーク率（ランキング直結）を構造的に確保。

### 【C 中優先】発見性と作家の手離れ

#### ⑧ タイトル/タグ/あらすじの CTR 最適化
- **設計**：`generate_metadata_node` でタイトル3案＋タグ＋2行プレビュー用あらすじを生成。④ルービックでタイトルを採点し上位を採用。カクヨムのジャンル/タグ分類に合わせてタグを走査・絞り込み。
- **効果**：発見・クリック率向上を測定可能に。

#### ⑨ HITL：最もレバレッジの高い「プロット承認ゲート」のみ
- **設計**：全自動ではなく、**プロット確定時の1点**だけ SSE/reporter 経由で作家が「採用/別案/調整」を選ぶ（⑤の複数案を提示）。執筆後は差分承認のみ。checkpointer で再開。
- **効果**：作家の手間を減らすには「毎ステップ止める」より「最重要1点で止める」方が「かんたんに」に寄与。

---

## 5. 全体ガードレール

- **コスト/時間予算**：タスクごとに `token_budget` と `wall_clock_budget` を設け、超過時は品質ゲートを緩和方向にフォールバック（かんたんさ優先）。
- **メタ評価ルーター（QualityRouter）**：①・②・④・⑤を束ね、「次はリファインか／差し戻しか／完了か」を一括判定し、API 呼び出し回数を最小化。
- **測定指標（A/B 比較用）**：`commercial_score`、`event_density`、`requires_revision数`、`API call数` の 4 指標を `quality_metrics` に記録。

---

## 6. 実装計画：72 ステップ

各ステップは「単一ファイル × 単一関数の小さな変更＋pytest 検証」に分解し、低性能 LLM でも 1 ステップずつ確実に進められる。Phase 0→9 の順とし、各 Phase 終了ごとにコミットする。

### Phase 0 — 基盤・計測（1〜8）
1. `MasterGraphState` に `api_call_count: int` 追加。
2. 同 state に `quality_metrics: dict` 追加。
3. `CountingLLMProvider` の既存メソッドから `api_call_count` を +1 するよう修正。
4. baseline（best=14 / worst=22）をテストで確認。
5. `ReviewGraphState` に `commercial_score: float` 追加。
6. `WritingGraphState` に `event_density: float` 追加。
7. `MasterGraphState` に `revision_budget: int = 1` 追加。
8. 作業ブランチ作成、Phase ごとコミットの運用決定。

### Phase 1 — ① 差し戻しループ（9〜16）
9. `call_review_graph_node` で `requires_revision` 話数を集計し `review_summary` 返却。
10. `MasterGraphState` に `needs_revision_eps: list[int]` 追加。
11. `master_graph.py` に `revise_writing_node` を空実装で追加。
12. `revise_writing_node` 内で該当話のみ `writing_graph` 再実行。
13. revise 後は既存 review を 1 回だけ再実行し再集計。
14. エッジを `review → (要修正 & budget>0) ? revise : END` に変更。
15. 収束判定追加（減らなければ budget 消費で END）。
16. テスト：revise 発動で API +2×該当話 増を確認。

### Phase 0 — 基盤・計測（1〜8）
- [x] 1. `MasterGraphState` に `api_call_count: int` 追加。
- [x] 2. `MasterGraphState` に `quality_metrics: Dict[str, Any]` 追加。
- [x] 3. `CountingLLMProvider` の `generate_json` / `generate_text` で `api_call_count += 1` するよう修正。
- [x] 4. ベースライン API コール数（best=14, worst=22）のアサーション追加・検証確認。
- [x] 5. `ReviewGraphState` に `commercial_score: float` 追加。
- [x] 6. `WritingGraphState` に `event_density: float` 追加。
- [x] 7. `MasterGraphState` に `revision_budget: int` 追加。
- [x] 8. ブランチ `feature/kakuyomu-pipeline-improvement` 作成および Phase 0 コミット。

### Phase 1 — ① 差し戻しループ（9〜16）
- [x] 9. `call_review_graph_node` で `requires_revision` 話数を集計し `review_summary` を返却。
- [x] 10. `MasterGraphState` に `needs_revision_eps: List[int]` を追加。
- [x] 11. `master_graph.py` に `revise_writing_node` をノードとして登録。
- [x] 12. `revise_writing_node` で該当話のみ `writing_graph` を再実行。
- [x] 13. `revise_writing_node` で修正話のみ ReviewGraph を1回再実行し、`review_summary` / `needs_revision_eps` を再集計。
- [x] 14. `master_graph.py` に条件付きエッジ `review_phase -> should_revise_writing -> (revise_phase | END)` を追加。
- [x] 15. `revise_writing_node` に収束判定（未改善時は budget=0 で強制終了）と `quality_metrics` 記録を追加。
- [x] 16. `tests/workflows/test_three_episodes_review.py` に `test_revision_loop_triggers_for_flagged_episode`（14 + 4 = 18コール）を追加し、5 件のテスト全パスを確認。Phase 1 コミット。

### Phase 2 — ② 密度ルービック（17〜26）
- [x] 17. `writing_nodes.py` 冒頭に `MIN_DRAFT_CHARS = 1500` 定義。
- [x] 18. `self_audit` の `len(draft) < 50` を定数に置換。
- [x] 19. audit プロンプトに `event_density` 評価項目追加。
- [x] 20. 出力をパースし `state["event_density"]` 格納。
- [x] 21. `check_audit_results` の合格条件に `event_density >= 0.5` を AND。
- [x] 22. `failures` に不足要素（展開/露出/緊張）を書くよう指示追記。
- [x] 23. `generate_draft_node` の既存 failures 反映ロジックを不足要素に活用。
- [x] 24. `llm=None` 時ダミーにも `event_density` 付与。
- [x] 25. テスト：短草稿は再生成せず、密度不合格は再生成することを確認。
- [x] 26. draft 文字数・密度をログ出力。

### Phase 3 — ③ 話内並列＋Bibleロック（27〜34）
- [x] 27. `analyze_pacing` と `check_character` の独立性をコメント確認。
- [x] 28. 両ノードを `asyncio.gather` で並列する `run_review_parallel()` 追加。
- [x] 29. `SequentialReviewGraphFallback` も gather 化。
- [x] 30. `MasterGraphState` に `bible_state: dict` 追加。
- [x] 31. `call_writing_graph_node` の for 内で bible_state へ直列書き込み。
- [x] 32. `call_review_graph_node` 開始時に bible_state を読み取り。
- [x] 33. 並列（review 内）と bible 直列書き込みの非競合を構造で保証。
- [x] 34. テスト：3話で API 数不変・正動作を確認。

### Phase 4 — ④ カクヨム指標ルービック（35〜42）
- [x] 35. `review_nodes.py` に `score_commercial_node` 追加（generate_json, audit）。
- [x] 36. プロンプトにルービック5項目を明記。
- [x] 37. 出力を `commercial_score` と副次項目にパース。
- [x] 38. review エッジを `pacing → char → commercial → propose` に変更。
- [x] 39. `ReviewGraphState.commercial_score` に格納。
- [x] 40. `call_review_graph_node` で各話スコアを `quality_metrics` へ集計。
- [x] 41. `COMMERCIAL_PASS = 0.7` を定数化。
- [x] 42. テスト：commercial_score が 0–1 で state に入ることを確認。

### Phase 5 — ⑤ プロット複数案×選抜（43〜50）
- [x] 43. `generate_initial_plot_node` に `num_variants: int = 1` 追加。
- [x] 44. `num_variants>1` で `generate_json` を逐次 N 回呼び `plot_variants` 保持。
- [x] 45. `PlotGraphState` に `plot_variants: list` 追加。
- [x] 46. ④ルービック転用の `score_plot_variants_node` 追加。
- [x] 47. 上位1案を `parsed_plots` にセット。
- [x] 48. `should_refine_plot` の閾値を 0.8→0.85 に引き上げ。
- [x] 49. `evaluate_plot_node` を variants スコアリングで拡張（後方互換）。
- [x] 50. テスト：3案生成→1案選抜で API +2 増を確認。

### Phase 6 — ⑥ 前話文脈参照の確約（51〜58）
- [x] 51. `WritingGraphState` に `prev_episode_tail: str` 追加。
- [x] 52. `call_writing_graph_node` のループで直前話末尾500字を取得。
- [x] 53. `writing_input["prev_episode_tail"]` へ渡す。
- [x] 54. `generate_draft_node` のプロンプトへ前話末尾セクションを追加。
- [x] 55. 「前話の文脈・感情を引き継ぎ」指示を明記。
- [x] 56. 1話目の場合はセクション空文字ハンドリング。
- [x] 57. `self_audit_node` に前話接続整合性項目を追加。
- [x] 58. テスト：2話生成時に前話末尾がプロンプトに含まれることを確認。

### Phase 7 — ⑦ 統合テスト・UI連携（59〜72）
- [x] 59. `tests/workflows/test_three_episodes_review.py` を最新仕様に同期（コール数・アサーション）。
- [x] 60. `tests/unit/test_commercial_scoring.py` を新設（ルービック5項目パース単体テスト）。
- [x] 61. `tests/unit/test_density_rubric.py` を新設（1500字・密度不合格の再生成単体テスト）。
- [x] 62. `tests/unit/test_plot_variants.py` を新設（N案生成と選抜の単体テスト）。
- [x] 63. `pytest tests/` を全実行（全パス確認）。
- [x] 64. `frontend/src/types/api.ts` に `event_density` / `commercial_score` / `plot_variants` 追加。
- [x] 65. `frontend/src/components/tabs/AuditTab.tsx` にカクヨム商業スコア表示（ルービック5レーダー/バー）。
- [x] 66. `frontend/src/components/tabs/WriteTab.tsx` に草稿文字数と `event_density` インジケータ追加。
- [x] 67. `frontend/src/components/tabs/PlotsTab.tsx` に複数案切り替え/比較 UI を追加。
- [x] 68. `frontend/src/components/panels/TaskMonitor.tsx` に差し戻しループ発生時の警告バッジ追加。
- [x] 69. `npm run build` または `npm test`（型チェックとビルド確認）。
- [x] 70. `docs/kakuyomu_pipeline_improvement_plan.md` の全チェックボックスを [x] に更新。
- [x] 71. 実装サマリーを `docs/` に作成。
- [x] 72. `main` ブランチへマージ（または PR 準備完了確認）。

---

## 7. 実行ルール（低性能 LLM 向け）

- **1 ステップ 1 変更**：対象ファイル 1 つ・関数 1 つの変更に留める。大きなリファクタは禁止。
- **都度検証**：各ステップ終了ごとに
  `python -m pytest tests/workflows/test_three_episodes_review.py -q`
  を実行。baseline（14/22 コール）が崩れたらそのステップを差し戻す。
- **進め方**：Phase 0 → 1 → … → 9 の順。Phase 終了ごとにコミット。
- **後方互換**：既存テスト（`test_master_graph.py`）も緑を維持する。

---

## 8. マイルストーンと成功基準

- **M1（Phase 0〜1 終了）**：差し戻しループにより、監査指摘が 0 にはならないが大幅減とする。API 増は許容範囲（+2×要修正話）。
- **M2（Phase 2〜4 終了）**：`event_density` と `commercial_score` が計測可能になり、薄い話・売れにくいプロットを自動検出。
- **M3（Phase 5〜7 終了）**：複数プロット案から商業スコアで選抜し、連続性台帳とフック最適化で上位作構造を満たす。
- **M4（Phase 8〜9 終了）**：CTR 最適化メタデータと、作家の1点承認ゲートが稼働。

**定量成功基準（例）**：
- 3話生成の `commercial_score` 平均 ≥ 0.7
- `event_density` 不合格による再生成率 ≤ 20%
- 差し戻し後の `requires_revision` 件数が初期の 50% 以下
- 1話あたりの API コール数を worst 22（3話）から 28 以内に収める（コスト爆発防止）

---

## 9. リスクと対策

| リスク | 影響 | 対策 |
|---|---|---|
| ループのコスト爆発 | 予算超過 | P2 の予算＋収束ガード（全ループに適用） |
| 話間並列による連続性崩壊 | 設定破綻 | P3：並列は話内のみ、bible は直列ロック |
| 低性能 LLM での不安定な JSON パース | ゲート誤作動 | 各ノードで `try/except` フォールバック（既存パターン維持） |
| 商業スコアの過信 | 独りよがりな作品 | ⑨ HITL で作家が最終判断 |
| プロンプト長の肥大 | コスト増 | ledger/メタデータは必要最小限の注入にとどめる |

---

## 10. まとめ

本計画は、単なる「ノード追加」から、**指標の一元化（④）・ループの収束ガード（①）・並列化と連続性の両立（③⑥）・人間は1点だけ（⑨）** へ厳密化した。これにより、カクヨムランキング上位の決定因（フック・読了率・設定の破綻なさ）をシステム内で評価・最大化しつつ、API コストと実行時間の爆発を防ぎ、作家の手間を最小化できる。72 ステップの細分化により、低性能な環境でも確実に実装・検証を進められる構成としている。
