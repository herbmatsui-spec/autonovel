# パイプライン統合 実装計画書
**ベース**: `AutoWorkflowPipeline` (src/services/auto_workflow_pipeline.py)
**目標**: FullAutoWorkflow / EasyModePipeline を統合し、単一パイプラインに集約

---

## 概要: 4フェーズ 32ステップ

| フェーズ | 目的 | ステップ数 |
|---|---|---|
| Phase 1 | 共通基盤・データモデル統合 | 1-8 |
| Phase 2 | 既存Stepの整理・新Step実装 | 9-20 |
| Phase 3 | エントリーポイント委譲・動作確認 | 21-28 |
| Phase 4 | 旧コード削除・最終検証 | 29-32 |

---

## Phase 1: 共通基盤・データモデル統合 (Steps 1-8)

### Step 1: 統合設定モデル作成
**ファイル**: `src/services/unified_pipeline_config.py` (新規)
```python
# PipelineConfig + WorkflowContext の統合モデル
# - genre, keywords, archetype_key, target_eps, word_count 等
# - enable_spice_guard, max_rewrite_iterations, target_audit_score (EasyMode由来)
# - enable_illustration, illustration_settings (FullAuto由来)
# - user_prompt, concept, tone_vibe 等
```

**確認**: `python -c "from src.services.unified_pipeline_config import UnifiedPipelineConfig; print('OK')"`

---

### Step 2: 進捗コールバック統一インターフェース
**ファイル**: `src/services/progress_reporter.py` (新規)
```python
# 既存の2形式を吸収するアダプタ
# - reporter.update_progress(step, total, msg, sub_msg)  <- FullAuto
# - callback(stage, current, total)                     <- EasyMode
# 統一: ProgressReporterProtocol / ProgressCallbackProtocol
```

**確認**: 既存の `StatusReporter` との互換性テスト

---

### Step 3: WorkflowContext に EasyMode フィールド追加
**ファイル**: `src/services/auto_workflow_pipeline.py`
- `enable_spice_guard: bool = True`
- `max_rewrite_iterations: int = 3`
- `target_audit_score: float = 95.0`
- `spice_elements: list = []` (Step間受け渡し用)
- `preset_name: str = ""` (ジャンルプリセット名)

**確認**: `python -c "from src.services.auto_workflow_pipeline import WorkflowContext; ctx = WorkflowContext(...); print(ctx.enable_spice_guard)"`

---

### Step 4: FullAutoWorkflowResult に EasyMode 結果フィールド追加
**ファイル**: `src/models.py` (既存)
```python
# 追加フィールド
average_audit_score: float = 0.0
episodes_detail: list[dict] = []  # EasyModeの episodes 情報
spice_guard_enabled: bool = False
```

**確認**: 既存テストが通ること (`pytest tests/ -k "full_auto" -v`)

---

### Step 5: ジャンルプリセットローダー統合
**ファイル**: `src/services/preset_loader.py` (新規)
```python
# EasyModePipeline.load_preset() を共通化
# FullAuto の STORY_ARCHETYPES とマッピング
def load_preset_for_pipeline(genre: str, archetype_key: str) -> dict:
    # preset + archetype settings の合成
```

**確認**: `python -c "from src.services.preset_loader import load_preset_for_pipeline; print(load_preset_for_pipeline('ファンタジー', '王道ざまぁ'))"`

---

### Step 6: 共通ユーティリティ整理
**ファイル**: `src/backend/workflows/_shared_ops.py` (既存)
- `run_pipeline_with_retry` を `AutoWorkflowPipeline` 用に汎用化
- `WriteStep` から呼び出せる形にリファクタ
- リトライロジックをパラメータ化 (`max_retries`, `is_easy_mode`)

**確認**: 既存の `FullAutoWorkflow` テストが通ること

---

