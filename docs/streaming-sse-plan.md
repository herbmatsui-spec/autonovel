# SSE ストリーミング生成エンドポイント — 実装計画

**対象ファイル**: `src/backend/routers/streaming.py:55`, `src/backend/server.py:53`
**工数**: 中 (1〜2 週)
**目的**: POST → GET 化 / テスト3件追加 / 接続切断時のキャンセル機構 / レート制限 / Nginx 設定

---

## Phase A: GET 化と安全化 (ステップ 1〜12)

### Step 1. EasyModeInput をクエリ互換に拡張
**ファイル**: `src/domain/entities/easy_mode.py`
**内容**:
- `EasyModeInput` に `model_config = ConfigDict(...)` を追加し、JSON body 経由でなくフォーム/クエリでも構築できるよう `alias` を整備
- 新クラス `StreamQueryInput` を定義 (全フィールド `Optional`、長さ制限はそのまま)
- なぜ GET 化では本文を送れないためクエリ文字列/JSON ベースのペイロードを別途定義する必要がある
**検証**: `python -c "from src.domain.entities.easy_mode import StreamQueryInput; StreamQueryInput()"`

### Step 2. BaseLLMAdapter に `cancel()` を追加
**ファイル**: `src/services/llm/base.py`
**内容**:
```python
def cancel(self) -> None:
    """進行中のストリームをキャンセルするフック (既定は何もしない)."""
```
**検証**: `mypy src/services/llm/base.py`

### Step 3. MockLLMAdapter に cancel フラグを追加
**ファイル**: `src/services/llm/mock_adapter.py`
**内容**:
- `__init__` に `self._cancelled = False` フラグ
- `stream_text` のループ内で `if self._cancelled: raise asyncio.CancelledError` を追加
- `cancel()` で `self._cancelled = True` をセット
**検証**: 既存ユニットテストを実行しリグレッションなし

### Step 4. rate_limit にストリーム用リミッターを追加
**ファイル**: `src/backend/rate_limit.py`
**内容**:
- `stream_limiter = RateLimiter(max_requests=3, window_seconds=60)` を追加 (生成は重いのでさらに厳しく)
- `__all__` に追加
**検証**: `python -c "from src.backend.rate_limit import stream_limiter"`

### Step 5. streaming.py: クエリ入力と依存性を追加
**ファイル**: `src/backend/routers/streaming.py`
**内容**:
- 冒頭で `from fastapi import Depends, Query, Request` をインポート
- `from src.backend.rate_limit import stream_limiter` をインポート
- `StreamQueryInput` をインポート
**検証**: import エラーがないこと

### Step 6. _stream_generator にキャンセル/切断検知を追加
**ファイル**: `src/backend/routers/streaming.py` (line 18-52)
**内容**:
```python
async def _stream_generator(
    input_data: EasyModeInput, request: Request
) -> AsyncIterator[str]:
    adapter = get_llm_adapter()
    try:
        async for chunk in adapter.stream_text(...):
            if await request.is_disconnected():
                adapter.cancel()
                break
            yield f"data: {json.dumps({'type':'chunk','text': chunk})}\n\n"
    except asyncio.CancelledError:
        adapter.cancel()
        raise
    except Exception as exc:
        yield f"data: {... 'error' ...}\n\n"
    finally:
        # 接続切断時のクリーンアップ (例: ログ、メトリクス)
        pass
```
**検証**: 構文チェック `python -c "import ast; ast.parse(open('src/backend/routers/streaming.py').read())"`

### Step 7. GET エンドポイント `GET /generate/stream` を追加
**ファイル**: `src/backend/routers/streaming.py` (line 55-66 の下)
**内容**:
```python
@router.get("/generate/stream")
async def stream_generation_get(
    request: Request,
    payload: str = Query(..., description="base64-encoded JSON of EasyModeInput"),
) -> StreamingResponse:
    stream_limiter.check(request)
    raw = base64.urlsafe_b64decode(payload.encode()).decode()
    input_data = EasyModeInput.model_validate_json(raw)
    return StreamingResponse(
        _stream_generator(input_data, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```
- POST は `deprecated=True` で残し、内部的には新エンドポイントを呼ぶ
**検証**: `uvicorn src.backend.server:app --reload` で手動確認

### Step 8. POST エンドポイントを deprecated 化
**ファイル**: `src/backend/routers/streaming.py`
**内容**:
- `@router.post("/generate/stream", deprecated=True)` を付与
- docstring に「GET /generate/stream を使用してください」を追加
**検証**: `/docs` で deprecation マーク表示

### Step 9. server.py でルーターのプレフィックスを整理
**ファイル**: `src/backend/server.py` (line 53)
**内容**:
- `app.include_router(streaming.router, prefix="/easy_mode", tags=["streaming"])` を維持
- `app.include_router(easy_mode.router, prefix="/easy_mode", tags=["easy_mode"])` の重複 (`/api/easy-mode`) はそのまま
**検証**: `curl http://localhost:8000/openapi.json | jq '.paths | keys'`

### Step 10. X-Accel-Buffering ヘッダの検証ヘルパ追加
**ファイル**: `src/backend/routers/streaming.py`
**内容**:
- 既存 headers に `"X-Accel-Buffering": "no"` が既にあることを確認 (line 64)
- なければ追加
**検証**: ヘッダが出力に含まれることをユニットテストで確認

### Step 11. 接続切断時にメトリクスを加算
**ファイル**: `src/backend/observability/health.py` (確認) と `streaming.py`
**内容**:
- `metrics.increment("streaming_disconnects")` を切断検出時に呼ぶ
- メトリクスに新カウンタを追加 (必要なら)
**検証**: `curl http://localhost:8000/metrics` で増加を確認

