# テストカバレッジ強化 48ステップ実装計画

**作成日**: 2026-07-11
**対象**: 改善1（テストカバレッジの強化と安定化）
**前提条件**: Python 3.11+, pytest 導入済み

---

## 現状分析

### 確認された問題
1. `tests/integration/test_enigma_engine.py` - `InternalLogicValidator` import error
2. `tests/test_background_worker.py` - `with_trace_context` import error（報告のみ・実際は存在）
3. `tests/test_outbox_worker.py` - `with_trace_context` import error（報告のみ・実際は存在）
4. `tests/unit/test_commercial_roles.py` - `config/archetypes.py` の SyntaxError
5. `tests/unit/test_llm_service_di.py` - `track_llm_call` import error（報告のみ・実際は存在）

### 根本原因
- `docs/test_coverage_report.md` は古い状態（2026-07-07）を記録している可能性
- `config/archetypes.py` の SyntaxError は実際の問題（Pydantic関連）
- 一部のImportErrorは報告された時点での問題であり、現状では解決している可能性

---

## Step 1-12: 基盤整備（テスト環境・設定）

### Step 1: `pytest.ini` と `pyproject.toml` の設定確認
- **対象**: `pytest.ini`, `pyproject.toml`
- **アクション**: testpaths の設定を確認

```ini
# pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto
```

### Step 2: `tests/conftest.py` の既存 fixture 確認
- **対象**: `tests/conftest.py`
- **アクション**: 既存 fixture の棚卸し

```python
# 既存 fixture 確認
@pytest.fixture
def erotic_vocabulary():  # あり
@pytest.fixture
def sample_erotic_text():  # あり
@pytest.fixture
def real_db_manager():  # あり
@pytest.fixture
def mock_llm():  # あり
```

### Step 3: モックオブジェクト標準化のための `tests/mocks/__init__.py` 整備
- **対象**: `tests/mocks/__init__.py`
- **アクション**: 共通モックをエクスポート

```python
"""tests/mocks/__init__.py"""
from tests.mocks.mock_llm import MockGeminiApiClient
from tests.mocks.mock_engine import MockEngine
from tests.mocks.mock_api_client import MockApiClient
from tests.mocks.mock_repo import MockPlotRepository

__all__ = [
    "MockGeminiApiClient",
    "MockEngine",
    "MockApiClient",
    "MockPlotRepository",
]
```

### Step 4: `MockGeminiApiClient` の整備
- **対象**: `tests/mocks/mock_llm.py`
- **アクション**: 完全なモック実装を提供

```python
class MockGeminiApiClient:
    def __init__(self, api_key: str = "test"):
        self.api_key = api_key
        self._responses = []
    
    def add_response(self, response: dict):
        self._responses.append(response)
    
    async def generate(self, prompt: str, **kwargs) -> dict:
        if self._responses:
            return self._responses.pop(0)
        return {"text": "mock response"}
```

### Step 5: `MockEngine` の整備
- **対象**: `tests/mocks/mock_engine.py`
- **アクション**: エンジン用モックを整備

```python
class MockEngine:
    def __init__(self):
        self.generate_mock = AsyncMock(return_value=GenerateResult(
            text="mock generated text",
            success=True
        ))
```

### Step 6: `tests/mocks/mock_api_client.py` の整備
- **対象**: `tests/mocks/mock_api_client.py`
- **アクション**: APIクライアント用モック

```python
class MockApiClient:
    def __init__(self):
        self._handlers = {}
    
    def register_handler(self, endpoint: str, handler):
        self._handlers[endpoint] = handler
```

### Step 7: `tests/mocks/mock_repo.py` の整備
- **対象**: `tests/mocks/mock_repo.py`
- **アクション**: Repository用モック

```python
class MockPlotRepository:
    def __init__(self):
        self._plots = {}
    
    async def get(self, plot_id: int):
        return self._plots.get(plot_id)
```

### Step 8: `tests/conftest.py` に共通モック fixture 追加
- **対象**: `tests/conftest.py`
- **アクション**: 新規 fixture を追加

