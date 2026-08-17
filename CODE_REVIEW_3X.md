# コードレビュー（3倍詳細版）— autonovel / 覇権小説エンジン

- 対象: リポジトリルート `/home/herbmatsui/autonovel`、Python ファイル 677 本、約 53,181 行（`src/` 配下）
- 視点: アーキテクチャ・正確性・セキュリティ・パフォーマンス・並行安全性・保守性・テスト
- 前回（通常版）レビューから 3 倍の深さで、具体的な `file:line` と再現・影響・修正案を提示

---

## 0. エグゼクティブサマリー

| 区分 | 重大度 | 代表箇所 |
|---|---|---|
| A. 重複する LLM クライアント層（3系統並存） | 🔴 Critical | `src/llm/*`, `src/core/llm_gateway.py`, `src/backend/llm_client.py` |
| B. 重複モジュール名（module と package 同名） | 🔴 Critical | `erotic_integrity.py` vs `erotic/`、`spice_guard.py` vs `spice_guard/` |
| C. `init_db` が Alembic をスキップし `create_all` を実行 | 🔴 Critical | `src/backend/database/core.py:305-331` |
| D. DB アクセス層の多重化（Manager / Repository / 生 SQL） | 🟠 High | `core.py`, `uow.py`, 25 本の repositories |
| E. リトライ/フォールバック処理の脆弱性と疑似モデル名 | 🟠 High | `src/services/retry_decorator.py:146,308-330` |
| F. セキュリティヘッダ/認証/ログ漏洩 | 🟠 High | `server.py:135-180`, `core.py:225` |
| G. 非同期コードでの無意味なロックとデッドコード | 🟡 Medium | `retry_decorator.py:131-151`, `core.py:144-176` |
| H. ブロード `except Exception` の過剰な網羅（40+箇所） | 🟡 Medium | `tasks.py`, `engine_context.py`, `health/checks.py` 等 |
| I. 本番コードパスでの `print()` 残存 | 🟡 Medium | `presets/loader.py`, alembic versions |
| J. 例外階層の重複定義 | 🟢 Low | `src/core/exceptions.py` |

優先対応: **A・B・C** はリファクタまたは統合しない限り、機能追加時にバグの温床となる。

---

## 1. アーキテクチャ — 系統重複（A, B, D）

### A. LLM クライアントが 3 系統並存
- `src/llm/` — `gemini_client.py`, `gemini_provider.py`(? 実体は `base.py`/`provider_factory.py`), `openai_provider.py`, `model_router.py`
- `src/core/llm_gateway.py` — `LLMProviderFactory`, `create_genai_client`, `LLMGenerateResultProxy`
- `src/backend/llm_client.py` — さらに別の LLM クライアント

同じ「Gemini を呼ぶ」責務が少なくとも 3 か所に分散。結果:
- プロバイダ切替・フォールバック・トークン上限判定のロジックが複数箇所に重複（例: トークン上限の文字列判定が `retry_decorator.py:186-197` と各 client の例外処理に二重実装）。
- 新しいモデル追加時に 3 か所を整合させる必要があり、既に `MODEL_STABLE_FALLBACK` / `MODEL_ULTRA_STABLE` のハードコード（`retry_decorator.py:301-330`）が古いモデル名（`gemini-3.1-flash-lite`）を参照している。

**修正案**: `src/core/llm_gateway.py` を単一のファサードとし、`src/llm/*` をその背後のプロバイダ実装として吸収。`src/backend/llm_client.py` は gateway への薄いアダプタに降格または削除。

### B. 同名の module と package（import の曖昧さ）
- `src/agents/erotic_integrity.py` (2,779 行) と `src/agents/erotic/` (package: `continuity.py`, `filter.py`, `vocabulary.py`, `curve.py`)
- `src/easy_mode/spice_guard.py` (537 行) と `src/easy_mode/spice_guard/` (package: `__init__.py`, `extractor.py`, `marker.py`, `pattern_registry.py`)

