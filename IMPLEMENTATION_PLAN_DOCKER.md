# AutoNovel 実装計画書: Docker 起動フロー & かんたんモード初期セットアップ健全化

## 概要

コンテナの起動から「かんたんモード」で作品を1点作成して完了するまでのフローに対して、前回の監査レポートで抽出した **High 5件 / Medium 4件 / Low 6件** の問題点を順に解消する。設定ミス・論理的矛盾・URL 不整合・依存二重管理を排除し、Docker 環境のみで完結する再現可能なワークフローを確立する。

---

## 前提・方針

- `docker-compose.yml` (dev) と `docker-compose.prod.yml` (prod) の整合を取る
- 設定値の **fail-fast** を最優先とし、未設定のまま正常終了してユーザーを混乱させる経路を全廃
- 既存の Huey キュー名 (`autonovel`) とタスク定義は変更しない
- すべての修正は段階的にデプロイ可能(ロールバック容易)
- テスト/CI が壊れない範囲で実装

---

## 実装手順

### Phase 1: 設定値 fail-fast と起動シーケンス整備 (High)

#### Step 1.1 `docker-compose.yml` の LLM キーを必須化

`docker-compose.yml:21-31` の `${OPENAI_API_KEY:-}` などを **必須化** し、未設定なら compose 起動段階で停止。

```yaml
- OPENAI_API_KEY=${OPENAI_API_KEY:?OPENAI_API_KEY is required}
- OPENAI_BASE_URL=${OPENAI_BASE_URL:-http://localhost:11434}  # openai 互換エンドポイントを許容
```

`docker-compose.prod.yml` 側は既に `?:` パターンが導入されているため、dev 側に寄せる。

#### Step 1.2 `factory.py` の Mock フォールバックを fail-fast に変更

`src/services/llm/factory.py:43-65` の `WARNING + MockLLMAdapter` フォールバックを **エラー送出** に変更。

```python
if p == "openai":
    resolved_key = api_key or settings.OPENAI_API_KEY
    resolved_url = base_url or settings.OPENAI_BASE_URL
    if not resolved_key and not resolved_url:
        raise RuntimeError(
            "OPENAI_API_KEY / OPENAI_BASE_URL が未設定です。.env を確認してください。"
        )
    return OpenAIAdapter(api_key=resolved_key, base_url=resolved_url, model=model_name)
```

`gemini` / `claude` も同様に修正。

#### Step 1.3 `init_db` を alembic upgrade head と組み合わせる `entrypoint.sh` 化

新規ファイル `docker/backend/entrypoint.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
echo "[entrypoint] running alembic upgrade head"
alembic upgrade head
echo "[entrypoint] starting: $@"
exec "$@"
```

- `Dockerfile` の `CMD` を `["docker/backend/entrypoint.sh", "uvicorn", "src.backend.server:app", "--host", "0.0.0.0", "--port", "8200"]` に変更
- `worker` コンテナは `command:` で huey_consumer を起動しているため compose 側で `entrypoint` を上書きせず、**両方の command で entrypoint.sh を前置** する
  ```yaml
  worker:
    entrypoint: ["docker/backend/entrypoint.sh", "python", "-m", "huey.bin.huey_consumer", ...]
  ```
  ただし entrypoint.sh は alembic スキップ可の引数 `--skip-migrations` を受け付ける設計にする(worker は backend の healthy 後に起動するので二重実行防止)。

```bash
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" != "--skip-migrations" ] && [ "${SKIP_ALEMBIC:-0}" != "1" ]; then
  echo "[entrypoint] running alembic upgrade head"
  alembic upgrade head
fi
shift || true
exec "$@"
```

#### Step 1.4 `docker-compose.yml` の worker を `entrypoint.sh` 経由に

```yaml
worker:
  command: []
  entrypoint:
    - docker/backend/entrypoint.sh
    - --skip-migrations
    - python
    - -m
    - huey.bin.huey_consumer
    - src.backend.tasks.huey.huey
    - -w
    - "2"
    - -k
    - thread
```