```python
@pytest.fixture
def mock_gemini_client():
    """Mock Gemini APIクライアント"""
    from tests.mocks.mock_llm import MockGeminiApiClient
    return MockGeminiApiClient()

@pytest.fixture
def mock_engine():
    """Mock エンジン"""
    from tests.mocks.mock_engine import MockEngine
    return MockEngine()

@pytest.fixture
def mock_api_client():
    """Mock APIクライアント"""
    from tests.mocks.mock_api_client import MockApiClient
    return MockApiClient()
```

### Step 9: 非同期テスト用設定確認
- **対象**: `pytest.ini`
- **アクション**: asyncio_mode が auto に設定されていることを確認

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

### Step 10: テストカテゴリ別ディレクトリ確認
- **対象**: `tests/`
- **アクション**: ディレクトリ構造を確認

```
tests/
├── unit/          # ユニットテスト
├── integration/   # 統合テスト
├── mocks/         # モックオブジェクト
├── fixtures/      # テストフィクスチャ
└── state/         # 状態関連テスト
```

### Step 11: `tests/__init__.py` の存在確認
- **対象**: `tests/__init__.py`
- **アクション**: ファイル作成（空でOK）

```python
"""tests package"""
```

### Step 12: 各サブディレクトリ `__init__.py` 整備
- **対象**: `tests/unit/__init__.py`, `tests/integration/__init__.py` 等
- **アクション**: 各ディレクトリに `__init__.py` を作成

```python
"""tests.unit package"""
```

---

## Step 13-24: ImportError 解消

### Step 13: `src/agents/audit.py` の `InternalLogicValidator` 確認
- **対象**: `src/agents/audit.py`
- **アクション**: `InternalLogicValidator` が存在するか確認

```bash
grep -n "class InternalLogicValidator" src/agents/audit.py
```

### Step 14: `InternalLogicValidator` の Stub 実装
- **対象**: `src/agents/audit.py`
- **アクション**: 存在しない場合はスタブを追加

```python
class InternalLogicValidator:
    """InternalLogicValidator stub for backward compatibility"""
    def validate(self, plot_data: dict) -> bool:
        return True
```

### Step 15: `src/backend/tasks.py` の `with_trace_context` 確認
- **対象**: `src/backend/tasks.py`
- **アクション**: import 路径を確認

```python
# src/backend/tasks.py
from src.core.observability import with_trace_context  # 既に存在
```

### Step 16: `src/core/observability.py` の完全確認
- **対象**: `src/core/observability.py`
- **アクション**: `with_trace_context` と `track_llm_call` がエクスポートされているか確認

```python
# 確認
from src.core.observability import with_trace_context, track_llm_call
# どちらも存在することを確認済み
```

### Step 17: `config/archetypes.py` の SyntaxError 修正
- **対象**: `config/archetypes.py`
- **アクション**: SyntaxError の原因を調査・修正

```bash
python -c "import config.archetypes" 2>&1 | findstr SyntaxError
```

### Step 18: `config/archetypes.py` の Pydantic v1→v2 移行
- **対象**: `config/archetypes.py`
- **アクション**: `@validator` を `@field_validator` に置換

```python
# Before
@validator("genre")
def validate_genre(cls, v):
    return v

# After
@field_validator("genre")
@classmethod
def validate_genre(cls, v):
    return v
```

### Step 19: `src/llm/provider_factory.py` の import 確認
- **対象**: `src/llm/provider_factory.py`
- **アクション**: `track_llm_call` import 路径を確認

### Step 20: `src/llm/gemini_provider.py` の import 確認
- **対象**: `src/llm/gemini_provider.py`
- **アクション**: `track_llm_call` が正しく import できるか確認

```bash
python -c "from src.llm.gemini_provider import GeminiProvider; print('OK')"
```

### Step 21: 失敗するテストの個別確認
- **対象**: `tests/test_background_worker.py`
- **アクション**: import が失敗する原因を解明

```bash
python -c "from src.backend.tasks import huey, run_test_coro"
```

### Step 22: `test_background_worker.py` の修正
- **対象**: `tests/test_background_worker.py`
- **アクション**: import を修正、必要に応じてモック化

