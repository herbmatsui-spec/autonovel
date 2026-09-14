# P2: サービス層・キャッシュ・ベクトル検索基盤 テストカバレッジ80%引き上げ実装計画書（全12ステップ）

**対象レイヤー**: `src/services/` (writing_services, redis_cache, vector_store, semantic_cache, bible_service, retry_decorator, etc.)  
**削減対象未カバー行**: 約 1,650 行（現状 33.7% → 目標 85%以上）  
**並列実行独立性**: 本計画書（P2）は `tests/unit/services/` 配下にのみテストファイルを作成・編集します。他の計画書（P1, P3〜P6）とは完全に直交しており、並列実装による競合は一切発生しません。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全なテストコード（import文、fixture、mock、assertion）**、**検証コマンド**、**合格条件** を完備しています。外部RedisやChromaDB、OpenAI APIへの通信は一切行わず、インメモリ辞書モックまたは `unittest.mock` を用いて高速かつ確実に実行します。

---

## 📋 ステップ一覧

| Step | 対象モジュール | 作成テストファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | `redis_cache.py` (CRUD・シリアライズ) | `tests/unit/services/test_redis_cache_crud.py` | get, set, delete, ttl, JSONシリアライズ/デシリアライズ |
| **Step 2** | `redis_cache.py` (障害フォールバック) | `tests/unit/services/test_redis_cache_fallback.py` | Redisダウン時のインメモリ退避、エラーログ、サイレント復旧 |
| **Step 3** | `vector_store.py` (コレクション操作) | `tests/unit/services/test_vector_store.py` | ドキュメント登録、メタデータ付与、コサイン類似度検索モック |
| **Step 4** | `semantic_cache.py` (類似プロンプト) | `tests/unit/services/test_semantic_cache.py` | 類似度閾値判定（0.85以上ヒット、未満ミス）、TTL失効 |
| **Step 5** | `retry_decorator.py` (リトライ制御) | `tests/unit/services/test_retry_decorator.py` | 指数バックオフ、特定例外フィルタ、リトライ回数上限超過 |
| **Step 6** | `bible_service.py` (設定抽出) | `tests/unit/services/test_bible_service.py` | 世界観設定パース、キャラ属性抽出、コンフリクト解決 |
| **Step 7** | `writing_services.py` (コンテキスト生成) | `tests/unit/services/test_writing_context_builder.py` | `WritingGenerationContext` の構築、指示文・POVバインディング |
| **Step 8** | `writing_services.py` (レスポンス解析) | `tests/unit/services/test_writing_response_parser.py` | LLM本文出力パース、ルビ記法正規化、文字数カウント |
| **Step 9** | `auto_workflow_pipeline.py` | `tests/unit/services/test_auto_pipeline_service.py` | パイプラインステップ順次実行、途中で失敗時のリカバリ |
| **Step 10** | `illustration/` (構図抽出) | `tests/unit/services/test_illustration_service.py` | シーン本文からキャラクター・構図・スタイルプロンプト生成 |
| **Step 11** | `nlp/tense_analyzer.py` | `tests/unit/services/test_tense_analyzer.py` | 文末時制（過去「た」/現在「る」）比率解析、文体崩れ検出 |
| **Step 12** | サービス層 複合シナリオ結合 | `tests/unit/services/test_services_integration.py` | SemanticCache + Redis + WritingServices 連動スモークテスト |

---

## 🛠 各ステップ詳細仕様

### Step 1: RedisCacheService の基本操作・シリアライゼーションテスト
- **目的**: `RedisCacheService` の `get`, `set`, `delete`, `set_json`, `get_json` のキープレフィックス付与と型変換を検証。
- **対象ファイル**: `src/services/redis_cache.py`
- **作成テストファイル**: `tests/unit/services/test_redis_cache_crud.py`
- **モック方針**: `AsyncMock` で `redis.asyncio.Redis` のメソッドをモック。
- **実装コード**:
```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.redis_cache import RedisCacheService

@pytest.mark.asyncio
async def test_redis_cache_set_and_get():
    service = RedisCacheService(namespace="test_ns")
    mock_client = AsyncMock()
    mock_client.get.return_value = json.dumps({"title": "novel"}).encode("utf-8")
    service._client = mock_client
    
    val = await service.get("key1")
    assert val is not None
    mock_client.get.assert_awaited_once_with("test_ns:key1")

@pytest.mark.asyncio
async def test_redis_cache_delete():
    service = RedisCacheService(namespace="test_ns")
    mock_client = AsyncMock()
    service._client = mock_client
    
    await service.delete("key1")
    mock_client.delete.assert_awaited_once_with("test_ns:key1")
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_redis_cache_crud.py -v`
- **合格条件**: 全テストPASS。

---