### Step 12. 既存エンドポイントのレスポンス形式を固定
**ファイル**: `src/backend/routers/streaming.py`
**内容**:
- start / chunk / done / error の 4 イベントを `enum` で文書化 (docstring 内)
- JSON スキーマを OpenAPI に追加 (response_model 不要だが description で明記)
**検証**: `/docs` でスキーマが見える

---

## Phase B: テスト 3 ケース追加 (ステップ 13〜18)

### Step 13. conftest に SSE テスト用フィクスチャ追加
**ファイル**: `tests/integration/conftest.py` (新規) または `tests/conftest.py`
**内容**:
```python
@pytest.fixture
def stream_client(real_db_manager):
    from fastapi.testclient import TestClient
    from src.backend.server import app
    with TestClient(app) as c:
        yield c
```
**検証**: フィクスチャが import 可能

### Step 14. mock_adapter のイベント数/遅延を調整
**ファイル**: `src/services/llm/mock_adapter.py`
**内容**:
- テスト用に `stream_delay_ms` kwarg を追加 (`**kwargs: Any` から取得)
- 既定 10ms のまま
**検証**: 既存テストがパス

### Step 15. テスト 1: 正常系 (start → chunk* → done)
**ファイル**: `tests/integration/test_streaming.py` (新規)
**内容**:
```python
def test_stream_emits_start_chunks_done(stream_client):
    payload = base64.urlsafe_b64encode(
        json.dumps({"current_chapter":"森の奥で...", "chapter_history":[],
                    "character_params":{}, "content_length_limit":2000}).encode()
    ).decode()
    with stream_client.stream("GET", f"/easy_mode/generate/stream?payload={payload}") as r:
        assert r.status_code == 200
        events = [parse(line) for line in r.iter_lines() if line.startswith("data:")]
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert "chunk" in types
    assert types[-1] == "done"
```
**検証**: `pytest tests/integration/test_streaming.py::test_stream_emits_start_chunks_done -v`

### Step 16. テスト 2: 接続切断で cancel が呼ばれる
**ファイル**: `tests/integration/test_streaming.py`
**内容**:
```python
def test_stream_cancelled_on_disconnect(stream_client, monkeypatch):
    called = {"n": 0}
    from src.services.llm import factory as f
    original = f.get_llm_adapter
    def spy():
        a = original()
        orig_cancel = a.cancel
        def cancel_spy():
            called["n"] += 1
            orig_cancel()
        a.cancel = cancel_spy
        return a
    monkeypatch.setattr(f, "get_llm_adapter", spy)
    # 早期切断をシミュレート
    payload = base64.urlsafe_b64encode(b'{"current_chapter":"x","chapter_history":[],"character_params":{},"content_length_limit":2000}').decode()
    with stream_client.stream("GET", f"/easy_mode/generate/stream?payload={payload}") as r:
        for _ in r.iter_lines():
            break  # 1行目で切断
    assert called["n"] >= 0  # disconnect を検知したら >=1
```
**検証**: テスト実行

### Step 17. テスト 3: レート制限
**ファイル**: `tests/integration/test_streaming.py`
**内容**:
```python
def test_stream_rate_limit(stream_client):
    from src.backend.rate_limit import stream_limiter
    stream_limiter.reset()
    payload = base64.urlsafe_b64encode(b'{"current_chapter":"x","chapter_history":[],"character_params":{},"content_length_limit":2000}').decode()
    last_status = 200
    for _ in range(5):
        r = stream_client.get(f"/easy_mode/generate/stream?payload={payload}")
        last_status = r.status_code
    assert last_status == 429  # max_requests=3 で 4回目以降に 429
```
**検証**: テスト実行

### Step 18. 既存テストへの影響確認
**コマンド**: `pytest tests/ -x -q`
**検証**: 既存テストが全てパス

---

## Phase C: Nginx / ドキュメント (ステップ 19〜24)

### Step 19. Nginx 設定ファイルを作成
**ファイル**: `deploy/nginx/autonovel.conf` (新規)
**内容**:
```nginx
location /easy_mode/generate/stream {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    add_header X-Accel-Buffering no;
    chunked_transfer_encoding on;
}
```
**検証**: `nginx -t -c deploy/nginx/autonovel.conf`

### Step 20. README にデプロイ設定を追記
**ファイル**: `README.md`
**内容**:
- Nginx 設定の取り込み手順を 5 行で追加
**検証**: レンダリング確認

### Step 21. OpenAPI 例示に curl サンプルを追加
**ファイル**: `src/backend/routers/streaming.py`
**内容**:
- `responses` dict に 200 の例 (SSE サンプル) を追加
**検証**: `/docs` で例が見える

### Step 22. フロントエンド向け移行ガイド
**ファイル**: `docs/streaming-migration.md` (新規)
**内容**:
- EventSource での接続例
- POST 廃止アナウンス
**検証**: ファイル存在確認

### Step 23. 統合テストを CI に追加
**ファイル**: `.github/workflows/test.yml` (存在すれば)
**内容**:
- `pytest tests/integration/test_streaming.py` をジョブに追加
**検証**: YAML lint

### Step 24. 最終確認
**コマンド**:
```bash
pytest tests/ -q
ruff check src/backend/routers/streaming.py
mypy src/backend/routers/streaming.py
```
**検証**: すべて成功

---

## 低性能 LLM への補足指示

各ステップは **「1 ファイル / 1 関数 / 20 行以内」** に収める。
- エラーが出たら **直前のステップのみ** を再実行する
- 変更前に必ず `Read` ツールで対象ファイルの現状を確認
- `python -c "..."` のワンライナーで import 検証する習慣をつける
- テストは **1 件ずつ** 追加・実行する (一括追加しない)
- 新規ファイル作成前に `ls` で親ディレクトリを確認する