### Step 7: SpiceGuard 統合ラッパー作成
**ファイル**: `src/services/spice_guard_adapter.py` (新規)
```python
# EasyModePipeline._spice_guard を Step から呼べる形に
class SpiceGuardAdapter:
    def extract_spice(self, text: str, genre: str) -> list[SpiceElement]
    def inject_markers(self, text: str, elements: list[SpiceElement]) -> str
    def clean_markers(self, text: str) -> str
    def build_rewrite_prompt(self, content: str, improvements: list[str], elements: list[SpiceElement]) -> str
```

**確認**: `python -c "from src.services.spice_guard_adapter import SpiceGuardAdapter; a = SpiceGuardAdapter(); print(a.extract_spice('テスト', 'ファンタジー'))"`

---

### Step 8: 監査エンジン共通インターフェース
**ファイル**: `src/services/audit_adapter.py` (新規)
```python
# EasyModePipeline._audit_episode + FullAuto の plan_auditor を統一
class AuditAdapter:
    async def audit_episode(self, content: str, context: dict) -> dict  # score, passed, improvements
    async def audit_bible(self, bible: dict, reporter) -> bool
```

**確認**: 両方の監査パスで動作すること

---

## Phase 2: 既存Step整理・新Step実装 (Steps 9-20)

### Step 9: InferenceStep - 現状維持・テスト追加
**ファイル**: `src/services/auto_workflow_pipeline.py` (既存 `InferenceStep`)
- 変更なし（既に完成度高い）
- 単体テスト作成: `tests/test_inference_step.py`

**確認**: `pytest tests/test_inference_step.py -v`

---

### Step 10: PlanStep - カタルシス分析統合
**ファイル**: `src/services/auto_workflow_pipeline.py` (既存 `PlanStep`)
- `FullAutoWorkflow` のカタルシス分析ロジック (56-94行) を移植
- `ctx.easy_parameters["catharsis_pattern"]` に格納
- `ctx.easy_parameters["catharsis_positions"]` も設定

**確認**: カタルシス情報が context に残ること

---

### Step 11: PlanStep - プリセット適用対応
**ファイル**: `src/services/auto_workflow_pipeline.py` (既存 `PlanStep`)
- `load_preset_for_pipeline(ctx.genre, ctx.archetype_key)` を呼び出し
- `style_key`, `cheat_scale` 等をプリセットから上書き可能に
- 既存 `STORY_ARCHETYPES` をフォールバックとして維持

**確認**: ジャンル指定でプリセット適用されること

---

### Step 12: WriteStep - リトライロジック共通化
**ファイル**: `src/services/auto_workflow_pipeline.py` (既存 `WriteStep`)
- `_shared_ops.run_pipeline_with_retry` を使用するよう変更
- `ctx.max_retries` (新フィールド) を参照
- `is_easy_mode` フラグを context から取得

**確認**: 失敗エピソードがリトライされること

---

### Step 13: CatharsisAnalysisStep 新規作成
**ファイル**: `src/services/pipeline_steps.py` (新規)
```python
class CatharsisAnalysisStep(WorkflowStep):
    """FullAutoWorkflow のカタルシス分析を Step 化"""
    async def execute(self, ctx, engine, reporter):
        # プロット取得 -> WavePatternAnalyzer -> ctx.easy_parameters に格納
        # 失敗しても警告のみで継続 (FullAuto と同じ挙動)
```

**確認**: Step 単体で実行可能

---

### Step 14: AuditRewriteStep 新規作成 (核心)
**ファイル**: `src/services/pipeline_steps.py` (新規)
```python
class AuditRewriteStep(WorkflowStep):
    """EasyMode の「監査→リライト→再監査 (max_rewrite_iterations)」を Step 化"""
    async def execute(self, ctx, engine, reporter):
        if not ctx.enable_spice_guard:
            return True
        for ep_num in range(1, ctx.target_eps + 1):
            # 1. エピソード本文取得
            # 2. 監査 (audit_adapter)
            # 3. スコア < target_audit_score ならリライトループ
            #    - SpiceGuard で尖り抽出・マーカー注入
            #    - 改善指示でリライト
            #    - 再監査
            # 4. 最終結果を DB 更新
        return True
```