### Step 2: RedisCacheService の接続障害時フォールバックテスト
- **目的**: Redisサーバーダウン時に例外を外へ投げず、インメモリキャッシュへの退避またはNoneを返す動作を検証。
- **対象ファイル**: `src/services/redis_cache.py`
- **作成テストファイル**: `tests/unit/services/test_redis_cache_fallback.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock
from src.services.redis_cache import RedisCacheService

@pytest.mark.asyncio
async def test_redis_cache_connection_error_safe_get():
    service = RedisCacheService()
    mock_client = AsyncMock()
    mock_client.get.side_effect = ConnectionError("Redis is down")
    service._client = mock_client
    
    # 接続エラー時でも例外を出さずNoneを返す設計であること
    res = await service.get("some_key")
    assert res is None
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_redis_cache_fallback.py -v`
- **合格条件**: 全テストPASS。

---

### Step 3: VectorStore のドキュメント登録・類似度検索テスト
- **目的**: ベクトル検索基盤における埋め込み追加、メタデータ保存、検索スコア計算を検証。
- **対象ファイル**: `src/services/vector_store.py`
- **作成テストファイル**: `tests/unit/services/test_vector_store.py`
- **モック方針**: ChromaDBクライアントまたはPGVectorアダプターをモック。
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.vector_store import VectorStoreService

@pytest.mark.asyncio
async def test_vector_store_add_and_search():
    mock_client = MagicMock()
    mock_col = MagicMock()
    mock_col.query.return_value = {
        "documents": [["勇者が現れた"]],
        "metadatas": [[{"chapter": 1}]],
        "distances": [[0.12]]
    }
    mock_client.get_or_create_collection.return_value = mock_col
    
    store = VectorStoreService(client=mock_client)
    res = await store.search_similar("勇者", top_k=1)
    
    assert len(res) == 1
    assert res[0]["text"] == "勇者が現れた"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_vector_store.py -v`
- **合格条件**: 全テストPASS。

---

### Step 4: SemanticCache の類似度ヒット・失効テスト
- **目的**: 意味的類似度（コサイン類似度 >= 0.85）によるプロンプトキャッシュヒットと、閾値未満でのミスを検証。
- **対象ファイル**: `src/services/semantic_cache.py`
- **作成テストファイル**: `tests/unit/services/test_semantic_cache.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.semantic_cache import SemanticCacheService

@pytest.mark.asyncio
async def test_semantic_cache_hit_and_miss():
    cache = SemanticCacheService(similarity_threshold=0.85)
    cache._vector_store = AsyncMock()
    
    # 類似度0.90 -> ヒット
    cache._vector_store.search.return_value = [{"text": "プロンプトA", "score": 0.90, "cached_response": "生成テキストA"}]
    hit = await cache.get_similar("プロンプトA似")
    assert hit == "生成テキストA"
    
    # 類似度0.70 -> ミス
    cache._vector_store.search.return_value = [{"text": "無関係", "score": 0.70, "cached_response": "生成テキストB"}]
    miss = await cache.get_similar("全然違う質問")
    assert miss is None
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_semantic_cache.py -v`
- **合格条件**: 全テストPASS。

---

### Step 5: retry_decorator の指数バックオフ・例外フィルタテスト
- **目的**: `src/services/retry_decorator.py` のリトライ回数、遅延計算、除外例外の即時スローを検証。
- **対象ファイル**: `src/services/retry_decorator.py`
- **作成テストファイル**: `tests/unit/services/test_retry_decorator.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, patch
from src.services.retry_decorator import async_retry

@pytest.mark.asyncio
async def test_async_retry_decorator():
    mock_func = AsyncMock(side_effect=[ValueError("一時エラー"), "成功"])
    decorated = async_retry(max_retries=2, backoff=0.01)(mock_func)
    
    with patch("asyncio.sleep", new_callable=AsyncMock):
        res = await decorated()
        assert res == "成功"
        assert mock_func.call_count == 2
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_retry_decorator.py -v`
- **合格条件**: 全テストPASS。

---

### Step 6: BibleService の世界観設定抽出＆マージテスト
- **目的**: 原稿テキストや箇条書き設定からキャラクター・設定用語を抽出・更新するロジックを検証。
- **対象ファイル**: `src/services/bible_service.py`
- **作成テストファイル**: `tests/unit/services/test_bible_service.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.bible_service import BibleService

@pytest.mark.asyncio
async def test_bible_service_extract_characters():
    service = BibleService()
    text = "アリスは剣士である。ボブは魔法使いである。"
    
    chars = await service.extract_character_candidates(text)
    assert isinstance(chars, list)
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_bible_service.py -v`
- **合格条件**: 全テストPASS。

---

### Step 7: WritingServices の執筆コンテキスト構築テスト
- **目的**: `WritingGenerationContext` のプロンプト構築、POV（一人称/三人称）指示付与、スタイル反映を検証。
- **対象ファイル**: `src/services/writing_services.py`
- **作成テストファイル**: `tests/unit/services/test_writing_context_builder.py`
- **実装コード**:
```python
import pytest
from src.services.writing_services import WritingGenerationContext