同名のモジュールとパッケージが共存すると、`import spice_guard` がどちらを解決するかは配置順に依存し、テスト/実行環境で挙動が変わる。`erotic_integrity.py` はさらに `SCENE_TYPES` を **2 回同一内容で定義**（行 15-26 と 28-40）している（後述 5-E）。

**修正案**: 大モジュールを `erotic_integrity/` パッケージへ分割し、`spice_guard.py` は `spice_guard/__init__.py` のエイリアスにするか完全統合する。

### D. DB アクセス層の多重化
- 低レベル: `DatabaseManager`（`core.py`）— `execute/fetch_one/fetch_all` は「非推奨」としつつ `logger.warning` で毎回出力（後述 F）。
- 中レベル: `UnitOfWork`（`uow.py`）が `BibleRepository` 等 13 種のリポジトリを保持。
- リポジトリ層: `src/backend/database/repositories/*`（24 本）＋ 古い `repo_*.py`（`repo_plot.py`, `repo_book.py`…）が並存。

`repo_*.py`（単数形）と `repositories/*.py`（複数形）が重複。DB アクセス経路が 3 通りあり、どの経路が正であるかの規約が不在。

---

## 2. データベース — 正確性とスキーマ管理（C, D, G）

### C. `init_db` が Alembic を飛ばして `create_all`（`core.py:305-331`）🔴
```python
engine = create_engine(sync_url)
Base.metadata.create_all(engine)   # マイグレーションを無効化
# command.upgrade(alembic_cfg, "head")  # コメントアウト
```
- `src/backend/alembic/versions/` に本番用マイグレーションが存在するにもかかわらず、起動時に `create_all` でモデル定義から強制作成している。
- リスク: マイグレーション（列追加・データ移行・制約緩和）と `models.py` の定義が乖離したとき、**一部の環境だけスキーマが違う**状態になる。`create_all` は「存在しない表の作成」のみで、列型変更や列削除は絶対に反映されない。
- さらにこの処理は **同期ブロッキング**（`create_engine` + `create_all`）であり、`lifespan` の中で呼ばれるため（実質起動時 1 回だが）イベントループをブロックする。

**修正案**: 本番は `command.upgrade` のみにする。`create_all` はテスト専用 DB または `KAKU_ENV=test` のみ許可するフラグを設ける。

### G. `DatabaseConnectionWrapper` の unsafe `__setattr__`（`core.py:103-107`）
```python
def __setattr__(self, name, value):
    if name in ("sql_conn", "dbapi_conn"):
        super().__setattr__(name, value)
    else:
        setattr(self.dbapi_conn, name, value)   # 任意属性を生接続へ転送
```
任意の属性代入が内部 DBAPI 接続へ転送される。呼び出し側が誤って `wrapper.some_flag = ...` を書くと、DBAPI 接続の内部状態を汚染する。wrapper は必要最小のメソッドだけを公開する（`__slots__` 推奨）。

### G. `get_conn` がプライベート属性へ到達（`core.py:191-196`）
```python
raw_conn = await sql_conn.get_raw_connection()
dbapi_conn = raw_conn._connection          # プライベート
```
SQLAlchemy の非公開属性 `_connection` に依存。バージョンアップで破損する。raw 接続が本当に必要なら `engine.raw_connection()` を使う。

### UoW のトランザクション入れ子（`uow.py:158-164`）
```python
self.session = self.db.get_session()
await self.session.begin()
```
`async_sessionmaker(expire_on_commit=False)` から作ったセッションに対し `begin()` を呼ぶ。セッションが既にトランザクション中（ネストした UoW）の場合 `begin()` はエラーになる。ネスト呼び出しが存在しないか要確認。またアウトボックス・パターンで「Chroma 書き込み」は `outbox_service.flush` が SQLite へ **意図** を書くだけで、実際の Chroma 反映が別プロセス/別トランザクションで行われる構成なら、SQLite コミット成功 → Chroma 失敗時に **不整合** が残る（補償トランザクションの実装有無を要確認）。

---

## 3. リトライ・レジリエンス（E, G）