**実装ヒント**: `EasyModePipeline._generate_episode` (221-276行) を参考に分解

**確認**: 1話分の監査リライトが動くこと

---

### Step 15: PackageStep - 拡張
**ファイル**: `src/services/auto_workflow_pipeline.py` (既存 `PackageStep`)
- `ctx.average_audit_score`, `ctx.episodes_detail` を計算して結果に含める
- `ctx.zip_data` は None のまま (フロントエンド生成維持)

**確認**: 結果オブジェクトに全フィールドが入ること

---

### Step 16: IllustrationStep 新規作成
**ファイル**: `src/services/pipeline_steps.py` (新規)
```python
class IllustrationStep(WorkflowStep):
    """FullAutoWorkflow の挿絵生成を Step 化"""
    async def execute(self, ctx, engine, reporter):
        if not ctx.illustration_settings or not ctx.illustration_settings.get("enableIllustration"):
            return True
        # IllustrationWorkflow 呼び出し
        # 結果を ctx.illustrations に格納
```

**確認**: 挿絵設定ありで実行され、なしでスキップされること

---

### Step 17: MarketingStep 新規作成 (将来拡張用・最小実装)
**ファイル**: `src/services/pipeline_steps.py` (新規)
```python
class MarketingStep(WorkflowStep):
    """タイトル・あらすじ・キャッチコピー生成 (EasyMode の _finalize_series 相当)"""
    async def execute(self, ctx, engine, reporter):
        # プリセットの marketing から生成
        # ctx.title, ctx.concept, ctx.catchphrase, ctx.synopsis 設定
```

**確認**: メタデータが生成されること

---

### Step 18: パイプライン構築関数作成
**ファイル**: `src/services/auto_workflow_pipeline.py` (追記)
```python
def create_full_auto_pipeline(enable_spice_guard: bool = True, 
                               enable_illustration: bool = False,
                               enable_marketing: bool = True) -> AutoWorkflowPipeline:
    steps = [
        InferenceStep(),
        PlanStep(),
        CatharsisAnalysisStep(),      # NEW
        WriteStep(),
        AuditRewriteStep(),           # NEW (spice_guard 有効時のみ)
        IllustrationStep(),           # NEW (illustration 有効時のみ)
        MarketingStep(),              # NEW
        PackageStep(),
    ]
    # 条件付きステップ除外ロジック
    return AutoWorkflowPipeline(steps)
```

**確認**: `python -c "from src.services.auto_workflow_pipeline import create_full_auto_pipeline; p = create_full_auto_pipeline(); print([type(s).__name__ for s in p.steps])"`

---

### Step 19: EasyMode 用パイプライン構築関数
**ファイル**: `src/services/auto_workflow_pipeline.py` (追記)
```python
def create_easy_mode_pipeline(genre: str, target_episodes: int = 8, **kwargs) -> AutoWorkflowPipeline:
    # genre から archetype_key 推定 or デフォルト
    # プリセット読み込み
    # SpiceGuard 有効固定
    return create_full_auto_pipeline(
        enable_spice_guard=True,
        enable_illustration=False,
        enable_marketing=True,
    )
```

**確認**: `python -c "from src.services.auto_workflow_pipeline import create_easy_mode_pipeline; p = create_easy_mode_pipeline('ファンタジー'); print('OK')"`

---

### Step 20: 統合パイプライン統合テスト
**ファイル**: `tests/test_unified_pipeline.py` (新規)
```python
# モックエンジンで全Step通しテスト
# - InferenceStep -> PlanStep -> ... -> PackageStep
# - Context の流れ確認
# - エラーハンドリング (step が False 返却時)
```

**確認**: `pytest tests/test_unified_pipeline.py -v`

---

## Phase 3: エントリーポイント委譲・動作確認 (Steps 21-28)

