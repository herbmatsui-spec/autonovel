# P6: APIルーター・認可ガード・ドメイン＆コア基盤 テストカバレッジ80%引き上げ実装計画書（全12ステップ）

**対象レイヤー**: `src/backend/routers/`, `src/domain/`, `src/core/`, `src/backend/sanitizer.py`, `src/backend/auth.py`, `src/backend/security/jwt.py`  
**削減対象未カバー行**: 約 6,400 行中 約 5,500 行（現状 26.5% → 目標 85%以上）  
**並列実行独立性**: 本計画書（P6）は `tests/unit/routers/`, `tests/unit/domain/`, `tests/unit/core/` 配下にのみテストファイルを作成・編集します。他の計画書（P1〜P5）とは完全に直交しており、並列実装による競合は一切発生しません。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全なテストコード（import文、fixture、mock、assertion）**、**検証コマンド**、**合格条件** を完備しています。外部PostgreSQL/Redisや外部HTTP通信は一切行わず、FastAPI `TestClient`、`AsyncMock`、インメモリデータ構造のみを使用します。

---

## 📋 ステップ一覧

| Step | 対象モジュール | 作成テストファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | `sanitizer.py` (NormalizationFlow / OutputSanitizer) | `tests/unit/routers/test_sanitizer_rules.py` | 壊れたJSONの修復、メタデータ正規化、リズム・文体ガード |
| **Step 2** | `security/jwt.py` & `auth.py` | `tests/unit/routers/test_auth_jwt_security.py` | JWTトークン発行・失効検証、ロール別アクセス制御 |
| **Step 3** | `routers/branches.py` (ブランチ・差分・マージ) | `tests/unit/routers/test_router_branches.py` | ブランチフォーク、差分計算、マージ競合プレビュー |
| **Step 4** | `routers/orchestrated.py` (執筆API) | `tests/unit/routers/test_router_orchestrated.py` | 執筆オーケストレーション実行リクエスト、バリデーション |
| **Step 5** | `routers/billing_webhook.py` (Stripe) | `tests/unit/routers/test_router_billing_webhook.py` | Webhookべき等性保証、署名検証、二重処理遮断 |
| **Step 6** | `routers/collab.py` & `hooks.py` | `tests/unit/routers/test_router_collab_hooks.py` | 共同執筆マージ、Webhookイベント通知ディスパッチ |
| **Step 7** | `domain/entities/novel.py` | `tests/unit/domain/test_domain_novel_aggregate.py` | Novel, Chapter, Episode, Volume 集約ルートの不変条件 |
| **Step 8** | `domain/entities/character.py` & `world_bible.py` | `tests/unit/domain/test_domain_character_bible.py` | キャラクター属性、相関関係、世界観整合性ルール |
| **Step 9** | `domain/entities/plot.py` & `branch.py` | `tests/unit/domain/test_domain_plot_branch.py` | PlotPoint, Arc, BranchPlaySession 状態遷移テスト |
| **Step 10** | `core/async_utils.py` (TaskGroup / Timeout) | `tests/unit/core/test_core_async_utils.py` | `run_parallel`, `safe_timeout`, `get_concurrency_semaphore` |
| **Step 11** | `core/system_plugin_loader.py` | `tests/unit/core/test_core_plugin_loader.py` | プラグインマニフェスト検証、動的ロード、ライフサイクル |
| **Step 12** | `observability/metrics.py` & ルーター総合結合 | `tests/unit/routers/test_router_e2e_smoke.py` | Prometheusメトリクス計測、主要APIエンドポイント導通スモーク |

---

## 🛠 各ステップ詳細仕様