### E. 疑似/ハードコード モデル名（`retry_decorator.py:308-330`）🔴
```python
state.model_name = (
    MODEL_ULTRA_STABLE if MODEL_ULTRA_STABLE
    else "gemini-3.1-flash-lite"   # 実在しない/古いモデル名
)
```
`config` に定数が無いときにフォールバックする文字列が `gemini-3.1-flash-lite`（実在しない命名）。フォールバックが発動すると **存在しないモデルへの永続的再試行** となり、ユーザーに届くエラーが意味不明になる。

### E. `_extract_llm_params` の脆いヒューリスティクス（`retry_decorator.py:47-95`）
- `args[1]` が `model_name`/`prompt` 属性を持つかだけで判定（`line 50`）。呼び出しシグネチャが変わると `max_retries`/`temp`/`model_name` が **全て既定値（5 / 0.7 / ""）** に黙ってフォールバックする。
- 既定 `model_name=""` のまま本番呼び出しが走ると、`except` ブロックの `"model is required"` 判定（line 200）で初めて `LLMUnrecoverableError` になるが、そもそも引数抽出が失敗したこと自体が通知されない。

### E. 5xx カウントのロック下再読み取り（`retry_decorator.py:285-298`）
インクリメント直後に同じロック内で `getattr(self, "_consecutive_5xx", 0)` を再読みしているが、`with lock:` ブロックのスコープ外で `fail_count` を使うため、実質的に「直前に +1 した値」が入るだけ。ロジックは動くが意図が読み取りにくく、コメント `fail_count = ...` が誤導する。

### G. デッドコード（`retry_decorator.py:146-151`）
```python
consecutive_5xx = getattr(self, "_consecutive_5xx", 0)   # 代入のみで未使用
if lock is not None:
    with lock:
        setattr(self, "_consecutive_5xx", 0)
```
`consecutive_5xx` ローカル変数は以降使われない（リセットの副作用のみ）。変数代入を削除。

### G. 非同期コードでの `threading.Lock` の無意味性（`retry_decorator.py:131-151`）
`_lock` が `threading.Lock` なら asyncio 単一スレッドでは保護にならず、await 境界をまたぐと意味をなさない。そもそも `_active_requests` は **カウントするだけで実際の同時実行制限（セマフォ）には使われていない**。制限が目的なら `asyncio.Semaphore` を導入すべき。

---

## 4. API / セキュリティ / ミドルウェア（F, server.py）

### F. Redis レートリミッター未初期化時のカスケード（`server.py:160-180`）
```python
if _redis_rate_limiter is None:
    redis = RedisCacheService()
    _redis_rate_limiter = RedisRateLimiter(redis=redis, ...)
allowed = await _redis_rate_limiter.is_allowed(client_ip)
```
- `_redis_rate_limiter` はモジュールグローバルだが、Redis がダウンしている場合 `is_allowed` が例外を投げると **全リクエストが 500** になる（ミドルウェア内で捕捉されていない）。
- さらに `_rate_limit_store: dict[str, list[float]] = defaultdict(list)`（`line 144`）と `_rate_limit_lock`（`line 146`）は **完全に未使用のデッドコード**（Redis 実装に置換された名残）。

**修正案**: `is_allowed` は try/except で失敗時は許可（fail-open）またはキューイングし、未使用変数を削除。

### F. CORS の `allow_credentials=True` + 動的オリジン（`server.py:183-192`）
`allow_credentials=True` と `allow_methods=["*"]`/`allow_headers=["*"]` の組み合わせ。オリジンが `get_allowed_origins()` で `"*"` を含む設定になった場合、クレデンシャル付きの全オリジン許可となる。`get_allowed_origins` が `"*"` を返さないことを単体テストで保証すること。

### F. 認証キーの比較方式（`server.py:275,300,384` → `src/backend/auth.py`）
`validate_api_key_or_raise(req.api_key)` — 辞書/文字列比較が `==` の場合、タイミング攻撃の余地がある。定数時間比較（`hmac.compare_digest`）への置換を推奨。