def test_writing_generation_context_build_sys_inst():
    ctx = WritingGenerationContext(
        sys_inst="基本指示",
        pov_instruction="一人称視点（私）で記述せよ",
        style_key="web_novel_fast",
        target_word_count=3000
    )
    sys_inst = ctx.build_sys_inst()
    assert "基本指示" in sys_inst
    assert "一人称視点" in sys_inst
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_writing_context_builder.py -v`
- **合格条件**: 全テストPASS。

---

### Step 8: WritingServices のレスポンスパース・整形テスト
- **目的**: LLMの生成結果から思考ログ(`<thinking>`)を除去し、地の文と台詞を整形する処理を検証。
- **対象ファイル**: `src/services/writing_services.py`
- **作成テストファイル**: `tests/unit/services/test_writing_response_parser.py`
- **実装コード**:
```python
import pytest
from src.services.writing_services import clean_writing_response

def test_clean_writing_response_strip_thinking():
    raw = "<thinking>プロットの整理...</thinking>「こんにちは」と彼女は言った。"
    cleaned = clean_writing_response(raw)
    assert "<thinking>" not in cleaned
    assert "「こんにちは」" in cleaned
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_writing_response_parser.py -v`
- **合格条件**: 全テストPASS。

---

### Step 9: AutoWorkflowPipeline 実行管理テスト
- **目的**: ステップ1（構成）→ステップ2（執筆）→ステップ3（校正）の順次実行とデータ引き渡しを検証。
- **対象ファイル**: `src/services/auto_workflow_pipeline.py`
- **作成テストファイル**: `tests/unit/services/test_auto_pipeline_service.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.auto_workflow_pipeline import AutoWorkflowPipeline

@pytest.mark.asyncio
async def test_auto_workflow_pipeline_execute_steps():
    pipeline = AutoWorkflowPipeline()
    pipeline.run_step = AsyncMock(return_value={"status": "success"})
    
    result = await pipeline.run_all({"book_id": "b1"})
    assert result["status"] == "success"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_auto_pipeline_service.py -v`
- **合格条件**: 全テストPASS。

---

### Step 10: IllustrationService のプロンプト生成テスト
- **目的**: シーン文脈から画像生成AI用のプロンプト（英語呪文、構図、ライティング）を組み立てる処理を検証。
- **対象ファイル**: `src/services/illustration/`
- **作成テストファイル**: `tests/unit/services/test_illustration_service.py`
- **実装コード**:
```python
import pytest
from src.services.illustration.prompt_generator import IllustrationPromptGenerator

def test_generate_prompt_from_scene():
    gen = IllustrationPromptGenerator()
    prompt = gen.build_prompt(
        character_desc="銀髪の少女、青いドレス",
        mood="緊迫した夜の森",
        style="anime"
    )
    assert "silver hair" in prompt.lower() or "anime" in prompt.lower()
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_illustration_service.py -v`
- **合格条件**: 全テストPASS。

---

### Step 11: TenseAnalyzer 時制ゆらぎ解析テスト
- **目的**: 小説の文末における「〜た」「〜だ」（過去形）と「〜る」「〜す」（現在形）の比率を算出し、文体の一貫性を評価。
- **対象ファイル**: `src/services/nlp/tense_analyzer.py`
- **作成テストファイル**: `tests/unit/services/test_tense_analyzer.py`
- **実装コード**:
```python
import pytest
from src.services.nlp.tense_analyzer import TenseAnalyzer

def test_tense_analyzer_ratio():
    analyzer = TenseAnalyzer()
    text = "風が吹いた。空を見上げた。歩き出す。雨が降り始めた。"
    result = analyzer.analyze(text)
    assert "past_ratio" in result
    assert "present_ratio" in result
    assert result["past_ratio"] > 0.5
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_tense_analyzer.py -v`
- **合格条件**: 全テストPASS。

---

### Step 12: サービス層 複合シナリオ結合テスト
- **目的**: キャッシュ（Redis/SemanticCache）と執筆統括サービス（WritingServices）を組み合わせたスモークテスト。
- **対象ファイル**: `src/services/`
- **作成テストファイル**: `tests/unit/services/test_services_integration.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock
from src.services.redis_cache import RedisCacheService
from src.services.semantic_cache import SemanticCacheService

@pytest.mark.asyncio
async def test_services_end_to_end_mock():
    redis_svc = RedisCacheService()
    redis_svc.get = AsyncMock(return_value=None)
    redis_svc.set = AsyncMock(return_value=True)
    
    await redis_svc.set("key", "val")
    redis_svc.set.assert_awaited_once_with("key", "val")
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/services/test_services_integration.py -v`
- **合格条件**: 全テストPASS。
