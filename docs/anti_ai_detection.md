# Anti-AI Detection & Correction System

AI生成テキストの痕跡を検出し、自動的に修正するシステム。

## アーキテクチャ

```
WritingAgent.generate_draft()
    │
    ▼
RuleBasedAntiAIDetector (7カテゴリ検出)
    │
    ▼
AntiAICorrector (カテゴリ別修正)
    │
    ▼
AntiAILoopController (反復制御)
    │
    ▼
最終テキスト → EpisodePipeline
```

## 7カテゴリ

| カテゴリ | 説明 | パターン例 |
|---------|------|----------|
| TRANSITION_OVERUSE | 冗長な接続詞 | しかし、また、さらに |
| SAME_STRUCTURE | 同一構文の連続 | 「〜だった。〜だった。」 |
| DIRECT_EMOTION | 直接的な内言 | 「〜と思った」「〜と感じた」 |
| HEDGING_PATTERNS | 曖昧表現 | 「〜かもしれません」「〜だろう」 |
| TEMPLATE_PHRASES | 論文調フレーズ | 「重要なことに」「結論として」 |
| UNIFORM_PARAGRAPH | 段落長均一 | ±5文字差で3連続 |
| GENERIC_VOCABULARY | 抽象語 | 「素晴らしい」「重要な」 |

## 設定

`config/anti_ai_config.yaml` で各カテゴリのパラメータを調整可能。

### 検出パラメータ

```yaml
detectors:
  TRANSITION_OVERUSE:
    enabled: true
    density_threshold: 0.33  # 3文に1回以上で違反
    weight: 1.0
  SAME_STRUCTURE:
    enabled: true
    consecutive_count: 3  # 3連続以上で違反
    weight: 1.5
```

### ループパラメータ

```yaml
loop:
  max_iterations: 2        # 最大反復回数
  stop_threshold: 70.0    # このスコア以上で停止
  min_improvement: 2.0      # この値を下回ると早期終了
  backoff_base_seconds: 0.0 # 指数バックオフ（秒）
```

## API

### 管理画面 API

```
POST /admin/anti_ai/detect
  Body: { "text": "検出したいテキスト" }
  Response: { total_score, category_scores, total_violations, violations }

POST /admin/anti_ai/correct
  Body: { "text": "修正したいテキスト", "max_loops": 3, "score_threshold": 90.0 }
  Response: { original_text, corrected_text, final_score, iterations, converged, history }

GET /admin/anti_ai/config
  Response: { enabled, categories }
```

### Python API

```python
from src.services.anti_ai import RuleBasedAntiAIDetector, AntiAICorrector, AntiAILoopController

# 検出のみ
detector = RuleBasedAntiAIDetector()
result = detector.detect(text)

# 修正のみ
corrector = AntiAICorrector()
correction = corrector.correct(text, result.violations)

# 検出→修正の反復
controller = AntiAILoopController(max_loops=3, score_threshold=90.0)
loop_result = controller.run_sync(text)
```

## Specialist Auditor

`StyleAuditor` と統合されており、スタイルスコアにAnti-AIスコアを反映可能。

```python
from src.agents.specialists.style_auditor import StyleAuditor

auditor = StyleAuditor(
    enable_anti_ai=True,
    anti_ai_weight=0.1  # Anti-AIスコアの影響度（デフォルト10%）
)
```

## Prometheus メトリクス

| メトリクス | タイプ | 説明 |
|-----------|--------|------|
| anti_ai_detection_total | Counter | 検出数（カテゴリ別） |
| anti_ai_corrections_total | Counter | 修正数（カテゴリ別） |
| anti_ai_loop_iterations | Histogram | 反復回数分布 |
| anti_ai_score | Gauge | 現在のスコア |

## スコア計算

スコアは0-100の範囲：
- 100: 違反なし（クリーン）
- 0: 全カテゴリで最大違反

カテゴリ別スコアを重み付けして合計スコアを算出：

```
total_score = Σ(category_score × weight) / Σ(weight)
```

デフォルト重み：
- SAME_STRUCTURE: 1.5（高）
- TEMPLATE_PHRASES: 1.2（中）
- DIRECT_EMOTION: 1.0（標準）
- TRANSITION_OVERUSE: 1.0（標準）
- HEDGING_PATTERNS: 0.8（低）
- GENERIC_VOCABULARY: 0.7（低）
- UNIFORM_PARAGRAPH: 0.6（低）

## 運用ガイド

### 閾値設定

- `stop_threshold: 70.0` - 最低品質基準
- `stop_threshold: 85.0` - 高品質要求時
- `stop_threshold: 95.0` - 非常に高い品質要求時

### パフォーマンス

- 2700文字テキスト: ~19ms
- 目標: 100ms以内

### LLM統合

オプションでLLMサニティチェックを有効化可能：

```yaml
llm_sanity_check:
  enabled: true
  max_calls_per_chapter: 3
  max_total_tokens: 1000
  trigger_below_score: 60.0
```