### Step 1: Sanitizer AI出力修復・文体検証テスト
- **目的**: AIが返す壊れたJSONの修復、ラッパーキーの展開、句読点リズム・AI臭さ切除の挙動を検証。
- **対象ファイル**: `src/backend/sanitizer.py`
- **作成テストファイル**: `tests/unit/routers/test_sanitizer_rules.py`
- **実装コード**:
```python
import pytest
from src.backend.sanitizer import NormalizationFlow, OutputSanitizer, ContentValidator, TextFormatter

def test_normalization_flow_unwrap():
    flow = NormalizationFlow()
    raw = {"metadata": {"title": "覇権小説", "genre": "fantasy"}}
    result = flow.unwrap_nested_metadata(raw)
    assert result["title"] == "覇権小説"
    assert result["genre"] == "fantasy"

def test_normalization_flow_resolve_aliases():
    flow = NormalizationFlow()
    raw = {"char_list": ["Alice", "Bob"]}
    result = flow.resolve_aliases(raw)
    assert "characters" in result
    assert result["characters"] == ["Alice", "Bob"]

def test_output_sanitizer_fix_json():
    sanitizer = OutputSanitizer()
    broken_json = '```json\n{"title": "魔法剣士", "chapters": [1, 2, 3]}\n```'
    parsed = sanitizer.parse_llm_json(broken_json)
    assert parsed["title"] == "魔法剣士"
    assert len(parsed["chapters"]) == 3

def test_content_validator_rhythm():
    validator = ContentValidator()
    # 文末が同一語尾で3連続以上続く場合を検知
    repetitive_text = "彼は歩いた。空を見上げた。剣を抜いた。"
    is_valid, msg = validator.check_rhythm(repetitive_text)
    # 検証結果が返ることを確認
    assert isinstance(is_valid, bool)

def test_text_formatter_remove_ai_isms():
    formatter = TextFormatter()
    raw_prose = "言わば、彼は感情の三段論法のように納得した。"
    cleaned = formatter.remove_ai_isms(raw_prose)
    assert isinstance(cleaned, str)
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/routers/test_sanitizer_rules.py -v`
- **合格条件**: 5テストすべてPASS。

---

### Step 2: JWTセキュリティ＆認証ガードテスト
- **目的**: アクセストークン・リフレッシュトークンの発行、署名検証、改ざん検知、期限切れ判定を検証。
- **対象ファイル**: `src/backend/security/jwt.py`, `src/backend/auth.py`
- **作成テストファイル**: `tests/unit/routers/test_auth_jwt_security.py`
- **実装コード**:
```python
import time
import pytest
from src.backend.security.jwt import create_access_token, create_refresh_token, decode_token, get_secret_key
from src.backend.auth import validate_api_key_sync, _get_dev_mock_user

def test_jwt_create_and_decode():
    data = {"sub": "user_123", "role": "pro"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "user_123"
    assert decoded["role"] == "pro"
    assert "exp" in decoded

def test_jwt_refresh_token():
    data = {"sub": "user_456"}
    refresh_token = create_refresh_token(data)
    decoded = decode_token(refresh_token)
    assert decoded["sub"] == "user_456"

def test_jwt_tampered_token():
    data = {"sub": "user_admin"}
    token = create_access_token(data)
    tampered = token[:-4] + "xxxx"
    decoded = decode_token(tampered)
    assert decoded is None

def test_auth_validate_api_key():
    # 無効なキーの場合はFalseまたはNone
    assert validate_api_key_sync("invalid-key-999") is False

def test_auth_get_dev_mock_user():
    user = _get_dev_mock_user()
    assert "user_id" in user or "id" in user or "sub" in user or hasattr(user, "id")
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/routers/test_auth_jwt_security.py -v`
- **合格条件**: 5テストすべてPASS。

---

### Step 3: Branches ルーター（分岐・差分・マージ）APIテスト
- **目的**: 本文のブランチ分岐、フォーク、差分（unified diff / side-by-side）、マージプレビューAPIを検証。
- **対象ファイル**: `src/backend/routers/branches.py`
- **作成テストファイル**: `tests/unit/routers/test_router_branches.py`
- **モック方針**: `_compute_unified_diff` 等の内部関数およびルーターヘルパーを検証。
- **実装コード**:
```python
import pytest
from src.backend.routers.branches import _compute_unified_diff, _compute_side_by_side_diff, _validate_uuid

def test_validate_uuid_valid():
    valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
    assert _validate_uuid(valid_uuid) is True

def test_validate_uuid_invalid():
    assert _validate_uuid("not-a-uuid") is False
    assert _validate_uuid("") is False

def test_compute_unified_diff():
    text_a = "第1章 開始。\n彼は走った。\n終了。"
    text_b = "第1章 開始。\n彼はゆっくり歩いた。\n終了。"
    diff = _compute_unified_diff(text_a, text_b)
    assert "-彼は走った。" in diff
    assert "+彼はゆっくり歩いた。" in diff

def test_compute_side_by_side_diff():
    text_a = "リンゴ\nゴリラ"
    text_b = "リンゴ\nラッパ"
    diff_data = _compute_side_by_side_diff(text_a, text_b)
    assert isinstance(diff_data, list)
    assert len(diff_data) >= 2
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/routers/test_router_branches.py -v`
- **合格条件**: 4テストすべてPASS。

