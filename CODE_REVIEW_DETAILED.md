# ��権小説エンジン - コードレビュー報告書

**レビュー対象**: kaku-hegemony v3.2 (2026-08-13時点)
**レビュー日**: 2026-08-14
**レビュー����**: src/ 全体、tests/、config/、streamlit_app/

---

## ��� 総合評価

| ��目 | 評価 | 備考 |
|------|------|------|
| **アーキテクチャ設計** | ������������☆ | DIコンテナ・ProtocolベースのDI、レイヤー分離は良好。��環依存が一部残存 |
| **コード品質** | ���������☆☆ | ���ヒント充実、しかし `Any` 多用、巨大ファイル、��務過大クラスが散見 |
| **テスト品質** | ���������☆☆ | 単体・統合テスト��富だが、モック重複、E2Eテストの不安定性、カバレッジ不明 |
| **ドキュメント** | ������������☆ | README充実、ADR等設計ドキュメントあり。コード内docstringは不均一 |
| **運用・監視** | ������������☆ | ��ルスチェック・Prometheusメトリクス・構造化ログ実装済み |
| **セキュリティ** | ���������☆☆ | APIキー管理・SQLインジェクション対策は概ね良好。入力����に��さあり |

**総合: B+ (良好だが改善余地大)**

---

## ������ アーキテクチャ・設計

### ��い点

1. **DIコンテナの適切な活用** (`src/core/container/`)
   - `InfraContainer` (インフラ��) と `AppContainer2` (アプリ��) の分離
   - `providers.Singleton/Factory` の使い分けが適切
   - 後方互��エイリアス (`AppContainer = InfraContainer`) は意��的で明記済み

2. **Protocolベースのインターフェース定義** (`src/core/interfaces.py`)
   - `ILLMClient`, `IPromptManager`, `IRepository` 等で依存性逆転実現
   - ���安全なモック差し替えが容易

3. **レイヤー分離の意��**
   ```
   core (DI, インターフェース, 例外, 観��性)
   ├── agents (エージェント実装)
   ├── backend (エンジン、ワークフロー、タスク)
   ├── llm (プロバイダ��象化、モデルルーティング)
   ├── services (ビジネスロジック)
   └── models (Pydanticモデル、DBモデル)
   ```

### ��善が必要な点

| ��題 | 影響度 | 詳細 |
|------|--------|------|
| **��環依存の残存** | ��� High | `src/backend/engine.py` → `src/agents/*` → `src/backend/*` 相互参照。`_legacy_dep` でランタイム解決 |
| **God Class: `UltimateHegemonyEngine`** | ��� High | 400行超、15個の `property` で��延依存解決。SRP違反 |
| **巨大ファイル: `writing.py` (2,400行)** | ��� Medium | 文��構��・����・パイプライン・スケジューラ連��が混在 |
| **設定の分散** | ��� Medium | `config/constants.py`, `config/models.py`, `config/project_context.py`, `config/settings.py` が混在 |
| **グローバル状態の多用** | ��� Low | `get_db_manager()`, `_GLOBAL_DB_MANAGER`, `get_config()` 等 |

---

## ��� 詳細コードレビュー

### 1. DIコンテナ周り (`src/core/container/`)

#### `app.py` - ��い設計
```python
# �� 適切: 具象クラスではなく文字列参照で��延インポート
plot_service = providers.Factory["PlotService"](
    "src.services.plot_service.PlotService",
    repo=repo,
    llm=llm,
)
```

#### ���念点
- `api_key = providers.Object("DUMMY")` - 本番では環境変数から注入すべき（`.env` 経由で上書きされる想定だが明示的でない）
- `connection_pipeline = providers.Singleton(lambda: None)` - プレースホルダが本番コードに残存

### 2. LLMゲートウェイ (`src/core/llm_gateway.py`)

#### 優秀な実装
- **スキーマモードフォールバック** (`native` → `clean_dict` → `prompt_fallback`) - Geminiの制限回��に��果的
- **適応的温度減��** - リトライ毎に `temp - attempt * 0.15` で確率的出力を制御
- **NSFWモード別セーフティ設定** - `HarmBlockThreshold.BLOCK_ONLY_HIGH` で適切に��和
- **指数バックオフ + ジッター** - `with_llm_retry` デコレータと連��

#### ��善点
```python
# ��� ���い例: インラインで巨大な関数 (generate_json 200行超)
# �� ��善: 以下のように分割すべき
class GeminiApiClient:
    def _build_prompt(self, prompt, response_schema, mode, error_feedback): ...
    def _execute_with_stream(self, model, prompt, config, callback): ...
    def _execute_without_stream(self, model, prompt, config): ...
    def _validate_response(self, response, response_schema): ...
```

- `LLMGenerateResultProxy.generate()` がプレースホルダ実装 (`return {}, "", None`) - ��除または実装必��
- `OpenAIApiClient` で毎回 `AsyncOpenAI` クライアントを生成 - プール化すべき

### 3. リトライデコレータ (`src/services/retry_decorator.py`)

#### 優秀な設計
- `RetryState` で試行状態を明示的に管理
- `CooldownProtocol` / `LLMClientProtocol` で��結合
- **Fail-Fast パターン**: `TypeError`, `NameError` 等は即座に再スロー
- **モデルフォールバック**: 5xx連続時 `STABLE_FALLBACK` → `ULTRA_STABLE` へ自動切替

#### ��善点
```python
# ��� ���い例: ロック操作が散在
lock = getattr(self, "_lock", None)
if lock is not None:
    with lock:
        setattr(self, "_active_requests", active_requests + 1)
else:
    setattr(self, "_active_requests", active_requests + 1)

# �� ��善: ��ルパー��ソッド化
def _increment_active(self): ...
def _decrement_active(self): ...
```

- 400行超の巨大デコレータ - クラスベース (`RetryPolicy`) へのリファクタリング推��
- `reporter` への依存が強い - `IReporter` Protocol 使用で��結合化可能

### 4. エージェント�� (`src/agents/`)

#### `writing.py` - **最大の問題ファイル (2,425行)**

| ��務 | 行数 | ����分割 |
|------|------|----------|
| 文��構�� (`build_full_writing_context`) | ~300 | `ContextBuilder` クラスへ |
| プロンプト構��・官能��理 (`write_episode`) | ~400 | `PromptComposer` + `EroticEnhancer` へ |
| エピソード生成パイプライン | ~500 | `EpisodePipeline` へ |
| ストリーミングスケジューラ連�� | ~200 | `SchedulerCoordinator` へ |

**具体的問題:**
```python
# ��� Any 多用で型安全性��如
async def _get_plot(self, book_id: int, branch_id: int, ep_num: int) -> Optional[Any]:
    return await self.repo.get_plot(book_id, ep_num, branch_id=branch_id)

# ��� インスタンス変数への動的属性追加 (pm, planner, plot_expander properties)
@property
def pm(self): return self.prompt_manager
@pm.setter
def pm(self, value): self._pm = value  # 実体は prompt_manager なのに別名で混乱

# ��� 例外��み込み (ログのみで��続)
try:
    for task in scheduler.tasks.values():
        if not task.done():
            task.cancel()
except Exception as exc:
    logger.warning("スケジューラタスクのキャン��ルに失敗: %s", exc, exc_info=True)
```

#### `erotic_integrity.py` (99,091行!)
- **単一ファイルとして最大** - 明らかに分割不足
- ���能: ����バンク、テンプレート、評価器、フィルタ、カーブ生成等
- ����: `erotic/vocabulary.py`, `erotic/curve.py`, `erotic/evaluator.py`, `erotic/filter.py` 等へ分割

### 5. データベース�� (`src/backend/database/`)

#### 優秀な実装
- **SQLAlchemy 2.0 非同期** (`AsyncSession`, `create_async_engine`) 適切活用
- **接続プール最適化**: `pool_pre_ping=True`, `pool_recycle=1200`, `max_overflow=20`
- **SQLite WALモード + PRAGMA チューニング** - 並行性・性能への配��良好
- **リトライデコレータ** (`retry_with_logging`) で一時的エラーに強��

#### ���念点
```python
# ��� 非推��警告を出しつつ raw SQL 実行を許容
async def execute(self, sql: Any, params: Any = ()) -> None:
    if isinstance(sql, str):
        warnings.warn("DatabaseManager.execute() with raw string is deprecated...", DeprecationWarning)
        sql = text(sql)
    # 実行される → ���び出し��が直さない限り警告のみ

# ��� グローバルシングルトン + DI コンテナの二重管理
_GLOBAL_DB_MANAGER: Optional[DatabaseManager] = None
def get_db_manager() -> DatabaseManager:
    if _GLOBAL_DB_MANAGER is not None: return _GLOBAL_DB_MANAGER
    try: return AppContainer.db()  # DI優先
    except: pass  # フォールバックでグローバル生成
```

### 6. ワークフロー (`src/backend/workflows/`)

#### `full_auto_workflow.py` - ��い例
- `BaseWorkflow` ��承で共通��理集約
- `reporter.update_progress()` で進��可視化
- エラー��ンドリングでユー��ー向けメッセージを適切に返却

#### ��善点
- `run_pipeline_with_retry` 等の共通関数が `_shared_ops.py` に散在
- ワークフロー間の共通基盤 (`BaseWorkflow`) が��い - テンプレートメソッドパターンで統一すべき

### 7. フロントエンド (`streamlit_app/` / `frontend/`)

#### Streamlit版 (`streamlit_app/`) - **保守モード**
- `easy_mode_runner.py` でバックグラウンドタスク実行
- `dependency_container.py` でDIコンテナ初期化
- **問題**: `streamlit` 依存がコアロジックに��出 (`src/core/llm_gateway.py` で `streamlit.*` mypy ignore)

#### React版 (`frontend/`) - **メイン**
- TypeScript + Vite + TailwindCSS + Zustand
- コンポーネント分割適切 (`ui/`, `controllers/`, `sidebar_sections/`)
- **注意**: このレビューでは詳細未確認

---

## ��� テスト品質

### ��い点
- **テスト数��富**: `tests/` 直下 70+ ファイル、`tests/unit/` 30+ ファイル
- **フィクスチャ充実**: `conftest.py` で `real_db_manager`, `mock_llm` 提供
- **統合テスト**: `test_phase1_preset_integration.py` (17テスト), `test_phase2_pipeline_integration.py` (20テスト) 等

### ��善必��項目

| ��題 | 詳細 |
|------|------|
| **モックの重複・不整合** | `tests/mocks/mock_llm.py` 等が複数あり、実装が��離 |
| **E2Eテストの不安定性** | `test_full_balance_pipeline_e2e.py` 等で外部API依存・時間依存 |
| **カバレッジ未��定** | `pytest --cov` 実行環境未整備 (`.coverage` ファイルのみ存在) |
| **テスト分類不明確** | `unit/`, `integration/`, `e2e/` 存在するが境界���� |
| **プロパティベーステストなし** | ���界��・��常��の体系的����不足 |

---

## ��� ���ヒント・静的解��

### mypy 設定 (`pyproject.toml`) - **��格で優秀**
```toml
[tool.mypy]
strict = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
no_implicit_optional = true
warn_return_any = true
warn_unused_ignores = true
```

### 現状の違反例 (多数)
```python
# ��� Any 多用 (writing.py だけで 50+ ��所)
repo: Any = None
style_rag: Any = None
plot_expander: Any = None

# ��� ���無視コメント乱用
from google import genai  # type: ignore
from google.genai import types as genai_types  # type: ignore

# ��� プロトコル未実装クラスをプロトコルとして渡す
llm: Optional[LLMService] = None  # LLMService は Protocol ではない
```

---

## ��� セキュリティ

### ��い点
- **パラメータ化クエリ**: SQLAlchemy ORM / `text()` + params で SQL インジェクション防止
- **APIキー管理**: 環境変数 (`.env`) + Docker secrets ���定
- **NSFW オプトイン**: デフォルト OFF、明示的同意必��

### ��善点
```python
# ��� 入力����不足 (engine.py)
async def sync_bible(self, book_id: int, reporter=None):
    return await self.bible_agent.sync_bible_lifecycle(book_id, reporter=reporter)
    # book_id の����チェック・存在確認なし

# ��� パス遍歴の可能性 (config/project_context.py)
def _persist_to_toml(self, config_model):
    settings_path = BASE_DIR / "config" / "settings.toml"
    # BASE_DIR が����されている場合の����なし
```