### F. ログへの機微情報混入（`core.py:225,241,258`）
```python
logger.warning(f"DatabaseManager.execute called: {sql}")
```
全 SQL を **WARNING** で出力。SQL にユーザー入力（小説本文・プロンプト・API キーが誤って含まれるクエリ）が含まれる可能性があり、本番ログへの機微情報流出リスク。DEBUG 化 + パラメータのマスキングを推奨。

### F. HSTS ヘッダの無条件付与（`server.py:140`）
`Strict-Transport-Security` を HTTP 終端環境でも付与。開発/ローカルで害は少ないが、設定で切り替え可能に。

### 起動シーケンス（`server.py:66-92`）
`except Exception:` の後に `except BaseException as e:` がある。`BaseException` は `KeyboardInterrupt`/`SystemExit` を含み、意図せず捕捉・再送出する。起動失敗時のシャットダウン処理としては許容だが、`finally` で `engine.dispose()` を行うなら `BaseException` 節は不要。

---

## 5. 各ファイルの詳細所見

### 5-A `src/agents/erotic_integrity.py`（2,779 行）
- **重複定数**: `SCENE_TYPES` を 2 回同一内容で定義（行 15-26 と 28-40）。後者が優先されるが、保守時に片方だけ変更されるリスク大。
- ファイルが巨大すぎ（単一責任の原則違反）。`erotic/` パッケージ側の `continuity.py`/`filter.py`/`vocabulary.py` と責務が重複・不明瞭。

### 5-B `src/backend/sanitizer.py`（879 行）
- `NormalizationFlow` の JSON 修復ロジックは複雑だが、入力が壊れていた場合の上限・循環防止が不明確。再帰・正規表現置換の無限ループ/爆発的バックトラック（ReDoS）に備え、試行回数上限とタイムアウトを明示すべき（特に LLM 出力をそのまま正規表現に通す箇所）。
- Pydantic `ValidationError` を文字列化して再試行プロンプトに戻す（`retry_decorator.py:159`）のは妥当だが、エラーメッセージ内のユーザーデータがプロンプトへ混入する可能性を確認。

### 5-C `src/easy_mode/spice_guard/__init__.py` ＋ `pattern_registry.py`
- `SpiceGuard` ファサードの責務は明確。だが同名 `spice_guard.py`（537 行）との重複（B）のため、どちらが本番で import されているかを `python -c "import spice_guard; print(spice_guard.__file__)"` で検証済みとすること。

### 5-D `config/settings.py`（SSOT）
- `Settings` が pydantic-settings で `KAKU_` プレフィックスを使うのは良い。ただし `src/core/container/app.py` の `api_key` プロバイダが `get_settings()` 経由のフォールバックを持つ一方、`server.py:333` は `AppContainer(api_key=req.api_key, ...)` でリクエスト毎に上書きする。DI 上書きと設定フォールバックの優先順位が文書化されておらず、どちらの API キーが実際に使われるかが経路依存。

### 5-E `src/core/rate_limiter.py`（`TokenBucket`）
- 非同期 `TokenBucket` の実装は概ね健全。ただし複数プロセス（uvicorn `--workers N` 等）で動く場合、インメモリ桶はプロセス間で共有されずレート制限が無効化される。`RedisRateLimiter` への統一、またはワーカー数に応じた係数調整が必要。

### 5-F `src/backend/database/core.py`
- `DatabaseManager.__init__` の `pool_size=10` は SQLite では無視される（接続プールは Postgres のみ意味を持つ）。誤解を招くのでコメントで明記。
- `fetch_lastrowid`（`line 263-266`）は `engine.begin()` のコネクションに対し `exec_driver_sql` を使い `lastrowid` を返すが、SELECT 等の場合の挙動が不定。insert 専用であることを型/コメントで保証。

---

## 6. 保守性 / コード品質（H, I, J）

