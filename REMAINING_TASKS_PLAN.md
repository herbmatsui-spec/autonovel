# Anti-AI Detection & Correction Loop - 残タスク詳細実装計画書

## 現状確認

### 完了済み
- Steps 1-72 のうち大半が完了
- コミット済み: `dcd3e38`
- テスト: 80 tests passing
- パフォーマンス: 18.6ms / 2700chars (目標 <100ms)

### 残タスク一覧

| Step | 内容 | 優先度 | 難易度 |
|------|------|--------|--------|
| 61 | バックオフロジック | 中 | 低 |
| 53 | StyleAuditor との統合 | 高 | 中 |
| 62 | Loop Controller テスト | 高 | 低 |
| 54 | AntiAIDetector テスト | 高 | 低 |
| 64 | Prometheus メトリクス | 低 | 中 |
| 65 | YAML 設定読み込み | 中 | 低 |
| 71 | ドキュメント作成 | 低 | 低 |
| - | loop_controller.py バグ修正 | 高 | 低 |

---

## 1. loop_controller.py バグ修正 (最優先)

### 問題
`loop_controller.py:111` で `output_score` に修正前のスコアを設定している。

### 修正内容
```python
# 現在 (バグ):
history.append(CorrectionHistory(
    iteration=iteration,
    input_score=current_score,
    output_score=result.total_score,  # ← 修正前のスコア
    ...
))

# 修正後:
history.append(CorrectionHistory(
    iteration=iteration,
    input_score=current_score,
    output_score=correction_result.total_changes,  # 修正数を記録
    ...
))
```

### 担当: 10分

---

## 2. StyleAuditor との統合 (Step 53)

### 目的
`StyleAuditor` に `anti_ai_score` を反映させ、全身的な品質スコア算出を可能にする。

### 修正ファイル
`src/agents/specialists/style_auditor.py`

### 修正内容
1. `StyleAuditor.__init__` に `anti_ai_weight: float = 0.1` パラメータ追加
2. `audit()` メソッドで `AntiAIDetector` を呼び出し
3. 最終スコアに `anti_ai_score * anti_ai_weight` を反映

```python
async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
    # 既存のスタイル監査
    style_score = ...  # 現在のロジック

    # Anti-AI スコア取得
    anti_ai = AntiAIDetector()
    anti_result = await anti_ai.audit(ctx)
    anti_ai_score = anti_result.score

    # 重み付けで合計スコア算出
    combined_score = (
        style_score * (1 - self.anti_ai_weight) +
        anti_ai_score * self.anti_ai_weight
    )

    return SpecialistAuditResult(
        "style",
        round(combined_score, 1),
        feedback={
            **feedback,
            "anti_ai_score": anti_ai_score,
        },
        ...
    )
```

### 担当: 30分

---

## 3. Loop Controller ユニットテスト (Step 62)

### テストファイル
`tests/unit/anti_ai/test_loop_controller.py`

### テストケース

```python
class TestAntiAILoopController:
    def test_converges_within_max_loops(self) -> None:
        """スコアが閾値に到達したら早期終了"""
        controller = AntiAILoopController(max_loops=5, score_threshold=90.0)
        result = controller.run_sync(AI_TEXT)
        assert result.converged is True
        assert result.iterations <= 5

    def test_stops_when_no_violations(self) -> None:
        """違反ゼロで終了"""
        controller = AntiAILoopController(max_loops=5, score_threshold=90.0)
        result = controller.run_sync(CLEAN_TEXT)
        assert result.converged is True
        assert result.iterations == 0

    def test_respects_max_loops(self) -> None:
        """最大ループ数を守って終了"""
        controller = AntiAILoopController(max_loops=2, score_threshold=100.0)
        result = controller.run_sync(AI_TEXT)
        assert result.iterations <= 2

    def test_history_records_each_iteration(self) -> None:
        """各イテレーションが記録される"""
        controller = AntiAILoopController(max_loops=3, score_threshold=90.0)
        result = controller.run_sync(AI_TEXT)
        assert len(result.history) == result.iterations
        for h in result.history:
            assert h.iteration > 0
            assert h.violations_found >= 0

    def test_empty_text_returns_clean(self) -> None:
        """空テキストはスコア100で終了"""
        controller = AntiAILoopController()
        result = controller.run_sync("")
        assert result.final_score == 100.0
        assert result.converged is True
```

### 担当: 45分

---

## 4. AntiAIDetector ユニットテスト (Step 54)

### テストファイル
`tests/unit/anti_ai/test_anti_ai_detector.py`

### テストケース

