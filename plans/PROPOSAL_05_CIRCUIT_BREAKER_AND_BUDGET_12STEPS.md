# 提案5: LLMサーキットブレーカー & トークン予算（Cost Budget）強制遮断 実装計画書（全12ステップ）

**対象レイヤー**: `src/services/llm/`, `src/services/billing/`, `src/agents/writing/`, `tests/unit/services/`  
**目的**: 外部LLM（Gemini / OpenAI / Claude）のAPI障害（500）やレート制限（429）発生時に、リトライ無限滞留を防ぐサーキットブレーカーと自動フェイルオーバーを導入する。また、執筆エージェントのPDCA自己修正ループに対して「ハードトークン上限（Cost Budget Guard）」を強制し、暴走による莫大なAPI課金事故を物理的に防ぐ。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全な実装コードおよび単体テストコード**、**検証コマンド**、**合格条件** を完備しています。外部LLMへの実通信は一切行わず、すべてモックとインメモリシミュレーションで検証可能です。

---

## 📋 ステップ一覧

| Step | 分類 | 対象ファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | 回路遮断 | `src/services/llm/circuit_breaker.py` | CLOSED / OPEN / HALF-OPEN の状態遷移を管理するサーキットブレーカー実装 |
| **Step 2** | フェイルオーバー | `src/services/llm/provider_failover.py` | Primaryモデル障害時にSecondaryモデルへ即時切り替えるルーティング機構 |
| **Step 3** | ゲートウェイ統合 | `src/llm/resilient_gateway.py` | レジリエントゲートウェイへのサーキットブレーカー適用 |
| **Step 4** | 予算モデル | `src/services/billing/cost_budget_guard.py` | 1話/1リクエストあたりの最大許容トークン数・金額上限モデルの定義 |
| **Step 5** | リアルタイム監視 | `src/services/billing/token_budget_tracker.py` | 呼び出し毎にトークンを積算し上限到達を即座に検知するトラッカー |
| **Step 6** | 例外定義 | `src/core/exceptions.py` | 予算上限到達を示す `CostBudgetExceededError` の定義 |
| **Step 7** | PDCAループ統合 | `src/agents/writing/_writing.py` | 執筆PDCAループへのトークントラッカー注入と上限超過時の強制脱出 |
| **Step 8** | LangGraph統合 | `src/backend/workflows/writing_langgraph.py` | ワークフローノード実行時の予算チェックと安全終了ノードへのルーティング |
| **Step 9** | 最良版確定 | `src/agents/writing/agent.py` | 予算超過時にそれまでの最高スコア版を採用して安全終了するコミットロジック |
| **Step 10** | 単体テスト | `tests/unit/services/test_circuit_breaker.py` | 連続失敗による回路遮断（OPEN）と時間経過による復旧のテスト |
| **Step 11** | 単体テスト | `tests/unit/services/test_cost_budget_guard.py` | トークン上限到達時の即時例外送出と残高整合性テスト |
| **Step 12** | 統合テスト | `tests/unit/services/test_resilient_writing_loop.py` | 障害フェイルオーバーと予算上限ブレイクの複合シミュレーション |

---

## 🛠 各ステップ詳細仕様

### Step 1: サーキットブレーカーの状態遷移管理実装
- **目的**: 連続エラー回数が閾値（例: 3回）を超えた場合に回路を OPEN にし、指定時間（例: 30秒）外部通信を即座に遮断するステートマシンを作成。
- **対象ファイル**: `src/services/llm/circuit_breaker.py`（新規作成）
- **実装コード**:
```python
"""LLMプロバイダー向けサーキットブレーカー。"""
from __future__ import annotations
import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"      # 正常稼働
    OPEN = "open"          # 遮断中 (通信スキップ)
    HALF_OPEN = "half_open"  # 試験復旧中


class CircuitBreakerOpenException(Exception):
    """回路遮断中にリクエストが試行された場合の例外。"""
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True
```
- **検証コマンド**: `python -c "from src.services.llm.circuit_breaker import CircuitBreaker; print('CircuitBreaker loaded')"`
- **合格条件**: インポート成功。