### Phase 2: ルーティング・URL 不整合解消 (High)

#### Step 2.1 `server.py` の `easy_mode.router` 二重 include を解消

`src/backend/server.py:46-47` を以下に置換。互換用 `/api/easy-mode` は **dev 環境のみ** で `deprecated` ヘッダ付き。

```python
app.include_router(easy_mode.router, prefix="/easy_mode", tags=["easy_mode"])
if settings.APP_ENV == "development":
    app.include_router(easy_mode.router, prefix="/api/easy-mode", tags=["easy-mode"])
```

#### Step 2.2 フロントの streaming URL を `/easy_mode/generate/stream` に統一

`frontend/src/api/easyMode.ts:31` の `fetch('/generate/stream', ...)` を `fetch('/easy_mode/generate/stream', ...)` に変更。BASE 定数を再利用。

```ts
const res = await fetch(`${BASE}/generate/stream`, { ... });
```

#### Step 2.3 nginx location パターンの網羅

`frontend/Dockerfile:35` を更新し、未カバーパスを追加:

```nginx
location ~ ^/(easy_mode|api|editor|graph|health|metrics|plots|episodes|books|tasks|styles|multimedia|issues|patches|marketing|branches|prompt_versions|commercial|novel|illustrations|collab|export|hooks|prompt_compare|reverse_plot|orchestrated|structure|system|trace) {
  proxy_pass http://backend:8200;
  ...
}
```

さらに SSE 用に `proxy_buffering off;` と `proxy_cache off;` を追加。

### Phase 3: Medium 修正

#### Step 3.1 Huey キュー名の統一

`src/backend/worker_config.py` を削除(未使用)し、import 元が単一であることを保証。grep で参照箇所がないことを確認の上で削除。

#### Step 3.2 dev compose の storage ボリュームマウント追加

`docker-compose.yml` の `backend` / `worker` に:

```yaml
volumes:
  - ./storage:/app/storage
```

#### Step 3.3 `check_llm_gateway` の存在しないモデル名を修正

`src/backend/health/checks.py:141` の `gemini-3.5-flash-lite` を `settings.GEMINI_MODEL` に切替:

```python
result = await factory.generate_text(
    model=settings.GEMINI_MODEL,
    prompt="ping",
    max_tokens=1,
    temperature=0.0,
)
```

#### Step 3.4 prod compose の backend に healthcheck 追加

`docker-compose.prod.yml:42` 付近に healthcheck を追加(Dockerfile 側の HEALTHCHECK を削除して compose に集約):

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8200/health').read()"]
  interval: 30s
  timeout: 5s
  retries: 5
  start_period: 30s
```

`worker` の healthcheck は維持 (`disable: true` のまま)。

### Phase 4: Low 修正

#### Step 4.1 `.dockerignore` に `.env*` 追加

```
.env
.env.*
```

#### Step 4.2 `requirements.txt` の `pgvector` パッケージ調査

`grep -rn "from pgvector\|import pgvector" src/` で参照がないことを確認し、未使用なら requirements.txt から削除。

#### Step 4.3 `.env.example` 拡充

```ini
# LLM
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
VLLM_BASE_URL=http://localhost:8000
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct

# Production secrets
POSTGRES_PASSWORD=
REDIS_PASSWORD=
UVICORN_WORKERS=2
```

#### Step 4.4 フロントの polling に AbortController / タイムアウト

`frontend/src/api/easyMode.ts:41` の `pollGenerationStatus` に `signal` 引数と最大リトライ回数 (例: 60 回 × 2 秒 = 120 秒上限) を実装。`useGenerate` フックから `AbortController` を渡す。

#### Step 4.5 `init_db` の冗長 print 削除

`src/backend/database/core.py:343-345` の 3 つの `print(...)` を `logger.debug(...)` に変更。

#### Step 4.6 README に rate limit 1-worker 注記

`README.md` の Operations / Docker セクションに「`UVICORN_WORKERS=1` を推奨(process 内レートリミッタのため)」を追記。

### Phase 5: 検証

#### Step 5.1 静的検証

```bash
py -m ruff check src tests
py -m pytest -q --tb=short -x
cd frontend && npm run lint && npm run typecheck && npm run test:ci
```

#### Step 5.2 Docker ビルド/起動検証

```bash
# ビルド
docker compose build backend worker frontend-dev

