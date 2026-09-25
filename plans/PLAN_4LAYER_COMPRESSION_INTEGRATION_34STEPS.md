# 4層圧縮パイプライン統合 実装計画書 (34ステップ・リグレッション防止込み)

## 概要
既存の `FourLayerCompressor` を全執筆経路（ContextBuilderAgent, WritingService, オーケストレーション, EasyMode）で活用できるようにする。
各ステップは単一ファイル・単一変更で完結し、低性能LLMでも実装可能な粒度に分割。

---

## フェーズ1: DIコンテナへの登録（基盤）

### Step 1: CompressionConfig プロバイダ追加
**ファイル**: `src/core/container/app.py`
**変更**: `AppContainer` クラス内に `compression_config` プロバイダを追加
```python
compression_config: providers.Singleton = providers.Singleton(
    "src.services.compression.models.CompressionConfig",
)
```
**確認**: `python -c "from src.core.container.app import AppContainer; c = AppContainer(); print(c.compression_config())"`

### Step 2: FourLayerCompressor プロバイダ追加
**ファイル**: `src/core/container/app.py`
**変更**: `AppContainer` クラス内に `compressor` プロバイダを追加（Step 1 依存）
```python
compressor: providers.Singleton = providers.Singleton(
    "src.services.compression.compressor.FourLayerCompressor",
    config=compression_config,
)
```
**確認**: 同様にインスタンス化テスト

### Step 3: ContextBuilderAgent に compressor 注入
**ファイル**: `src/core/container/app.py`
**変更**: 既存の `context_builder_agent` 定義に `compressor=compressor` を追加
```python
context_builder_agent: providers.Singleton = providers.Singleton(
    "src.agents.context_builder_agent.ContextBuilderAgent",
    repo=repo,
    llm=llm,
    style_rag=style_rag,
    rag_prefetch=providers.Self(),
    event_bus=providers.Self(),
    compressor=compressor,  # ← 追加
)
```
**確認**: `python -c "from src.core.container.app import AppContainer; c = AppContainer(); agent = c.context_builder_agent(); print(agent.compressor is not None)"`

---

## フェーズ2: ContextBuilderAgent の受け入れ準備

### Step 4: ContextBuilderAgent.__init__ に compressor パラメータ追加
**ファイル**: `src/agents/context_builder_agent.py`
**変更**: `__init__` シグネチャに `compressor: Any = None` を追加し、`self.compressor = compressor` で保存
```python
def __init__(
    self,
    repo: Any = None,
    llm: Any = None,
    style_rag: Any = None,
    rag_prefetch: Any = None,
    event_bus: Any = None,
    reflective_rag: Any = None,
    compressor: Any = None,  # ← 追加
    social_manager: Any = None,
    age_client: Any = None,
):
    ...
    self.compressor = compressor  # ← 追加
```
**確認**: インスタンス化時に compressor が保存されるか確認

### Step 5: execute() で compressor 取得ロジック確認
**ファイル**: `src/agents/context_builder_agent.py`
**変更**: `execute()` 内の `compressor = ctx.artifacts.get("compressor") or self.compressor` が動作することを確認（既存コードのまま）
**確認**: 単体テスト `tests/unit/test_four_layer_compression.py::test_context_builder_with_compressor` 実行

---

## フェーズ3: WritingService への統合

### Step 6: WritingService.__init__ に compressor パラメータ追加
**ファイル**: `src/services/writing_service.py`
**変更**: コンストラクタに `compressor: Any = None` 追加、保存
```python
def __init__(
    self,
    writing_agent: WritingAgent,
    book_score_calculator: BookScoreCalculator,
    context_builder_agent: ContextBuilderAgent,
    illustration_agent: IllustrationAgent,
    compressor: Any = None,  # ← 追加
    max_retries: int = 3,
    ...
):
    ...
    self.compressor = compressor  # ← 追加
```

### Step 7: WritingService に compressor を context_builder_agent に渡すメソッド追加
**ファイル**: `src/services/writing_service.py`
**変更**: `_build_context_with_compression()` ヘルパーメソッド追加
```python
async def _build_context_with_compression(self, ctx: AgentContext) -> dict:
    """compressor 付きでコンテキスト構築"""
    # ContextBuilderAgent が compressor を使うよう artifacts に設定
    ctx.artifacts["compressor"] = self.compressor
    result = await self.context_builder_agent.execute(ctx)
    return result.artifacts.get("writing_context", {})
```