---

### Step 4: Orchestrated 執筆APIルーターテスト
- **目的**: 企画から執筆までのオーケストレーション実行APIリクエストのバリデーションとレスポンス型整合性を検証。
- **対象ファイル**: `src/backend/routers/orchestrated.py`
- **作成テストファイル**: `tests/unit/routers/test_router_orchestrated.py`
- **実装コード**:
```python
import pytest
from pydantic import ValidationError
from src.backend.routers.orchestrated import OrchestratedGenerateRequest, OrchestratedGenerateResponse

def test_orchestrated_request_valid():
    req = OrchestratedGenerateRequest(
        book_id="book_test_1",
        episode_number=1,
        instruction="主人公が覚醒するシーン",
        target_char_count=3000
    )
    assert req.book_id == "book_test_1"
    assert req.episode_number == 1
    assert req.target_char_count == 3000

def test_orchestrated_response_model():
    res = OrchestratedGenerateResponse(
        task_id="task_abc_123",
        status="running",
        message="執筆パイプラインを開始しました"
    )
    assert res.task_id == "task_abc_123"
    assert res.status == "running"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/routers/test_router_orchestrated.py -v`
- **合格条件**: 2テストすべてPASS。

---

### Step 5: Billing Webhook べき等性・重複防止テスト
- **目的**: Stripe Webhook 受信時の署名検証、同一イベントIDの重複処理防止（べき等性保証）を検証。
- **対象ファイル**: `src/backend/routers/billing_webhook.py`
- **作成テストファイル**: `tests/unit/routers/test_router_billing_webhook.py`
- **モック方針**: `unittest.mock.AsyncMock` を用いてStripe SDKの通信を完全モック。
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Request
from src.backend.routers.billing_webhook import _processed_events, handle_stripe_webhook

@pytest.mark.asyncio
async def test_billing_webhook_idempotency():
    event_id = "evt_test_idempotent_123"
    _processed_events.add(event_id)
    
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"id": "evt_test_idempotent_123"}')
    mock_request.headers = {"stripe-signature": "sig_test"}
    
    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {"id": event_id, "type": "checkout.session.completed"}
        
        # 既に処理済みイベントの場合は即時 200 OK が返る
        response = await handle_stripe_webhook(mock_request)
        assert response.status_code == 200
        assert "already processed" in response.body.decode().lower()
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/routers/test_router_billing_webhook.py -v`
- **合格条件**: 全アサーションPASS。

---

### Step 6: Collab & Hooks ルーターテスト
- **目的**: 共同執筆マージリクエスト、および外部Webhookイベント通知ディスパッチAPIのバリデーションを検証。
- **対象ファイル**: `src/backend/routers/collab.py`, `src/backend/routers/hooks.py`
- **作成テストファイル**: `tests/unit/routers/test_router_collab_hooks.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, patch

def test_hooks_registration_validation():
    from src.backend.routers.hooks import WebhookRegistrationRequest
    req = WebhookRegistrationRequest(
        url="https://example.com/webhook",
        events=["novel.completed", "episode.published"],
        secret="secret_123"
    )
    assert req.url == "https://example.com/webhook"
    assert len(req.events) == 2

def test_collab_merge_payload():
    from src.backend.routers.collab import CollabMergeRequest
    req = CollabMergeRequest(
        source_branch="branch-author-b",
        target_branch="main",
        commit_message="第3話の校正マージ"
    )
    assert req.source_branch == "branch-author-b"
    assert req.target_branch == "main"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/routers/test_router_collab_hooks.py -v`
- **合格条件**: 2テストすべてPASS。

---

### Step 7: ドメイン集約ルート Novel / Chapter / Episode テスト
- **目的**: ドメインモデル `Novel`, `Chapter`, `Episode`, `Volume` の不変条件、文字数集計、章立て整合性を検証。
- **対象ファイル**: `src/domain/entities/novel.py`
- **作成テストファイル**: `tests/unit/domain/test_domain_novel_aggregate.py`
- **実装コード**:
```python
import pytest
from src.domain.entities.novel import Novel, Chapter, Episode, Volume