---

## ��� パフォーマンス

### ボトルネック候補
| ��所 | ���念 | ����対策 |
|------|------|----------|
| `WritingAgent.build_full_writing_context` | ��回DBクエリ多数 (plot, book, chars, prev_chapter) | バッチ取得・キャッシュ活用 |
| `GeminiApiClient.generate_json` | スキーマモード3段階フォールバックで最大3回API呼出 | 事前����・キャッシュ |
| `StreamingPlotScheduler` | タスク管理に `asyncio.Task` 直操作 | ���造化並行��理 (`asyncio.TaskGroup`) |
| ChromaDB ベクトル��索 | 同期呼出でイベントループブロック | `asyncio.to_thread` または非同期クライアント |

---

## ��� 依存関係・パッケージ管理

### `requirements.txt` / `pyproject.toml` の��離
- `requirements.txt` にのみ存在: `google-genai`, `httpx`, `huey`, `redis` 等
- `pyproject.toml` の `[project]` に `dependencies` 未記載
- **推��**: `pyproject.toml` に統一、または `requirements.txt` を生成対象に

### バージョン��定不足
```
# requirements.txt (一部)
google-genai
httpx
huey
redis
# → バージョン指定なし (供給チェーン攻撃リスク)
```

---

## ��� 優先度別改善提案

### ��� Critical (即時対応)

1. **`writing.py` 分割** - 2,400行単一クラスは保守不能
2. **`erotic_integrity.py` 分割** - 99,091行は論外
3. **��環依存解消** - `engine.py` の `_legacy_dep` パターン����
4. **グローバルDBシングルトン����** - DIコンテナ一本化

### ��� High (1-2スプリント)

5. **リトライデコレータ クラス化** - `RetryPolicy` クラスへリファクタ
6. **LLMゲートウェイ分割** - `GeminiClient`, `OpenAIClient`, `SchemaValidator` 等
7. **型ヒント `Any` ����** - Protocol / 具象型で置��
8. **設定一元化** - `ConfigManager` 単一エントリポイントへ統合

### ��� Medium (技術的負��返済)

9. **テストインフラ整備** - カバレッジ��定、モック統一、Property-based testing導入
10. **ワークフロー基盤統一** - `BaseWorkflow` テンプレートメソッド化
11. **非同期最適化** - `asyncio.TaskGroup`、`asyncio.to_thread` ���用
12. **ログ構造化完成** - `StructuredLogger` 全��所適用

### ��� Low (品質向上)

13. **ドキュメント同期** - コード変更時の README/ADR 更新ルール化
14. **依存関係バージョン��定** - `pip-tools` / `uv` 導入
15. **パフォーマンスベンチマーク** - ��続的��定環境構��

---

## ��� メトリクス・KPI 提案

| ��標 | 現状 | 目標 | ��定方法 |
|------|------|------|----------|
| **��環依存数** | ~15 | 0 | `madge --circular src/` |
| **最大ファイル行数** | 99,091 | < 500 | `wc -l src/**/*.py` |
| **`Any` 使用��所** | 200+ | < 20 | `grep -r "Any" src/` |
| **テストカバレッジ** | 不明 | > 80% | `pytest --cov=src` |
| **mypy エラー数** | 50+ | 0 | `mypy src/` |
| **平均関数複��度** | 不明 | < 10 | `radon cc src/` |

---

## ��� 結論

**��権小説エンジン v3.2** は、**「動くプロダクト」として高い完成度**を持ち、かんたんモード Phase 1-3 の実装によりユー��ー価��を大きく前進させている。

しかし、**内部構造には深刻な技術的負��** (巨大ファイル、��環依存、型安全性��如、グローバル状態) が��積しており、機能追加速度の低下・バグ混入リスク増大・オンボーディング困難を��く恐れがある。

**推��アクション**: 今後2-3スプリントを**「リファクタリング・スプリント」**として確保し、Critical/High項目を集中的に解消すること。新機能開発と並行せず、��念期間を設けることを強く推��する。

---

*本レビューは静的解��・コードリーディングベースであり、実行時動作����を含まない。動的解��・負荷テスト結果と��せて判断されたい。*