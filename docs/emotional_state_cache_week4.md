# 感情状態キャッシュ Week 4 - 融合レイヤー＋矛盾検出・アラート 運用ガイド

## 1. 概要
Week 4 では、3つの感情ソース（Pipeline: 自動抽出, RuleEngine: プロットルール推定, Annotation: 作者明示指定）の感情ベクトルを統合する「融合レイヤー」を構築しました。
矛盾の自動検出、信頼度ベースの仲裁、加重平均ブレンディング、手動解決API、および執筆エージェントへのプロンプト注入を提供します。

## 2. アーキテクチャ
```
[Annotation]      [RuleEngine]      [Pipeline]
     │                 │                 │
     └─────────┬───────┴─────────┬───────┘
               ▼                 ▼
        [VectorCollector] (全ソース収集)
               │
               ▼
       [ConflictDetector] (符号反転 & 有意差矛盾検出)
               │
               ▼
          [Arbitrator] (信頼度ベース仲裁 / 加重平均ブレンディング)
               │
        ┌──────┴──────────────────┐
        ▼                         ▼
  [FusedVector]            [ConflictStore] (矛盾記録 & 手動解決)
        │
  [PromptBuilder] -> Jinja2 Template (Writer Agent プロンプト注入)
```

## 3. 設定 (`config/fusion.yaml`)
- `source_confidence`: ソースごとのデフォルト信頼度
  - `annotation`: 1.0 (最優先)
  - `rule_engine`: 0.8
  - `pipeline`: 0.5
- `conflict_threshold`: 0.3 (絶対値差がこれ以上で矛盾と判定)
- `significance_threshold`: 0.3 (両者がこの絶対値以上の場合のみ矛盾判定)
- `mode`: `weighted_blend` または `highest_confidence`
- `conflict_penalty`: 0.2 (矛盾時の信頼度減衰ペナルティ)

## 4. API と CLI
### 矛盾解決 API (`src/api/conflicts.py`)
- `GET /api/conflicts?episode=15`: 該当話の矛盾一覧
- `GET /api/conflicts/{conflict_id}`: 詳細
- `POST /api/conflicts/{conflict_id}/resolve`: 手動解決の記録（`annotation`, `rule_engine`, `pipeline`, `manual`）

### デバッグ CLI (`src/fusion/debug_cli.py`)
```bash
python -m src.fusion.debug_cli show --episode 15 --source A --target B
python -m src.fusion.debug_cli conflicts --episode 15
python -m src.fusion.debug_cli explain --episode 15 --source A --target B --emotion fear
```