```python
class TestAntiAIDetector:
    def test_returns_score_in_range(self) -> None:
        """スコアは0-100の範囲"""
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": AI_TEXT}))
        assert 0 <= result.score <= 100

    def test_empty_text_returns_zero(self) -> None:
        """空テキストはスコア0"""
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": ""}))
        assert result.score == 0.0

    def test_includes_category_scores_in_feedback(self) -> None:
        """フィードバックにカテゴリ別スコアを含む"""
        auditor = AntiAIDetector()
        result = asyncio.run(auditor.audit({"draft_text": AI_TEXT}))
        assert "category_scores" in result.feedback
        assert "total_violations" in result.feedback

    def test_sync_fallback_works(self) -> None:
        """同期フォールバックが動作"""
        auditor = AntiAIDetector()
        result = auditor._sync_audit({"draft_text": AI_TEXT})
        assert 0 <= result.score <= 100
        assert result.degraded is True

    def test_specialist_name(self) -> None:
        """specialist_name が正しく設定"""
        auditor = AntiAIDetector()
        assert auditor.specialist_name == "anti_ai"
```

### 担当: 45分

---

## 5. バックオフロジック (Step 61)

### 修正ファイル
`src/services/anti_ai/loop_controller.py`

### 修正内容
ループ内で改善がない場合に指数バックオフで待機:

```python
async def run(self, text: str, ...) -> LoopResult:
    ...
    for iteration in range(1, max_loops + 1):
        result = self._detector.detect(current_text)
        ...

        correction_result = self._corrector.correct(current_text, result.violations)

        # バックオフ判定
        if iteration > 1 and score_improvement < self._min_score_improvement:
            backoff_time = self._backoff_base ** (iteration - 1)
            logger.info("Backing off for %.1f seconds", backoff_time)
            await asyncio.sleep(backoff_time)

        ...

class AntiAILoopController:
    def __init__(self, ..., backoff_base: float = 2.0) -> None:
        ...
        self._backoff_base = backoff_base
```

### 担当: 30分

---

## 6. Prometheus メトリクス (Step 64)

### 目的
運用監視のためにメトリクスを公開

### 修正ファイル
`src/services/anti_ai/metrics.py` (新規)

### 実装内容
```python
from prometheus_client import Counter, Histogram, Gauge

anti_ai_detection_total = Counter(
    "anti_ai_detection_total",
    "Total number of anti-AI detections",
    ["category", "method"]
)

anti_ai_corrections_total = Counter(
    "anti_ai_corrections_total",
    "Total number of corrections applied",
    ["category"]
)

anti_ai_loop_iterations = Histogram(
    "anti_ai_loop_iterations",
    "Number of iterations per correction loop",
    buckets=[1, 2, 3, 5, 10]
)

anti_ai_score = Gauge(
    "anti_ai_score",
    "Current anti-AI score after correction"
)
```

### 担当: 30分

---

## 7. YAML 設定読み込み (Step 65)

### 修正ファイル
`src/services/anti_ai/loop_controller.py`

### 修正内容
`AntiAIConfig` からループパラメータを読み込む:

```python
class AntiAILoopController:
    def __init__(
        self,
        config: AntiAIConfig | None = None,
        ...
    ) -> None:
        if config:
            self._max_loops = config.max_loops
            self._score_threshold = config.score_threshold
            self._min_score_improvement = config.min_score_improvement
        ...
```

### 担当: 20分

---

## 8. ドキュメント作成 (Step 71)

### 目的
運用者がシステムを理解・設定できるようにする

### ファイル
`docs/anti_ai_detection.md`

### 内容
1. 各カテゴリの説明と検出パターン
2. 閾値の根拠
3. 設定ガイド
4. API ドキュメント

### 担当: 60分

---

## 実装順序

1. **loop_controller.py バグ修正** (10分) - 最優先
2. **Step 62: Loop Controller テスト** (45分)
3. **Step 54: AntiAIDetector テスト** (45分)
4. **Step 53: StyleAuditor 統合** (30分)
5. **Step 61: バックオフロジック** (30分)
6. **Step 65: YAML 設定読み込み** (20分)
7. **Step 64: Prometheus メトリクス** (30分)
8. **Step 71: ドキュメント** (60分)

**合計: 約4.5時間**

---

## 検証方法

各ステップ完了後に以下を実行:
```bash
# ユニットテスト
python -m pytest tests/unit/anti_ai/ -v

# E2E テスト
python -m pytest tests/e2e/test_anti_ai_full_flow.py -v

# パフォーマンステスト
python -c "import time; ..."
```

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| テストが既存の足を引っ張る | 既存テストを先に実行してベースライン確認 |
| バックオフで処理が遅くなる | デフォルトで無効化、設定で有効化 |
| メトリクスが追加のオーバーヘッド | Counter は原子操作で軽量 |