### Step 8: generate_with_quality_assurance でコンテキスト構築時に compressor 使用
**ファイル**: `src/services/writing_service.py`
**変更**: ループ内で `_build_context_with_compression` を呼ぶ（または `context_builder_agent.execute` 前に artifacts 設定）
```python
# 既存: result = await self.writing_agent.execute(ctx)
# 変更: 事前に compressor を artifacts に入れる
ctx.artifacts["compressor"] = self.compressor
result = await self.writing_agent.execute(ctx)
```

### Step 9: AppContainer で WritingService に compressor 注入
**ファイル**: `src/core/container/app.py`
**変更**: `writing_service` 定義に `compressor=compressor` 追加
```python
writing_service: providers.Singleton = providers.Singleton(
    "src.services.writing_service.WritingService",
    writing_agent=writer,
    book_score_calculator=book_score_calculator,
    context_builder_agent=context_builder_agent,
    illustration_agent=illustration_agent,
    compressor=compressor,  # ← 追加
    max_retries=3,
    score_threshold=70.0,
    backoff_base=2.0,
)
```

---

## フェーズ4: オーケストレーション経路（generation_tasks.py）

### Step 10: _generate_orchestrated の compressor 作成を DI から取得に変更
**ファイル**: `src/backend/tasks/generation_tasks.py`
**変更**: ローカル生成からコンテナ経由に変更
```python
# 変更前:
from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import CompressionConfig
compressor = FourLayerCompressor(config=CompressionConfig())

# 変更後: engine や container から取得
# ※ ここでは簡易的に既存のままでも動くが、将来的に container から取得するようコメント追加
# TODO: AppContainer から compressor を取得するよう変更
```

### Step 11: _generate_orchestrated で compressor を ContextBuilderAgent に渡す確認
**ファイル**: `src/backend/tasks/generation_tasks.py`
**変更**: 既存コード（`dependencies` dict に `"compressor": compressor`）が正しいことを確認のみ
**確認**: コードリーディングで `dependencies["compressor"]` が `ContextBuilderAgent` コンストラクタに渡される経路を確認

---

## フェーズ5: EasyMode / AutoWorkflowPipeline 経路

### Step 12: create_easy_mode_pipeline に compressor パラメータ追加
**ファイル**: `src/services/auto_workflow_pipeline.py`
**変更**: 関数シグネチャに `compressor: Any = None` 追加
```python
def create_easy_mode_pipeline(
    genre: str = "ファンタジー",
    target_episodes: int = 8,
    enable_spice_guard: bool = True,
    max_rewrite_iterations: int = 3,
    target_audit_score: float = 95.0,
    enable_marketing: bool = True,
    compressor: Any = None,  # ← 追加
) -> AutoWorkflowPipeline:
```

### Step 13: ContextBuilderAgent 作成時に compressor 渡す
**ファイル**: `src/services/auto_workflow_pipeline.py`
**変更**: フォールバック分岐内の `ContextBuilderAgent` 生成に `compressor=compressor` 追加
```python
AgentName.CONTEXT_BUILDER: ContextBuilderAgent(
    repo=repo,
    llm=planning_adapter,
    reflective_rag=reflective_rag,
    compressor=compressor,  # ← 追加
    social_manager=social_manager,
).run,
```

### Step 14: generate_chapter_orchestrated_task で compressor 作成・渡す
**ファイル**: `src/backend/tasks/generation_tasks.py`
**変更**: `_generate_orchestrated` 内で compressor 生成し、`create_easy_mode_pipeline` またはフォールバックに渡す
```python
# 既存の compressor 生成コードを流用
compressor = FourLayerCompressor(config=CompressionConfig())
# dependencies に追加済みなら OK、明示的に渡す場合:
orchestrator = Orchestrator.from_manifest(
    ...
    dependencies={..., "compressor": compressor},
)
```

### Step 15: generate_chapter_task (easy mode) でも compressor 使用
**ファイル**: `src/backend/tasks/generation_tasks.py`
**変更**: `_generate` 内で `generate_with_llm` 呼び出し前に compressor を用意し、engine/context に渡す
※ 簡易モードは `generate_with_llm` 経由なので、`src/backend/routers/easy_mode.py` 側で対応が必要（次ステップ）

---

## フェーズ6: EasyMode ルーター対応