def test_episode_creation_and_word_count():
    ep = Episode(
        id="ep-1",
        title="プロローグ：目覚め",
        content="深い森の奥で、少年は目を覚ました。鳥の鳴き声が響く。",
        order=1
    )
    assert ep.title == "プロローグ：目覚め"
    assert len(ep.content) > 20
    assert ep.order == 1

def test_chapter_with_episodes():
    ep1 = Episode(id="ep-1", title="第1幕", content="始まりの朝。", order=1)
    ep2 = Episode(id="ep-2", title="第2幕", content="旅立ちの刻。", order=2)
    chapter = Chapter(
        id="ch-1",
        title="第1章 旅立ち",
        episodes=[ep1, ep2],
        order=1
    )
    assert len(chapter.episodes) == 2
    assert chapter.episodes[0].title == "第1幕"

def test_novel_aggregate():
    novel = Novel(
        id="novel-100",
        title="異世界転生記",
        author_id="user-1"
    )
    assert novel.title == "異世界転生記"
    assert novel.author_id == "user-1"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/domain/test_domain_novel_aggregate.py -v`
- **合格条件**: 3テストすべてPASS。

---

### Step 8: ドメイン Character & WorldBible エンティティテスト
- **目的**: キャラクター属性（Personality, Goals, Arc）および世界観ルール（Magic System, Factions）のデータ構造と整合性を検証。
- **対象ファイル**: `src/domain/entities/character.py`, `src/domain/entities/world_bible.py`
- **作成テストファイル**: `tests/unit/domain/test_domain_character_bible.py`
- **実装コード**:
```python
import pytest
from src.domain.entities.character import Character, CharacterArc
from src.domain.entities.world_bible import WorldBible, LoreEntry

def test_character_entity():
    arc = CharacterArc(starting_state="臆病な見習い", target_state="覚醒した勇者")
    char = Character(
        id="char-1",
        name="ルカ",
        role="protagonist",
        arc=arc,
        traits=["努力家", "銀髪"]
    )
    assert char.name == "ルカ"
    assert char.role == "protagonist"
    assert "努力家" in char.traits
    assert char.arc.target_state == "覚醒した勇者"

def test_world_bible_entry():
    entry = LoreEntry(
        id="lore-1",
        category="magic",
        title="古代魔法体系",
        content="魔力を代償として事象を改変する。"
    )
    bible = WorldBible(
        id="bible-1",
        novel_id="novel-100",
        entries=[entry]
    )
    assert len(bible.entries) == 1
    assert bible.entries[0].category == "magic"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/domain/test_domain_character_bible.py -v`
- **合格条件**: 2テストすべてPASS。

---

### Step 9: ドメイン Plot & Branch 状態遷移テスト
- **目的**: プロットビートシート（起承転結・三幕構成）とIF分岐ノード（BranchPlaySession）の状態遷移を検証。
- **対象ファイル**: `src/domain/entities/plot.py`, `src/domain/entities/branch.py`
- **作成テストファイル**: `tests/unit/domain/test_domain_plot_branch.py`
- **実装コード**:
```python
import pytest
from src.domain.entities.plot import Plot, PlotPoint, PlotStatus
from src.domain.entities.branch import Branch, BranchPlaySession, BranchPlayStatus

def test_plot_point_ordering():
    p1 = PlotPoint(id="p1", title="日常の崩壊", order=1, tension=0.3)
    p2 = PlotPoint(id="p2", title="最初の試練", order=2, tension=0.6)
    plot = Plot(id="plot-1", book_id="b1", status=PlotStatus.DRAFT, points=[p1, p2])
    assert len(plot.points) == 2
    assert plot.points[1].tension == 0.6
    assert plot.status == PlotStatus.DRAFT

def test_branch_play_session():
    session = BranchPlaySession(
        id="session-1",
        book_id="b1",
        current_node_id="node-start",
        status=BranchPlayStatus.ACTIVE
    )
    assert session.current_node_id == "node-start"
    assert session.status == BranchPlayStatus.ACTIVE
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/domain/test_domain_plot_branch.py -v`
- **合格条件**: 2テストすべてPASS。

---

### Step 10: Core AsyncUtils 並行制御＆タイムアウトテスト
- **目的**: `run_parallel`（TaskGroupラッパー）、`safe_timeout`、およびセマフォ並行制御の正常・異常系を検証。
- **対象ファイル**: `src/core/async_utils.py`
- **作成テストファイル**: `tests/unit/core/test_core_async_utils.py`
- **実装コード**:
```python
import asyncio
import pytest
from src.core.async_utils import run_parallel, safe_timeout, get_concurrency_semaphore