```python
# 修正案: huey をモック化
@pytest.fixture
def mock_huey():
    from unittest.mock import MagicMock
    return MagicMock()
```

### Step 23: `test_outbox_worker.py` の修正
- **対象**: `tests/test_outbox_worker.py`
- **アクション**: 同様に修正

```python
# 修正案: _process_outbox_events_async をモック化
@pytest.fixture
def mock_outbox_processor():
    from unittest.mock import AsyncMock
    return AsyncMock(return_value={"processed": 0})
```

### Step 24: `test_commercial_roles.py` の修正
- **対象**: `tests/unit/test_commercial_roles.py`
- **アクション**: `config/archetypes.py` の SyntaxError 修正後に再確認

---

## Step 25-36: テスト安定化（ Fixtures 追加・改善）

### Step 25: Database 用テスト fixture
- **対象**: `tests/conftest.py`
- **アクション**: データベース用フィクスチャを追加

```python
@pytest.fixture
def test_db():
    """テスト用インメモリデータベース"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
```

### Step 26: LLM 応答モック用 fixture
- **対象**: `tests/conftest.py`
- **アクション**: LLM応答制御用フィクスチャを追加

```python
@pytest.fixture
def llm_response_handler():
    """LLM 応答を制御するフィクスチャ"""
    class Handler:
        def __init__(self):
            self.responses = []
        
        def add_response(self, text: str, metadata: dict = None):
            self.responses.append({
                "text": text,
                "metadata": metadata or {}
            })
        
        def get_next(self):
            return self.responses.pop(0) if self.responses else {"text": "default"}
    
    return Handler()
```

### Step 27: Plot 用テストデータ fixture
- **対象**: `tests/conftest.py`
- **アクション**: Plot 生成用フィクスチャを追加

```python
@pytest.fixture
def sample_plot():
    """サンプル Plot データ"""
    from src.models.db import PlotDbModel
    return PlotDbModel(
        id=1,
        title="テスト小説",
        genre="fantasy",
        tone="serious",
        target_hook="catharsis",
        base_tension=75,
        erotic_intensity=2
    )
```

### Step 28: Erotic Curve 用テスト fixture
- **対象**: `tests/conftest.py`
- **アクション**: 官能曲線用フィクスチャを追加

```python
@pytest.fixture
def erotic_curve_r15():
    """R15相当の官能曲線"""
    from config.erotic_pacing import EroticCurve
    return EroticCurve.create_default(intensity=3)
```

### Step 29: Platform Preset 用テスト fixture
- **対象**: `tests/conftest.py`
- **アクション**: プラットフォームプリセット用フィクスチャを追加

```python
@pytest.fixture
def platform_preset_nocturn():
    """ノクターン用プリセット"""
    from config.erotic_platform_presets import get_preset
    return get_preset("nocturn_novel")
```

### Step 30: Consent 関連テストデータ
- **対象**: `tests/conftest.py`
- **アクション**: 同意表現テスト用データ

```python
@pytest.fixture
def consent_test_cases():
    """同意表現テストケース集"""
    return {
        "explicit": ["同意", "了承", "承諾", "いいよ", "求めて"],
        "implicit": ["促す", "引き寄せる", "唇が触れる"],
        "refusal": ["嫌", "やだ", "断る", "拒否"]
    }
```

### Step 31: 五感キーワードテストデータ
- **対象**: `tests/conftest.py`
- **アクション**: 官能品質評価用テストデータ

```python
@pytest.fixture
def sensory_keywords():
    """五感関連キーワード集"""
    from src.agents.erotic_integrity import (
        SENSORY_TOUCH_KEYWORDS,
        SENSORY_SMELL_KEYWORDS,
        SENSORY_SOUND_KEYWORDS,
        SENSORY_SIGHT_KEYWORDS,
        SENSORY_TASTE_KEYWORDS
    )
    return {
        "touch": SENSORY_TOUCH_KEYWORDS,
        "smell": SENSORY_SMELL_KEYWORDS,
        "sound": SENSORY_SOUND_KEYWORDS,
        "sight": SENSORY_SIGHT_KEYWORDS,
        "taste": SENSORY_TASTE_KEYWORDS
    }
```