### Step 16: easy_mode ルーターで compressor 生成
**ファイル**: `src/backend/routers/easy_mode.py`
**変更**: `generate_with_llm` 内で `FourLayerCompressor` 生成し、生成パイプラインに渡す
```python
from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import CompressionConfig

# 関数内で:
compressor = FourLayerCompressor(config=CompressionConfig())
# WritingAgent または EpisodeWriter に渡す
```

### Step 17: EpisodeWriter / WritingAgent で compressor 受け取り
**ファイル**: `src/agents/writing/episode_writer.py`
**変更**: `__init__` に `compressor: Any = None` 追加、保存
```python
def __init__(self, ..., compressor: Any = None):
    ...
    self.compressor = compressor
```

### Step 18: EpisodeWriter.build_context で compressor 使用
**ファイル**: `src/agents/writing/episode_writer.py`
**変更**: `build_context` で `ContextBuilderAgent.execute` 呼出前に `ctx.artifacts["compressor"] = self.compressor`
```python
async def build_context(self, book_id, branch_id, ep_num, target_word_count, style_tag=None):
    ctx = AgentContext(...)
    ctx.artifacts["compressor"] = self.compressor  # ← 追加
    result = await self.context_builder.execute(ctx)
    return result.artifacts.get("writing_context", {})
```

---

## フェーズ7: WritingGraphManager / LangGraph 経路（上級・オプション）

### Step 19: WritingGraphManager に compressor 参照追加
**ファイル**: `src/backend/workflows/writing_langgraph.py`
**変更**: `__init__` で `self.compressor = getattr(manager, "compressor", None)`
```python
def __init__(self, manager):
    self.manager = manager
    self.compressor = getattr(manager, "compressor", None)
    ...
```

### Step 20: node_prepare で compressor 使用（コンテキスト圧縮）
**ファイル**: `src/backend/workflows/writing_langgraph.py`
**変更**: `node_prepare` で `gen_ctx` 作成時に圧縮実行
```python
# _phase_prepare_context 呼出後に圧縮適用
if self.compressor and gen_ctx:
    # gen_ctx から raw_text, entities, relations を抽出して圧縮
    compressed = self.compressor.compress(
        raw_text=gen_ctx.raw_text,
        entities=gen_ctx.entities,
        relations=gen_ctx.relations,
        scene_type=gen_ctx.scene_type,
    )
    gen_ctx.compressed_context = compressed.final_context_text
```
※ 実装は `_phase_prepare_context` 側で行う方が自然。このステップは「呼出し側で圧縮結果を受け取る」だけに留める。

---

## フェーズ8: 既存コードのクリーンアップ・無効化解除

### Step 21: engine_context.py の compressor=None を削除
**ファイル**: `src/backend/engine_context.py`
**変更**: `ContextManager._build_full_writing_context_internal` 呼出箇所（4箇所）で `compressor=None` を渡さない（デフォルトで DI から取得されるようにする）
```python
# 変更前: compressor=None,
# 変更後: compressor=compressor,  # 外から渡される想定
```
※ `ContextManager` は deprecated なので、委譲先 `ContextBuilderAgent` が持つ compressor が使われるよう委譲ロジック確認

### Step 22: 旧 ContextManager の委譲で compressor 伝播確認
**ファイル**: `src/backend/engine_context.py`
**変更**: `_get_delegate()` で生成する `ContextBuilderAgent` に `compressor=self.compressor` 渡す（`ContextManager` に `compressor` 属性を持たせる）
```python
def __init__(self, repo, compressor=None):  # compressor 追加
    self.compressor = compressor
    ...
def _get_delegate(self):
    if self._delegate_agent is None:
        self._delegate_agent = ContextBuilderAgent(repo=self.repo, compressor=self.compressor)
```

---

## フェーズ9: リグレッション防止テスト・検証（拡張）

### Step 23: 統合テスト追加 - 全経路圧縮動作確認
**ファイル**: `tests/integration/test_compression_integration.py` (新規)
**内容**: 
- オーケストレーション経路で圧縮実行・キャッシュヒット確認
- EasyMode 経路で圧縮実行確認
- WritingService 経路で圧縮実行確認
- 圧縮統計（reduction_ratio, token_count）が artifacts に含まれること確認