### Step 21: FullAutoWorkflow → 統合パイプライン委譲
**ファイル**: `src/backend/workflows/full_auto_workflow.py`
```python
# execute() 内容を置換
async def execute(self, reporter, **kwargs):
    from src.services.auto_workflow_pipeline import (
        create_full_auto_pipeline, WorkflowContext, UltimateHegemonyEngine
    )
    ctx = WorkflowContext(**kwargs)  # マッピング必要
    pipeline = create_full_auto_pipeline(
        enable_spice_guard=kwargs.get("enable_spice_guard", False),
        enable_illustration=bool(kwargs.get("illustration_settings", {}).get("enableIllustration")),
    )
    result = await pipeline.execute(ctx, self.engine, reporter)
    # 結果マッピング: FullAutoWorkflowResult -> dict
    return result.to_dict()
```

**確認**: 既存の FullAutoWorkflow テストが全通過

---

### Step 22: EasyModeWorkflow → 統合パイプライン委譲
**ファイル**: `src/backend/workflows/easy_mode_workflow.py`
```python
async def execute(self, reporter, **kwargs):
    from src.services.auto_workflow_pipeline import (
        create_easy_mode_pipeline, WorkflowContext
    )
    # kwargs -> WorkflowContext 変換
    genre = kwargs.get("genre", "ファンタジー")
    pipeline = create_easy_mode_pipeline(genre, kwargs.get("target_episodes", 10))
    # progress_callback アダプタ設定
    ctx = WorkflowContext(
        genre=genre,
        target_eps=kwargs.get("target_episodes", 10),
        word_count=kwargs.get("words_per_episode", 2000),
        enable_spice_guard=kwargs.get("enable_audit", True),
        max_rewrite_iterations=kwargs.get("max_rewrites", 2),
        target_audit_score=95.0,
        # ... 他フィールドマッピング
    )
    result = await pipeline.execute(ctx, self.engine, reporter)
    # SeriesResult -> 既存戻り値 dict に変換
    return self._map_result(result)
```

**確認**: 既存の EasyModeWorkflow テストが全通過

---

### Step 23: パラメータマッピングユーティリティ作成
**ファイル**: `src/services/pipeline_param_mapper.py` (新規)
```python
# FullAuto 用 kwargs -> WorkflowContext
# EasyMode 用 kwargs -> WorkflowContext
# 双方向変換関数
```

**確認**: 両ワークフローで正しくマッピングされること

---

### Step 24: 進捗コールバックアダプタ実装
**ファイル**: `src/services/progress_reporter.py` (Step 2 で作成したものに追加)
```python
# FullAuto: reporter.update_progress(step, total, msg, sub_msg)
# EasyMode: callback(stage, current, total)
# 統合パイプライン内部: reporter.report() + reporter.update_progress()
# アダプタで吸収
```

**確認**: 両UIで進捗が正しく表示されること

---

### Step 25: API エンドポイント動作確認
**対象**: 
- `POST /api/full-auto/start` (FullAutoWorkflow 使用)
- `POST /api/easy-mode/start` (EasyModeWorkflow 使用)

**確認**: 
```bash
# 手動テストまたは統合テスト
curl -X POST /api/full-auto/start -d '{"genre":"ファンタジー",...}'
curl -X POST /api/easy-mode/start -d '{"genre":"ファンタジー",...}'
```

---

### Step 26: CLI エントリーポイント動作確認
**対象**: `python -m src.cli full-auto ...` / `python -m src.cli easy-mode ...`

**確認**: 両コマンドで正常完了

---

### Step 27: 非機能要件テスト
- **キャンセル処理**: `reporter.state.should_stop()` が各 Step で効くこと
- **エラー伝播**: Step 内例外がパイプラインで catch され、適切な status で返ること
- **リソースリーク**: 大量エピソード生成でメモリリークしないこと

**確認**: 負荷テストスクリプト実行

---

### Step 28: パフォーマンス比較・ベンチマーク
**指標**: 
- 実行時間 (統合前後)
- メモリ使用量
- API レイテンシ

**確認**: ベンチマーク結果を記録、劣化していないこと