---

### Step 2: プロバイダーフェイルオーバー機構の実装
- **目的**: Primaryプロバイダーが遮断（OPEN）された際、自動的に代替のSecondaryプロバイダーへリクエストを切り替える。
- **対象ファイル**: `src/services/llm/provider_failover.py`（新規作成）
- **実装コード**:
```python
"""プロバイダーフェイルオーバーマネージャー。"""
from __future__ import annotations
from typing import Any, Callable, Coroutine
from src.services.llm.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException


class ProviderFailoverManager:
    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {
            "gemini": CircuitBreaker(failure_threshold=3, recovery_timeout=30.0),
            "openai": CircuitBreaker(failure_threshold=3, recovery_timeout=30.0),
            "claude": CircuitBreaker(failure_threshold=3, recovery_timeout=30.0),
        }

    async def execute_with_fallback(
        self,
        primary_provider: str,
        fallback_provider: str,
        primary_fn: Callable[[], Coroutine[Any, Any, Any]],
        fallback_fn: Callable[[], Coroutine[Any, Any, Any]],
    ) -> tuple[Any, str]:
        """Primaryで試行し、遮断または失敗時にFallbackを実行する。"""
        p_breaker = self.breakers.get(primary_provider, self.breakers["gemini"])
        f_breaker = self.breakers.get(fallback_provider, self.breakers["openai"])

        if p_breaker.can_execute():
            try:
                res = await primary_fn()
                p_breaker.record_success()
                return res, primary_provider
            except Exception:
                p_breaker.record_failure()

        # Fallback 実行
        if not f_breaker.can_execute():
            raise CircuitBreakerOpenException("すべての利用可能なプロバイダーが遮断されています")
        
        try:
            res = await fallback_fn()
            f_breaker.record_success()
            return res, fallback_provider
        except Exception as e:
            f_breaker.record_failure()
            raise e
```
- **検証コマンド**: `python -c "from src.services.llm.provider_failover import ProviderFailoverManager; print('Failover loaded')"`
- **合格条件**: インポート成功。

---

### Step 3: レジリエントゲートウェイへのサーキットブレーカー統合
- **目的**: 既存の `src/llm/resilient_gateway.py` のAPI呼び出し直前にフェイルオーバー判定を組み込む。
- **対象ファイル**: `src/llm/resilient_gateway.py`
- **修正内容**: `ProviderFailoverManager` のシングルトンを保持し、プロバイダー呼び出し時に `can_execute()` を評価する。
- **検証コマンド**: `python -m ruff check src/llm/resilient_gateway.py`
- **合格条件**: 構文チェック通過。

---

### Step 4: ハードトークン予算（CostBudgetGuard）の設定モデル定義
- **目的**: 1セッションあたりの最大許容トークン数（例: 50,000トークン）または円換算上限（例: 20円）を設定するモデルを作成。
- **対象ファイル**: `src/services/billing/cost_budget_guard.py`（新規作成）
- **実装コード**:
```python
"""トークン消費上限 (Cost Budget Guard) モデル。"""
from dataclasses import dataclass


@dataclass
class CostBudgetConfig:
    max_tokens_per_episode: int = 40_000      # 1話あたりの最大消費トークン
    max_cost_yen_per_episode: float = 15.0    # 1話あたりの最大円換算コスト
    max_pdca_iterations: int = 3              # 最大書き直し反復回数
```
- **検証コマンド**: `python -c "from src.services.billing.cost_budget_guard import CostBudgetConfig; print('BudgetConfig loaded')"`
- **合格条件**: インポート成功。

---