### H. 過剰な `except Exception`（40+ 箇所）
`grep` で `src/backend/tasks.py`(8), `engine_context.py`(3), `health/checks.py`(5), `infrastructure/api/api_client.py`(4) 他を確認。網羅的すぎる捕捉は:
- プログラム上のバグ（本来失敗すべき）を隠蔽し、後段で「空の結果」「None 伝播」として別のクラッシュを引き起こす。
- 特に `tasks.py` のワークフロー実行は失敗をログだけで済ませ、タスク状態が「永遠に running」になる恐れ。失敗状態の明示的遷移を。

### I. 本番パスでの `print()`（`presets/loader.py:187-191`, alembic versions, `cli/*`）
- `presets/loader.py` はライブラリコードであり `print` ではなく `logging` を使うべき。
- alembic マイグレーション内の `print` はログ基盤に統一。

### J. 例外階層の重複定義（`exceptions.py`）
`HegemonyError` 配下に 15 以上のサブクラスがあり、**全てが同じ形の `__init__` をコピー**している（`status_code`/`error_code` を再指定）。クラス変数でデフォルトを持たせ、`dataclass` または基底のキーワード引数で十分。保守コスト大。

### 未使用 / 死コード
- `server.py:144-146` の `_rate_limit_store`, `_rate_limit_lock`（F で言及）。
- `retry_decorator.py:146` のデッド代入（G で言及）。
- `core.py` の `enqueue_write`/`flush_writes`（後方互換ダミー、`line 206-212`）— 呼び出し元が無ければ削除。

---

## 7. テスト / 品質ゲート

- テストは `tests/unit/` へ移動済み（前フェーズ）。ただし本レビューで指摘した **クリティカル経路**（A の LLM フォールバック、C のスキーマ乖離、E の疑似モデル名、F の Redis ダウン時 500）に対する回帰テストが存在するか確認が必要。
- `.pre-commit-config.yaml` の xenon 閾値を `A` に厳格化したのは妥当（複雑度監視）。ただし `erotic_integrity.py`(2779 行) や `sanitizer.py`(879 行) のような巨大モジュールは xenon の個別メソッド閾値を超えている可能性があり、分割が先決。

---

## 8. 優先順位付きアクションプラン

| # | 優先度 | アクション | 該当 |
|---|---|---|---|
| 1 | 🔴 P0 | LLM クライアント層を `llm_gateway.py` に統合、疑似モデル名 `gemini-3.1-flash-lite` を定数から削除 | A, E |
| 2 | 🔴 P0 | `init_db` の `create_all` を本番から除外（Alembic `upgrade` のみ）、テスト用フラグ化 | C |
| 3 | 🔴 P0 | 同名 module/package（`erotic_integrity`・`spice_guard`）を統合し import 解決を確定 | B |
| 4 | 🟠 P1 | `repo_*.py` と `repositories/*.py` の統合、DB 経路の単一化 | D |
| 5 | 🟠 P1 | Redis レートリミッターの fail-open 化と未使用変数削除 | F |
| 6 | 🟠 P1 | `DatabaseConnectionWrapper.__setattr__` を `__slots__` + 最小公開に | G, D |
| 7 | 🟡 P2 | `retry_decorator` の `_extract_llm_params` を明示的引数へ、デッドコード削除 | E, G |
| 8 | 🟡 P2 | `except Exception` の絞り込み（tasks/engine_context/health）と失敗状態遷移 | H |
| 9 | 🟡 P2 | `print` → `logging` 化、`exceptions.py` の重複 `__init__` 削減 | I, J |
| 10 | 🟢 P3 | SQL ログを DEBUG+マスキング化、HSTS 設定化 | F |

---

## 9. 結論
本プロジェクトは機能実装が先行し、**「同じ責務の多重実装」が最大の技術債** となっている（LLM 層 ×3、DB 層 ×3、同名モジュール）。これらを統合しない限り、どの修正も「どの層に書くか」の迷いとバグの再発を生む。まず P0 の 3 点（LLM 統合・スキーマ管理・同名解消）を完了させ、その後 P1 の DB/Redis 整頓、P2 の堅牢性・保守性改善へ進めることを推奨する。