# 未設定で起動失敗することを確認
docker compose up backend  # OPENAI_API_KEY 未設定でエラー終了

# .env にキーを設定して起動
docker compose up -d
docker compose ps
curl -sf http://localhost:8200/health | jq .

# かんたんモード E2E (curl)
curl -sf -X POST http://localhost:8200/easy_mode/generate \
  -H 'Content-Type: application/json' \
  -d '{"character":{"name":"テスト","genre":"ハイファンタジー","personality":"正義感","ability":"剣"},"current_chapter":"導入","chapter_history":[]}'
```

期待結果: backend/worker/frontend-dev すべて healthy、`/health` が `status=ok`、生成タスクが DB に保存される。

#### Step 5.3 回帰テスト

`tests/integration/` 配下の easy_mode / health / tasks テストを全件パスさせる。新規に `tests/integration/test_docker_compose_health.py` を追加し、`/health` の 200 + `status=ok` 応答を検証。

---

## 変更ファイル一覧

| Phase | ファイル | 内容 |
|---|---|---|
| 1 | `docker-compose.yml` | OPENAI_API_KEY 必須化、worker entrypoint、storage マウント |
| 1 | `docker-compose.prod.yml` | backend healthcheck 追加 |
| 1 | `src/services/llm/factory.py` | Mock フォールバック → raise RuntimeError |
| 1 | `docker/backend/entrypoint.sh` | alembic upgrade head + exec |
| 1 | `Dockerfile` | CMD を entrypoint 経由に |
| 2 | `src/backend/server.py` | easy_mode 二重 include 解消 |
| 2 | `frontend/src/api/easyMode.ts` | streaming URL 統一、polling タイムアウト |
| 2 | `frontend/Dockerfile` | nginx location 網羅、SSE 設定 |
| 3 | `src/backend/worker_config.py` | 削除 |
| 3 | `src/backend/health/checks.py` | モデル名を settings から |
| 4 | `.dockerignore` | `.env*` 追加 |
| 4 | `requirements.txt` | `pgvector` 削除(未使用なら) |
| 4 | `.env.example` | LLM/secrets 項目追加 |
| 4 | `src/backend/database/core.py` | print → logger.debug |
| 4 | `README.md` | rate-limit 1-worker 注記 |
| 5 | `tests/integration/test_docker_compose_health.py` | 新規 |

---

## リスク・ロールバック

- **Step 1.1**: 既存ユーザーが `.env` なしで起動できなくなる → README の Quick Start を冒頭に明示。
- **Step 1.2**: Mock での単体テストが壊れる可能性 → テストでは `LLM_PROVIDER=mock` を維持(factory が明示的に `mock` を受け入れるパスを維持)。
- **Step 1.3**: alembic マイグレーション履歴の不整合が残っていると upgrade 失敗 → `alembic current` で事前確認、ロールバック手順を `IMPLEMENTATION_PLAN_AUDIT_REVIEW_LEARNING.md` に追記。
- **Step 2.1**: `/api/easy-mode` への依存クライアントが壊れる可能性 → `APP_ENV` 判定で dev のみ残し、prod では完全削除。
- **Step 2.2**: 既存のローカル開発者(proxy 経由でない vite 単体利用)でストリーミングが `/generate/stream` 前提だった場合 → vite proxy 設定を確認、nginx 経由なら問題なし。

ロールバック: 各 Phase を独立した commit に分け、`git revert` で任意の Phase を取り消せる粒度を維持。