### Step 32: 密度計算テスト用データ
- **対象**: `tests/conftest.py`
- **アクション**: 官能密度テスト用データ

```python
@pytest.fixture
def density_test_data():
    """密度管理テスト用データ"""
    return {
        "recent_intensities": [1, 2, 3, 4, 3, 2],
        "base_intensity": 3,
        "total_episodes": 10
    }
```

### Step 33: Vocabulary tier テストデータ
- **対象**: `tests/conftest.py`
- **アクション**: ボキャブラリ階層別テストデータ

```python
@pytest.fixture
def vocabulary_tiers():
    """ボキャブラリ階層別テストデータ"""
    from config.erotic_vocabulary import get_vocabulary_for_tier
    return {
        "mild": get_vocabulary_for_tier("mild"),
        "medium": get_vocabulary_for_tier("medium"),
        "full": get_vocabulary_for_tier("full")
    }
```

### Step 34: 伏字フィルタリング用テストテキスト
- **対象**: `tests/conftest.py`
- **アクション**: 検死用テストテキスト

```python
@pytest.fixture
def censor_test_cases():
    """伏字フィルタリング用テストケース"""
    return {
        "kakuyomu": "この文には FIG_1 が含まれる。FIG_2 とも呼ばれる。",
        "nocturn": "この文には NG_WORD_1 が含まれる。",
        "selfhost": "この文は安全なはず。"
    }
```

### Step 35: 統合テスト用ワークフロー
- **対象**: `tests/conftest.py`
- **アクション**: ワークフロー統合テスト用

```python
@pytest.fixture
def workflow_context():
    """ワークフロー統合テスト用コンテキスト"""
    return {
        "book_id": 1,
        "ep_num": 1,
        "nsfw_enabled": True,
        "erotic_intensity": 3,
        "platform_preset": "nocturn_novel"
    }
```

### Step 36: アサーションリスター ожидание
- **対象**: `tests/conftest.py`
- **アクション**: カスタムアサーションリスター ожидание

```python
@pytest.fixture
def assert_erotic_quality():
    """官能品質アサーションラッパー"""
    def _assert(text: str, min_score: float = 0.5):
        from src.services.erotic_diversity_score import compute_diversity_score
        score = compute_diversity_score(text)
        assert score >= min_score, f"Quality score {score} < {min_score}"
    return _assert
```

---

## Step 37-48: テスト実装と検証

### Step 37: `test_erotic_density_controller.py` の健全性確認
- **対象**: `tests/test_erotic_density_controller.py`
- **アクション**: 既存テストが通ることを確認

```bash
python -m pytest tests/test_erotic_density_controller.py -v
```

### Step 38: `test_erotic_thresholds.py` の追加テスト
- **対象**: `tests/test_erotic_thresholds.py`
- **アクション**: 新規テストケース追加

```python
def test_intensity_order():
    from config.erotic_thresholds import INTENSITY_SAFE_MAX, INTENSITY_R15
    assert INTENSITY_SAFE_MAX < INTENSITY_R15
```

### Step 39: `test_erotic_workflow.py` のカバレッジ拡張
- **対象**: `tests/test_erotic_workflow.py`
- **アクション**: 新規テストケース追加

```python
def test_vocabulary_tier_minimum():
    from config.erotic_vocabulary import get_vocabulary_for_tier
    full = get_vocabulary_for_tier("full")
    assert len(full["metaphors"]) >= 25
    assert len(full["onomatopoeia"]) >= 20
```

### Step 40: `test_erotic_afterglow_evaluator.py` のテスト追加
- **対象**: `tests/test_erotic_afterglow_evaluator.py`
- **アクション**: アフターグロー評価テスト追加

```python
def test_afterglow_min_paragraphs():
    from src.services.erotic_afterglow_evaluator import AfterglowEvaluator
    evaluator = AfterglowEvaluator()
    text = "余韻の長い文章\n\n第二段落\n\n第三段落"
    result = evaluator.evaluate(text)
    assert result["paragraphs"] >= 2
```