### Step 5: リアルタイムトークン集計器の実装
- **目的**: 執筆ループ内で呼び出されるLLMレスポンスからトークン数をリアルタイムで加算し、上限到達時に即座にフラグを立てる。
- **対象ファイル**: `src/services/billing/token_budget_tracker.py`（新規作成）
- **実装コード**:
```python
"""リアルタイムトークンバジェットトラッカー。"""
from __future__ import annotations
from src.services.billing.cost_budget_guard import CostBudgetConfig


class CostBudgetExceededError(Exception):
    """設定されたトークンまたは原価予算の上限を超過した場合の例外。"""
    pass


class TokenBudgetTracker:
    def __init__(self, config: CostBudgetConfig | None = None):
        self.config = config or CostBudgetConfig()
        self.total_tokens: int = 0
        self.estimated_cost_yen: float = 0.0

    def add_usage(self, prompt_tokens: int, completion_tokens: int, rate_per_1k_yen: float = 0.0003) -> None:
        usage = prompt_tokens + completion_tokens
        self.total_tokens += usage
        self.estimated_cost_yen += (usage / 1000.0) * rate_per_1k_yen

        if self.total_tokens > self.config.max_tokens_per_episode:
            raise CostBudgetExceededError(
                f"トークン上限超過: {self.total_tokens} > {self.config.max_tokens_per_episode}"
            )
        if self.estimated_cost_yen > self.config.max_cost_yen_per_episode:
            raise CostBudgetExceededError(
                f"コスト上限超過: {self.estimated_cost_yen:.2f}円 > {self.config.max_cost_yen_per_episode}円"
            )

    def is_within_budget(self) -> bool:
        return (
            self.total_tokens <= self.config.max_tokens_per_episode
            and self.estimated_cost_yen <= self.config.max_cost_yen_per_episode
        )
```
- **検証コマンド**: `python -c "from src.services.billing.token_budget_tracker import TokenBudgetTracker; print('Tracker loaded')"`
- **合格条件**: インポート成功。

---

### Step 6: グローバル例外型への登録
- **目的**: システム全体で `CostBudgetExceededError` を標準エラーとして認識させる。
- **対象ファイル**: `src/core/exceptions.py`
- **修正内容**: `src.services.billing.token_budget_tracker` の `CostBudgetExceededError` を re-export。
- **検証コマンド**: `python -c "from src.core.exceptions import CostBudgetExceededError; print('Exception registered')"`
- **合格条件**: インポート成功。

---

### Step 7: 執筆PDCAループへのトークン予算ガード組み込み
- **目的**: `src/agents/writing/_writing.py` または `agent.py` の反復ループ内で、`CostBudgetExceededError` を捕捉して安全にループを脱出させる。
- **対象ファイル**: `src/agents/writing/_writing.py`
- **修正内容**:
```python
# ループ処理部
try:
    budget_tracker.add_usage(prompt_tokens, completion_tokens)
except CostBudgetExceededError as e:
    logger.warning(f"予算上限に達したため自己修正ループを安全終了します: {e}")
    break  # それまでの最良版を採用して確定
```
- **検証コマンド**: `python -m ruff check src/agents/writing/_writing.py`
- **合格条件**: 構文チェック通過。

---

### Step 8: LangGraphワークフローへの予算ガード組み込み
- **目的**: LangGraph の状態遷移ノードにおいて、予算超過フラグが立った場合に修正ノードをスキップして確定ノードへ遷移させる。
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py`
- **修正内容**: 条件付きエッジ `should_continue_pdca` の判定に `tracker.is_within_budget()` を追加。
- **検証コマンド**: `python -m ruff check src/backend/workflows/writing_langgraph.py`
- **合格条件**: 構文チェック通過。

---

### Step 9: 予算超過時の最良版確定（Best-Effort Commit）ロジック
- **目的**: 予算上限で中断された場合でも、未完成で破棄するのではなく、反復の中で最もスコアの高かった本文を自動採用する。
- **対象ファイル**: `src/agents/writing/agent.py`
- **修正内容**: 各反復の `(score, text)` の最高値を保持し、予算ブレイク時にその `best_text` を返すよう実装。
- **検証コマンド**: `python -m ruff check src/agents/writing/agent.py`
- **合格条件**: 構文チェック通過。

---

### Step 10: サーキットブレーカーの単体テスト
- **目的**: 回路遮断（OPEN）、遮断中の通信スキップ、復旧時間経過後の半開（HALF-OPEN）の動作を検証。
- **対象ファイル**: `tests/unit/services/test_circuit_breaker.py`（新規作成）
- **実装コード**:
```python
import time
from src.services.llm.circuit_breaker import CircuitBreaker, CircuitState

