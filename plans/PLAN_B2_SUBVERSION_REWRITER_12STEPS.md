# PLAN_B2: 生成後リライター・アプローチ（中間・確実制御）

**目標**: LLM生成後の `ArcList` / `EpisodeBeat` を後処理で書き換える `SubversionRewriter` クラスを導入し、既存モデル・エージェント構造を**一切変更せず**に「3話ごとの裏切り」を確実に注入する。

**特徴**: 
- 既存 `PlotEpisode` / `ArcBlueprint` / `EpisodeBeat` に手を入れない
- `PlanningAgent` への注入ポイントは `generate_arcs()` 末尾と `generate_commercial_beat_sheet()` 末尾のみ
- 低性能LLMでも実装しやすい手続き的ロジック中心

---

## Step 1: `src/agents/subversion_rewriter.py` 新規作成（コアロジック）

**作業内容**
- `SubversionRewriter` クラス定義
- 定数 `PATTERNS = {"A": ..., "B": ..., "C": ...}` 定義
- `rewrite_arcs(arcs: ArcList, target_eps: int, start_ep: int) -> ArcList`
- `rewrite_beats(beats: list[EpisodeBeat], target_eps: int) -> list[EpisodeBeat]`
- 決定論的パターン選択（`hash(f"{ep}_{target_eps}")` 等）

**受け入れ基準**
- `python -c "from src.agents.subversion_rewriter import SubversionRewriter; r=SubversionRewriter(); arcs=r.rewrite_arcs(ArcList(arcs=[]), 40, 1); print('ok')"` がエラーなく動く

**テスト作成**: `tests/test_subversion_rewriter.py::test_rewrite_arcs_structure`

---

## Step 2: パターン適用ロジックの単体テスト

**作業内容**
- `ArcBlueprint` の `thematic_milestone` / `summary` に裏切り文言が注入されることを確認
- 3話ごと（3,6,9...）のみ注入され、それ以外は変更されないことを確認
- パターンA/B/C がラウンドロビンまたはハッシュベースで偏りなく割り当てられることを確認

**受け入れ基準**: `pytest tests/test_subversion_rewriter.py::test_pattern_distribution -v` が通る

---

## Step 3: `EpisodeBeat` 書き換えロジック・テスト

**作業内容**
- `rewrite_beats()` で `mission`/`visual_scene_focus`/`tension_target` が更新されることを確認
- `tension_target` が `min(1.0, original + 0.3)` でクリップされることを確認
- 元のビートオブジェクトがミュータブルに書き換えられるか、新規オブジェクト返却かを統一（推奨: 新規リスト返却）

**受け入れ基準**: `pytest tests/test_subversion_rewriter.py::test_rewrite_beats_mutation -v` が通る

---

## Step 4: 設定パラメータ対応

**作業内容**
- `enabled: bool = True` / `interval: int = 3` / `pattern_weights: dict` を `__init__` 引数で受け取り
- `enabled=False` で無操作パススルー
- `pattern_weights` 未指定時は均等配分

**受け入れ基準**: `SubversionRewriter(enabled=False).rewrite_arcs(...)` が入力をそのまま返す

**テスト作成**: `tests/test_subversion_rewriter.py::test_disabled_passthrough`

---

## Step 5: `PlanningAgent.generate_arcs()` への注入

**作業内容**
- `from src.agents.subversion_rewriter import SubversionRewriter` インポート
- LLM生成直後の `arcs` に対して `rewriter.rewrite_arcs(arcs, target_eps, start_ep)` 呼び出し
- 設定値は `ctx.artifacts.get("subversion", {})` から取得
- 戻り値の `ArcList` をそのまま返却（互換性維持）

**受け入れ基準**: 既存 `generate_arcs` テストが全通過 + 新規テストで裏切り注入確認

**テスト作成**: `tests/test_planning_agent.py::test_generate_arcs_rewriter_injection`

---

## Step 6: `generate_commercial_beat_sheet()` への注入

**作業内容**
- 同一 `SubversionRewriter` インスタンス（または同一設定で新規生成）で `rewrite_beats(beats, 40)` 呼び出し
- 戻り値の `list[EpisodeBeat]` を返却

**受け入れ基準**: 3の倍数話のビートで `mission` に「【裏切り-X】」プレフィクスが付く

**テスト作成**: `tests/test_planning_agent.py::test_beat_sheet_rewriter_injection`

---

## Step 7: 再現性確保（シード固定）

**作業内容**
- `SubversionRewriter` に `seed: str | int` パラメータ追加
- パターン選択・文言バリエーションに `hash(seed + str(ep))` を使用
- `ctx.artifacts.get("subversion_seed", "default")` を渡す

**受け入れ基準**: 同一シード・同一話数で2回実行すると完全同一の注入結果になる

**テスト作成**: `tests/test_subversion_rewriter.py::test_deterministic_with_seed`

---

## Step 8: 整合性検証メソッド追加

**作業内容**
- `validate(arcs: ArcList, beats: list[EpisodeBeat]) -> list[str]` 実装
- Arc側とBeat側で裏切り話数が一致すること
- 間隔・重複・終盤負荷のチェック

**受け入れ基準**: 検証エラーが空リストで返る正常ケースと、意図的破綻ケースでエラー検出

**テスト作成**: `tests/test_subversion_rewriter.py::test_validate_consistency`

---

## Step 9: `PlanningAgent.execute()` で検証実行・ログ出力

**作業内容**
- Arc生成・Beat生成後に `rewriter.validate(arcs, beats)` 呼び出し
- エラーがある場合 `logger.warning` で出力（失敗にはしない）
- `artifacts["subversion_validation"] = errors` で保存

**受け入れ基準**: 検証エラーがログに出力され、artifacts に残る

---

## Step 10: 既存テストスイートのリグレッション確認

**作業内容**
- `pytest tests/ -k "planning or plot" --tb=short` 実行
- `SubversionRewriter` 導入前後で出力構造（フィールド名・型・ネスト）が変わらないことを確認
- `ArcList` / `EpisodeBeat` の Pydantic バリデーションが通ることを確認

**受け入れ基準**: 全テスト通過。破壊的変更なし。

---

## Step 11: 設定ドキュメント・使用例追加

**作業内容**
- `docs/guides/subversion_rewriter.md` 作成
  - 設定項目一覧
  - パターン文言カスタマイズ方法（サブクラス化 or 設定注入）
  - 無効化手順
- `kilo.json` 設定例追記

**受け入れ基準**: ドキュメント存在。新規メンバーが読んで設定変更できるレベル。

---

## Step 13: CI/CD 統合・回帰防止テスト追加

**作業内容**
- `tests/test_subversion_regression.py` 作成
  - Step 1-9 の要点を統合したエンドツーエンドテスト
  - `enabled=False` / `enabled=True` / `interval=2` / `custom_weights` の4ケース
- GitHub Actions / CI 設定に `pytest tests/test_subversion_regression.py` 追加

**受け入れ基準**: CI でグリーン。リグレッション検知可能。

---

## 依存関係グラフ

```
Step 1 → Step 2,3,4
Step 2,3,4 → Step 7,8
Step 1,5 → Step 5 (generate_arcs注入)
Step 1,6 → Step 6 (beat_sheet注入)
Step 5,6,7,8 → Step 9
Step 9 → Step 10
Step 10 → Step 11,12
```

## 並行実行可能グループ
- Group A: Step 1 (独立)
- Group B: Step 2, 3, 4 (Step 1 後)
- Group C: Step 5, 6 (Step 1 後、独立)
- Group D: Step 7, 8 (Step 2,3,4 後)
- Group E: Step 9, 10, 11, 12 (順次)