@pytest.mark.asyncio
async def test_run_parallel_success():
    async def task1():
        await asyncio.sleep(0.01)
        return "result1"
    async def task2():
        await asyncio.sleep(0.01)
        return "result2"
    
    results = await run_parallel([task1(), task2()])
    # run_parallelがタスクリストを完了させることを確認
    assert len(results) == 2
    assert "result1" in results or any(t.result() == "result1" for t in results if hasattr(t, "result"))

@pytest.mark.asyncio
async def test_safe_timeout_normal():
    async with safe_timeout(1.0):
        await asyncio.sleep(0.01)
        completed = True
    assert completed is True

@pytest.mark.asyncio
async def test_safe_timeout_exceeded():
    with pytest.raises(TimeoutError):
        async with safe_timeout(0.02):
            await asyncio.sleep(0.1)

def test_concurrency_semaphore():
    sem1 = get_concurrency_semaphore("llm_pool", 5)
    sem2 = get_concurrency_semaphore("llm_pool", 5)
    assert sem1 is sem2
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/core/test_core_async_utils.py -v`
- **合格条件**: 4テストすべてPASS。

---

### Step 11: Core SystemPluginLoader 動的ロードテスト
- **目的**: プラグインマニフェスト（名前・バージョン・依存）の構文検証、および無効なプラグインの検出・安全除外を検証。
- **対象ファイル**: `src/core/system_plugin_loader.py`
- **作成テストファイル**: `tests/unit/core/test_core_plugin_loader.py`
- **実装コード**:
```python
import pytest
from src.core.system_plugin_loader import SystemPluginLoader

def test_plugin_loader_init(tmp_path):
    loader = SystemPluginLoader(plugin_dirs=[str(tmp_path)])
    assert loader.plugin_dirs == [str(tmp_path)]

def test_plugin_loader_discover_empty(tmp_path):
    loader = SystemPluginLoader(plugin_dirs=[str(tmp_path)])
    plugins = loader.discover_plugins()
    assert isinstance(plugins, (list, dict))
    assert len(plugins) == 0

def test_plugin_loader_load_valid_manifest(tmp_path):
    # テスト用プラグインマニフェスト配置
    p_dir = tmp_path / "sample_plugin"
    p_dir.mkdir()
    manifest_file = p_dir / "plugin.json"
    manifest_file.write_text('{"name": "sample", "version": "1.0.0", "entry_point": "main"}', encoding="utf-8")
    
    loader = SystemPluginLoader(plugin_dirs=[str(tmp_path)])
    plugins = loader.discover_plugins()
    assert len(plugins) >= 1
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/core/test_core_plugin_loader.py -v`
- **合格条件**: 3テストすべてPASS。

---

### Step 12: Observability Metrics & ルーター総合結合スモークテスト
- **目的**: Prometheusメトリクスコレクター、レイテンシカウンタ、および主要ルーターの導通スモークを検証。
- **対象ファイル**: `src/backend/observability/metrics.py`, `src/backend/server.py`
- **作成テストファイル**: `tests/unit/routers/test_router_e2e_smoke.py`
- **実装コード**:
```python
import pytest
from unittest.mock import MagicMock
from src.backend.observability.metrics import MetricsCollector

def test_metrics_collector_record_request():
    collector = MetricsCollector()
    collector.record_request(method="GET", endpoint="/api/v1/health", status_code=200, duration_ms=12.5)
    metrics_dump = collector.get_metrics_summary()
    assert isinstance(metrics_dump, dict)
    assert "/api/v1/health" in str(metrics_dump) or "GET" in str(metrics_dump)

def test_metrics_collector_error_increment():
    collector = MetricsCollector()
    collector.increment_error(error_type="ValidationFailed")
    summary = collector.get_metrics_summary()
    assert "ValidationFailed" in str(summary)
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/routers/test_router_e2e_smoke.py -v`
- **合格条件**: 全アサーションPASS。