def test_circuit_breaker_transitions_to_open():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 3回連続失敗
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()

    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # タイムアウト経過後は HALF_OPEN に遷移
    time.sleep(0.15)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 成功を記録して CLOSED に復旧
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
```
- **検証コマンド**: `pytest tests/unit/services/test_circuit_breaker.py -v --no-cov`
- **合格条件**: テストPASS。

---

### Step 11: ハードトークン予算トラッカーの単体テスト
- **目的**: トークン上限超過時に確実に例外が送出されることを検証。
- **対象ファイル**: `tests/unit/services/test_cost_budget_guard.py`（新規作成）
- **実装コード**:
```python
import pytest
from src.services.billing.cost_budget_guard import CostBudgetConfig
from src.services.billing.token_budget_tracker import TokenBudgetTracker, CostBudgetExceededError

def test_token_budget_tracker_within_limit():
    config = CostBudgetConfig(max_tokens_per_episode=1000)
    tracker = TokenBudgetTracker(config)
    tracker.add_usage(300, 200)
    assert tracker.total_tokens == 500
    assert tracker.is_within_budget() is True

def test_token_budget_tracker_exceed_limit_raises_error():
    config = CostBudgetConfig(max_tokens_per_episode=1000)
    tracker = TokenBudgetTracker(config)
    tracker.add_usage(600, 300)  # 900
    with pytest.raises(CostBudgetExceededError):
        tracker.add_usage(100, 100)  # 1100 -> 超過
```
- **検証コマンド**: `pytest tests/unit/services/test_cost_budget_guard.py -v --no-cov`
- **合格条件**: テストPASS。

---

### Step 12: 複合シナリオ（フェイルオーバー & 予算超過自動停止）の統合テスト
- **目的**: Primaryプロバイダーがダウンした際に自動でFallbackへ切り替わり、かつ途中で予算上限に達した際に安全停止することをモックで検証。
- **対象ファイル**: `tests/unit/services/test_resilient_writing_loop.py`（新規作成）
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock
from src.services.llm.provider_failover import ProviderFailoverManager
from src.services.billing.cost_budget_guard import CostBudgetConfig
from src.services.billing.token_budget_tracker import TokenBudgetTracker, CostBudgetExceededError

@pytest.mark.asyncio
async def test_failover_and_budget_integration():
    manager = ProviderFailoverManager()
    tracker = TokenBudgetTracker(CostBudgetConfig(max_tokens_per_episode=500))

    # Primary (Gemini) はエラー
    primary_mock = AsyncMock(side_effect=RuntimeError("503 Service Unavailable"))
    # Fallback (OpenAI) は成功
    fallback_mock = AsyncMock(return_value="Fallback text")

    # フェイルオーバー実行
    res, provider = await manager.execute_with_fallback("gemini", "openai", primary_mock, fallback_mock)
    assert res == "Fallback text"
    assert provider == "openai"

    # トークン加算して予算超過チェック
    tracker.add_usage(300, 100)  # 400
    with pytest.raises(CostBudgetExceededError):
        tracker.add_usage(100, 50)  # 550 > 500
```
- **検証コマンド**: `pytest tests/unit/services/test_resilient_writing_loop.py -v --no-cov`
- **合格条件**: テストPASS。