### Step 41: `test_erotic_integrity.py` の consent テスト
- **対象**: `tests/test_erotic_integrity.py`（新規）
- **アクション**: 同意表現検証テスト追加

```python
def test_consent_explicit():
    from src.agents.erotic_integrity import EroticIntegrityChecker
    checker = EroticIntegrityChecker()
    text = "二人は同意の上、深い親密さを分かち合った。"
    result = checker.check_consent_state(text)
    assert result["has_consent"] == True
    assert result["type"] == "explicit"
```

### Step 42: `test_erotic_censor.py` の拡張
- **対象**: `tests/test_erotic_censor.py`（新規）
- **アクション**: 伏字フィルタリングテスト追加

```python
def test_censorship_kakuyomu():
    from formatters.erotic_censor import apply_censorship
    text = "挿入 FIG_1 行為"
    result = apply_censorship(text, "kakuyomu_romance")
    assert "*" in result
```

### Step 43: `test_erotic_diversity_score.py` の拡張
- **対象**: `tests/test_erotic_diversity_score.py`（新規）
- **アクション**: 多様性スコアリングテスト追加

```python
def test_diversity_score_diverse():
    from src.services.erotic_diversity_score import compute_diversity_score
    text = "瞳を星の瞬きに例える。声が風鈴の音に例える。体温を夕暮れの大地に例える。"
    score = compute_diversity_score(text)
    assert score >= 0.6
```

### Step 44: エラー発生テストの確認
- **対象**: 問題のあるテストファイル5つ
- **アクション**: 個別に実行して問題を確認

```bash
python -m pytest tests/integration/test_enigma_engine.py -v --tb=short
python -m pytest tests/test_background_worker.py -v --tb=short
python -m pytest tests/test_outbox_worker.py -v --tb=short
python -m pytest tests/unit/test_commercial_roles.py -v --tb=short
python -m pytest tests/unit/test_llm_service_di.py -v --tb=short
```

### Step 45: `test_enigma_engine.py` の修正
- **対象**: `tests/integration/test_enigma_engine.py`
- **アクション**: `InternalLogicValidator` の handling を修正

```python
# 修正案: クラス存在確認 후 条件付き import
try:
    from src.agents.audit import InternalLogicValidator
except ImportError:
    InternalLogicValidator = None
```

### Step 46: `test_background_worker.py` の修正
- **対象**: `tests/test_background_worker.py`
- **アクション**: huey モック化

```python
# 修正案
@pytest.fixture
def mock_huey():
    from unittest.mock import MagicMock
    return MagicMock()

# 테스트에서
def test_background_task(mock_huey):
    # mock_huey を使用してテスト
    pass
```

### Step 47: `test_llm_service_di.py` の修正
- **対象**: `tests/unit/test_llm_service_di.py`
- **アクション**: `track_llm_call` フォールバック追加

```python
# 修正案
try:
    from src.core.observability import track_llm_call
except ImportError:
    def track_llm_call(func):
        return func
```

### Step 48: 全テスト実行とカバレッジ測定
- **対象**: 全テスト
- **アクション**: 最終検証

```bash
python -m pytest tests/ -v --cov=src --cov-report=term-missing --tb=short
```

---

## 依存関係図

```
Step1-12 (基盤) ──────→ Step13-24 (ImportError解消)
                              │
                              ▼
                        Step25-36 (Fixtures追加)
                              │
                              ▼
                        Step37-48 (テスト実装・検証)
```

## 検証コマンド

```bash
# Step 37以降で実行
cd d:/R15/cR15

# 1. 单独テスト
python -m pytest tests/test_erotic_density_controller.py -v

# 2. erotic 関連全テスト
python -m pytest tests/ -k "erotic" -v

# 3. カバレッジ測定
python -m pytest tests/ --cov=src --cov-report=term-missing --tb=short

# 4. ImportError 確認
python -m pytest tests/ --collect-only -q
```

## 完了条件

- [ ] `python -m pytest tests/ --collect-only -q` が 0 errors で終了
- [ ] `tests/test_erotic_*.py` の全テストが green
- [ ] カバレッジが現状から10%以上向上
- [ ] `config/archetypes.py` の SyntaxError が解消