### Step 24: 単体テスト追加 - DIコンテナ注入確認
**ファイル**: `tests/unit/test_compression_di_injection.py` (新規)
**内容**:
- `AppContainer.compressor()` が `FourLayerCompressor` インスタンスを返すこと
- `AppContainer.context_builder_agent().compressor` が同一インスタンスであること（Singleton確認）
- `AppContainer.writing_service().compressor` が同一インスタンスであること
- `CompressionConfig` が YAML 設定値で正しく初期化されること

### Step 25: 単体テスト追加 - ContextBuilderAgent 圧縮統合
**ファイル**: `tests/unit/test_context_builder_compression.py` (新規)
**内容**:
- `compressor=None` 時は圧縮スキップ（従来互換）
- `compressor` あり時は `compressed_context`, `compression_stats` が返る
- `ProtectedContext`（active_characters, foreshadowing_ids）が圧縮に反映されること
- `SceneFlowHistory` によるシーン検出が機能すること
- キャッシュヒット時 `from_cache=True`, `elapsed_ms < 5ms` 程度

### Step 26: 単体テスト追加 - WritingService 圧縮経路
**ファイル**: `tests/unit/test_writing_service_compression.py` (新規)
**内容**:
- `generate_with_quality_assurance` 実行時に `ctx.artifacts["compressor"]` が設定されること
- 再生成ループ（retry）でも compressor が毎回渡されること
- `AntiAILoopController` 実行後も圧縮コンテキストが保持されること

### Step 27: 単体テスト追加 - EasyMode/EpisodeWriter 経路
**ファイル**: `tests/unit/test_easymode_compression.py` (新規)
**内容**:
- `create_easy_mode_pipeline(compressor=...)` で ContextBuilderAgent に渡ること
- `EpisodeWriter.build_context()` で `ctx.artifacts["compressor"]` 設定されること
- `generate_with_llm` (easy_mode) 経由で圧縮実行されること

### Step 28: コントラクトテスト - 圧縮結果スキーマ検証
**ファイル**: `tests/contract/test_compression_output_schema.py` (新規)
**内容**:
- `CompressedContextResult` の必須フィールド存在確認:
  - `final_context_text: str` (非空)
  - `final_token_count: int` (> 0, <= max_tokens)
  - `overall_reduction_ratio: float` (0.0-1.0)
  - `layer1..4` 各層の出力オブジェクト存在
  - `metrics: CompressionQualityMetrics` 存在
  - `from_cache: bool`, `elapsed_ms: float`
- シーンタイプ別（combat/daily/psychological/political）で必須カテゴリ保持確認

### Step 29: プロパティベーステスト - 圧縮不変条件
**ファイル**: `tests/property/test_compression_invariants.py` (新規, hypothesis使用)
**内容**:
- 入力テキスト長 > 出力トークン数（圧縮されている）
- 同一入力・同一パラメータでキャッシュヒット時出力完全一致
- `max_tokens` 増加時 `final_token_count` 単調非減少
- `preserve_categories` 指定エンティティが出力に含まれる
- 空文字列入力でエラーにならず空結果返却

### Step 30: パフォーマンス回帰テスト
**ファイル**: `tests/performance/test_compression_benchmark.py` (新規)
**内容**:
- 10KB〜500KB テキストで `elapsed_ms` 計測
- キャッシュミス初回: < 2000ms (CI環境調整)
- キャッシュヒット2回目: < 50ms
- メモリ使用量: < 500MB
- ベンチマーク結果を `tests/benchmarks/compression_baseline.json` に保存し、CI で閾値比較

### Step 31: E2Eテスト - 実書籍生成フロー
**ファイル**: `tests/e2e/test_full_novel_with_compression.py` (新規)
**内容**:
- 実DB・実LLMモックで 3話生成
- 全話で `writing_context["compression_stats"]` 存在確認
- 圧縮率 50-80% 範囲内
- 伏線・キャラクター名が圧縮後も保持（`metrics.entity_retention_rate >= 0.8`）
- 生成完了まで例外なし

