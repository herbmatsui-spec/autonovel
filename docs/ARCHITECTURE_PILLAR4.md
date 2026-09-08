# 第4の柱 アーキテクチャ仕様書：評価・閉ループPDCA統合システム

## 1. 概要
本仕様書は、AutoNovelにおける「第4の柱：評価・閉ループPDCAの統合」のアーキテクチャ、データフロー、数学モデル、および商業品質基準を定義します。

---

## 2. 全体アーキテクチャ

```mermaid
graph TD
    subgraph Specialist Audit Layer [1. 専門家アンカー監査]
        Draft[生成ドラフト] --> Aud8[8専門家Auditor]
        Anchors[High/Mid/Low アンカー事例] -.-> Aud8
        Aud8 --> RawScores[生スコア 8名]
        Aud8 --> ActionDiffs[Actionable Diff]
    end

    subgraph Calibration & Mapping Layer [2. キャリブレーション & 5D変換]
        RawScores --> Calibrator[ScoreCalibrator (Z-Score + Prior Shrink)]
        Calibrator --> CalScores[キャリブレーション済スコア]
        CalScores --> Bridge[UnifiedBookScoreBridge]
        Overrides[ジャンル別・フェーズ別重み] -.-> Bridge
        Bridge --> BookScore5D[5次元 BookScore (0-100)]
    end

    subgraph Closed-Loop PDCA Layer [3. クローズドループ再執筆]
        BookScore5D --> DirectiveGen[PDCADirectiveGenerator]
        ActionDiffs --> DirectiveGen
        DirectiveGen --> Directives[WritingDirective (制約プロンプト)]
        Directives --> PDCARunner[ClosedLoopPDCARunner]
        PDCARunner --> Writer[WriterAgent (局所再執筆)]
    end

    subgraph Dynamic DAG Replanning Layer [4. DAG動的リプランニング]
        BookScore5D -->|不合格/足切り| DAGReplanner[DAGReplanner]
        DAGReplanner --> CancelDownstream[下流タスクの安全キャンセル]
        DAGReplanner --> RetryNode[対象ノードの局所リトライ]
        RetryNode --> Reactivate[成功後の自動再アクティベート]
        DAGReplanner --> EventBus[EventBus 'dag.replanned']
    end

    subgraph Commercial Benchmark Layer [5. 商業品質基準判定]
        Writer --> RevisedDraft[改訂ドラフト]
        RevisedDraft --> Benchmark[CommercialBenchmarkJudge]
        Benchmark --> Grade[S/A/B/C/D 判定]
        Benchmark --> Health[7-Point Health Check]
    end
```

---

## 3. 主要コンポーネント

### 3.1 専門家アンカー事例とActionable Diff (`src/agents/specialists/anchors.py`)
- **8専門家**: `reader_hook`, `structure`, `character_depth`, `style`, `emotion_curve`, `consistency`, `theme`, `multimodal`
- **アンカー構造**: 各専門家に `high (85+)`, `mid (65)`, `low (40)` のテキスト見本、講評、着眼点を注入し、採点ドリフトを防止。
- **Actionable Diff**: 抽象的な批判ではなく、`location`（該当箇所）、`original_quote`（原文引用）、`improved_suggestion`（改善案）、`rationale`（理由）を厳密抽出。

### 3.2 スコアキャリブレーション (`src/services/score_calibrator.py`)
- **事前分布（Priors）**: 専門家ごとの平均 $\mu$ と標準偏差 $\sigma$。
- **ベイズ的シュリンク**: サンプル数 $n$ に応じて事前分布へ引き戻し:
  $$w = \frac{n}{n + \lambda}$$
- **シグモイドスケーリング**: 外れ値スコアの平滑化と 0〜100 の有界保証。
- **分散ペナルティ**: 専門家間スコアの標準偏差が 18.0 を超える場合、減点ペナルティを課す。

### 3.3 統一5D BookScoreブリッジ (`src/services/book_score_mapping.py`)
- 8専門家の評価を 5次元（構成力、人物描写力、論理整合性、世界観構築力、テーマ性）へ数理的にマッピング。
- 欠損専門家がある場合は、比例再正規化（Proportional Renormalization）で合計重み 1.0 を維持。
- ジャンル別（異世界ファンタジー、現代恋愛等）および生成フェーズ別の動的重みシフター。

### 3.4 クローズドループPDCA (`src/services/pdca_directive.py`, `src/services/pdca_cycle.py`)
- 最低スコア次元と Actionable Diff を結合し、執筆プロンプトへの「必須制約」ディレクティブへ変換。
- 改善率計算：
  $$\text{Improvement Rate} = \frac{\text{Score}_{\text{after}} - \text{Score}_{\text{before}}}{\max(1, \text{Score}_{\text{before}})} \times 100\%$$
- 収束・早期終了判定（目標スコア到達、または改善率停滞検知）。

### 3.5 DAG動的リプランニング (`src/backend/tasks/dag_replanning.py`, `src/backend/tasks/dag_scheduler.py`)
- 監査不合格時、DAGグラフ全体を再実行するのではなく、ドラフト生成ノードのみを局所リトライ。
- BFS走査により下流タスク（イラスト生成、EPUBエクスポート等）のみを安全にキャンセル・ロールバック。
- リトライ成功時に下流ノードを自動再アクティベート。
- 最大リトライ数（3回）到達時の安全なフェイルセーフ。

### 3.6 商業水準ベンチマーク (`src/services/commercial_benchmarks.py`)
- **商業出版水準 (Sランク)**: 総合スコア $\ge 85.0$ かつ 全次元 $\ge 70.0$
- **Web連載人気水準 (Aランク)**: 総合スコア $\ge 75.0$ かつ 全次元 $\ge 65.0$
- **致命的欠陥足切り (Fatal Flaw)**: いずれかの次元が $< 60.0$ の場合は無条件不合格
- **PDCA改善目標**: 最低 $+15.0\%$ のスコア改善
- **7-Point Health Check**: 全7サブシステムの稼働健全性を 100% 検証。