---

## Phase 4: 旧コード削除・最終検証 (Steps 29-32)

### Step 29: 全テストスイート実行・修正
```bash
pytest tests/ -v --tb=short
# 失敗テストを全て修正
```

**確認**: 全テストパス (0 failures)

---

### Step 30: FullAutoWorkflow 旧実装削除
**削除ファイル**:
- `src/backend/workflows/full_auto_workflow.py`
- 参照している import の整理

**確認**: `grep -r "FullAutoWorkflow" src/ --include="*.py"` で参照残っていないこと

---

### Step 31: EasyModePipeline 旧実装削除
**削除ファイル**:
- `src/easy_mode/pipeline.py`
- `src/easy_mode/spice_guard.py` (adapter に移植済みなら)
- `src/easy_mode/__init__.py` (空なら)
- `src/backend/workflows/easy_mode_workflow.py`

**確認**: `grep -r "EasyModePipeline\|EasyModeWorkflow" src/ --include="*.py"` で参照残っていないこと

---

### Step 32: 最終統合テスト・ドキュメント更新
**実施項目**:
1. エンドツーエンドテスト (全自動・かんたんモード両方)
2. `AGENTS.md` / `CLAUDE.md` 等のアーキテクチャ文書更新
3. `CHANGELOG.md` 記録
4. 不要になった import・未使用コードの最終掃除

**確認**: 
- 本番相当環境でデプロイテスト
- ユーザー受け入れテスト (UAT) シナリオ全通過

---

## 実装時の重要な注意点

### 🔴 破壊的変更を避ける鉄則
1. **インターフェース維持**: `FullAutoWorkflow.execute()` / `EasyModeWorkflow.execute()` のシグネチャ・戻り値は**絶対に変更しない**
2. **段階的委譲**: 旧ロジックをコメントアウトせず、新パイプライン呼び出しに**置き換える** (ロールバック容易に)
3. **フィーチャーフラグ**: 環境変数 `USE_UNIFIED_PIPELINE=1` で新旧切替可能にしておく (Phase 3 まで)

### 🟡 LLM 実装しやすさのための工夫
- **各 Step 単体でテスト可能** にする (依存注入・モック容易)
- **型ヒント完全装備** (mypy で検証可能)
- **ログ出力統一** (`logger.info(f"[{Step名}] ...")` 形式)
- **ドキュメンテーション文字列** を各 class/method に必須

### 🟢 並行作業可能なステップ
| 並行グループ | Steps |
|---|---|
| データモデル系 | 1, 3, 4, 5 |
| アダプター系 | 2, 7, 8 |
| Step実装系 | 13, 14, 16, 17 |
| 委譲系 | 21, 22 |

---

## 完了判定基準

| 基準 | 目標 |
|---|---|
| テストカバレッジ | 統合パイプライン関連 80% 以上 |
| 回帰バグ | 0 件 (既存全テストパス) |
| 実行時間 | 統合前 ±10% 以内 |
| コード行数 | 旧3ファイル合計(~1070行) → 新実装 < 800行 (共通化効果) |

---

## 参照ファイル一覧 (実装時によく読む)

| ファイル | 役割 |
|---|---|
| `src/services/auto_workflow_pipeline.py` | **ベースパイプライン** (最重要) |
| `src/backend/workflows/full_auto_workflow.py` | 移植元: カタルシス分析・挿絵・リトライ |
| `src/easy_mode/pipeline.py` | 移植元: SpiceGuard・監査リライト・プリセット |
| `src/backend/workflows/_shared_ops.py` | 共通ユーティリティ (リトライ等) |
| `src/easy_mode/spice_guard.py` | SpiceGuard 実体 |
| `config/constants.py` | EP_CLIMAX, EP_FINAL 等 |
| `src/models.py` | FullAutoWorkflowResult 定義 |

---

**以上。この計画通りに Step 1 から順に実装を進めてください。各 Step 完了時に「確認」コマンドを実行し、成功してから次へ進むことを推奨します。**