### Step 32: 既存テスト全実行・回帰確認（拡張）
**コマンド**: 
```bash
# 圧縮関連既存テスト
pytest tests/unit/test_four_layer_compression.py -v
pytest tests/unit/test_compression_pipeline.py -v
pytest tests/unit/test_compression_consistency_metrics.py -v
pytest tests/integration/test_semantic_rag_compression_e2e.py -v

# 影響範囲テスト
pytest tests/unit/services/test_auto_pipeline_service.py -v
pytest tests/unit/test_context_builder_agent.py -v  # 存在すれば
pytest tests/unit/services/test_writing_service.py -v  # 存在すれば
pytest tests/unit/agents/test_episode_writer.py -v  # 存在すれば

# 新規追加テスト
pytest tests/unit/test_compression_di_injection.py -v
pytest tests/unit/test_context_builder_compression.py -v
pytest tests/unit/test_writing_service_compression.py -v
pytest tests/unit/test_easymode_compression.py -v
pytest tests/contract/test_compression_output_schema.py -v
pytest tests/property/test_compression_invariants.py -v
pytest tests/performance/test_compression_benchmark.py -v
pytest tests/e2e/test_full_novel_with_compression.py -v
pytest tests/integration/test_compression_integration.py -v
```
**確認**: 全テストパス、圧縮関連メトリクス正常出力、カバレッジ低下なし

### Step 33: CI/CD パイプライン統合
**ファイル**: `.github/workflows/ci.yml` (または同等)
**変更**: 
- `compression` ジョブ追加（ベンチマーク比較含む）
- `contract` ジョブ追加（スキーマ検証）
- `property` ジョブ追加（hypothesis実行、失敗時詳細出力）
- カバレッジ閾値: `compression` モジュール 80% 以上
- 失敗時: PR チェックでブロック、Slack/Discord 通知

### Step 34: ドキュメント・運用ガイド更新
**ファイル**: 
- `docs/compression_integration.md` (新規): 統合アーキテクチャ図、設定パラメータ説明、トラブルシューティング
- `config/context_compression.yaml` コメント充実化
- `CHANGELOG.md` に 4層圧縮統合エントリ追加

---

## 実装順序の依存関係

```
Step 1 → Step 2 → Step 3 → Step 4 → Step 5
                              ↓
Step 6 → Step 7 → Step 8 → Step 9
                              ↓
Step 10 → Step 11
                              ↓
Step 12 → Step 13 → Step 14 → Step 15 → Step 16 → Step 17 → Step 18
                              ↓
Step 19 → Step 20 (オプション)
                              ↓
Step 21 → Step 22
                              ↓
Step 23 → Step 24 → Step 25 → Step 26 → Step 27 → Step 28 → Step 29 → Step 30 → Step 31 → Step 32 → Step 33 → Step 34
```

---

## 各ステップの目安工数
- **Steps 1-5**: 約30分（DI設定・Agent修正）
- **Steps 6-9**: 約30分（WritingService統合）
- **Steps 10-11**: 約15分（オーケストレーション確認）
- **Steps 12-18**: 約45分（EasyMode/AutoWorkflow統合）
- **Steps 19-20**: 約30分（LangGraph・オプション）
- **Steps 21-22**: 約15分（クリーンアップ）
- **Steps 23-27**: 約60分（統合・単体テスト追加）
- **Steps 28-30**: 約45分（コントラクト・プロパティ・性能テスト）
- **Steps 31**: 約30分（E2Eテスト）
- **Steps 32**: 約30分（全テスト実行・回帰確認）
- **Steps 33**: 約15分（CI統合）
- **Steps 34**: 約15分（ドキュメント更新）

**合計目安: 約5-6時間**

---

## 各ステップの目安工数
- **Steps 1-5**: 約30分（DI設定・Agent修正）
- **Steps 6-9**: 約30分（WritingService統合）
- **Steps 10-11**: 約15分（オーケストレーション確認）
- **Steps 12-18**: 約45分（EasyMode/AutoWorkflow統合）
- **Steps 19-20**: 約30分（LangGraph・オプション）
- **Steps 21-22**: 約15分（クリーンアップ）
- **Steps 23-24**: 約30分（テスト・検証）

**合計目安: 約3-4時間**

---

## 完了基準
1. 全執筆経路で `FourLayerCompressor` が実行される
2. `compressed_context` と `compression_stats` が `writing_context` に含まれる
3. キャッシュヒット時 `from_cache=True` で高速化される（< 50ms）
4. 既存テスト全パス、新規統合・単体・コントラクト・プロパティ・E2Eテスト全パス
5. 圧縮率（reduction_ratio）が 50-80% 程度で安定
6. 必須エンティティ保持率 ≥ 80%、必須カテゴリ保持率 ≥ 80%（全シーンタイプ）
7. CI パイプラインで圧縮ベンチマーク・スキーマ検証が自動実行される
8. カバレッジ: `src/services/compression/` 80% 以上、影響モジュール低下なし