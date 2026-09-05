# 官能 (Erotic) 機能 完全再活性化 実装計画書

> **対象**: `E:\sssssss\autonovel\src` 配下の小説自動生成パイプライン
> **目的**: 「埋もれている」官能機能を、配線・デッドコード除去・YAMLプリセット統合・UI露出まで含めて完全復活させる
> **スコープ**: 24の小さなステップに分割。各ステップは単独でコミット可能な粒度。

---

## 0. 現状整理 (問題提起)

精査の結果、以下の **6 つの埋没ポイント** が判明した:

| # | 問題 | 影響 |
|---|------|------|
| P-1 | `PlanStep` が `easy_parameters["enable_erotic"]` を読むが、誰も書かない → 常に `False` | プランナーが官能前提の構成を組まない |
| P-2 | `EroticEnhancer.enhance_erotic_content` のゲート `context["nsfw_enabled"]` がセットされない | LLM再生成・メタファーフィルタ・アフターグロウ評価が動かない |
| P-3 | `preset["erotic"]` (YAML) は読まれるが唯一の使用者 `media_mix.py:464` の `self.erotic_rules` は代入後未参照 | 9ジャンルの `erotic_rules_*.yaml` が完全に死蔵 |
| P-4 | `EroticSpecialist.build_scene_prompt` が YAML を読まずに `config.erotic_*` Python モジュールから語彙を引く | ジャンル毎チューニングが反映されない |
| P-5 | Streamlit の NSFW トグル (`cfg_enable_nsfw`) が `cfg.enable_nsfw` に書かれるが、書き込みパイプラインに伝播しない | UI操作が反映されない (dead toggle) |
| P-6 | 死コード: `EroticIntensity` VO / `EroticDensityController` (実体は `audit_service.get_erotic_advice` が呼ばれない) / `EroticDiversityScore` (テストのみ) / `RefineEroticWorkflow` (登録のみ) / `media_mix.erotic_rules` フィールド | 保守コスト増、誤った参照を誘発 |
| P-7 | 用語の断片化: `enable_erotic` / `enable_nsfw` / `nsfw_enabled` / `erotic_intensity` (int) / `EroticIntensity` (VO) が混在 | ゲート条件が5箇所に散在 |
| P-8 | `_writing.py` と `writing.py` の並走、2系統の `EpisodeWriter` | どちらが実体か不明 |

**根本原因**: 配線点 (`PlanStep` → `WriteStep` → `EpisodeWriter.write` → `EroticEnhancer`) の **いずれの段でも値が届かない**。UI→Context→Enhancer の3層で分断されている。

---

## 全体アーキテクチャ (改修後)

```
┌─────────────────────────────────────────────────────────────────┐
│ Streamlit UI (00_Settings.py)                                   │
│   ├── st.toggle("NSFW/官能コンテンツ許可", cfg_enable_nsfw)        │
│   └── st.slider("官能強度 (1-5)", cfg_erotic_intensity)           │
│           ↓ ConfigState.get("enable_nsfw"/"erotic_intensity")    │
└─────────────────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ pipeline_param_mapper.py  ←  UI 値を WorkflowContext に転写     │
│   ctx.easy_parameters["enable_erotic"]  = ui_enable_nsfw        │
│   ctx.easy_parameters["erotic_intensity"] = ui_erotic_intensity  │
│   ctx.is_nsfw_enabled  = ui_enable_nsfw   (新規フィールド)       │
└─────────────────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PlanStep (pipeline_steps.py)                                    │
│   enable_erotic=ctx.easy_parameters.get("enable_erotic")        │
│   erotic_intensity=ctx.easy_parameters.get("erotic_intensity")  │
└─────────────────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ WriteStep → EpisodeWriter.write → EroticEnhancer                │
│   context["nsfw_enabled"] = ctx.is_nsfw_enabled   ← ここで注入  │
│   context["erotic_intensity"] = ctx.easy_parameters["..."]      │
│   context["erotic_rules_yaml"] = preset["erotic"]  ← YAML を運ぶ │
└─────────────────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ EroticSpecialist (engine/prompts/erotic_specialist.py)          │
│   build_scene_prompt() が YAML を読み込んで反映                 │
└─────────────────────────────────────────────────────────────────┘
```

**重要な原則**:
1. **真実の源 (single source of truth)**: `enable_erotic` (bool) と `erotic_intensity` (1-5) の **2つのキー** に集約。これ以外の名前 (`enable_nsfw`, `nsfw_enabled`) は薄いラッパに過ぎない。
2. **YAML プリセット優先**: `EroticSpecialist` は `context["erotic_rules_yaml"]` があればそれを最優先、無ければ `config.erotic_*` のデフォルト。
3. **デッドコード即削除**: 使われていないものを残すと、また埋もれる。

---

## ステップ一覧 (24)

| #  | カテゴリ | タイトル | 主ファイル |
|----|---------|---------|----------|
|  1 | 準備 | テストハーネスとフィクスチャ整備 | `tests/` |
|  2 | 用語統一 | `EroticGate` 値オブジェクト新設 + 用語集約 | `src/domain/value_objects/erotic_gate.py` |
|  3 | UI 露出 | Streamlit に官能強度スライダ追加 | `streamlit_app/pages/00_Settings.py` |
|  4 | UI 状態 | `ConfigState` に `erotic_intensity` デフォルト | `streamlit_app/state.py` |
|  5 | 配線 (UI→Context) | `pipeline_param_mapper` が UI 値を Context に転写 | `src/services/pipeline_param_mapper.py` |
|  6 | Context 拡張 | `WorkflowContext` に `is_nsfw_enabled` フィールド追加 | `src/services/pipeline_base.py` |
|  7 | PlanStep 修正 | 初期化フェーズで `enable_erotic` を必ず書く | `src/services/pipeline_steps.py` |
|  8 | WriteStep 配線 | `WriteStep` が context に `nsfw_enabled` / `erotic_intensity` を注入 | `src/services/pipeline_steps.py` |
|  9 | YAML 注入 | `WriteStep` が `preset["erotic"]` を context["erotic_rules_yaml"] に積む | `src/services/pipeline_steps.py` |
| 10 | Enhancer ゲート統一 | `EroticEnhancer` のゲート判定を `EroticGate` に委譲 | `src/agents/erotic_enhancer.py` |
| 11 | Specialist YAML 統合 | `EroticSpecialist` が YAML を読んでプロンプトに反映 | `src/engine/prompts/erotic_specialist.py` |
| 12 | dead field 削除 | `media_mix.py:464` の `self.erotic_rules` 削除 | `src/easy_mode/phase3/media_mix.py` |
| 13 | dead VO 削除 | `EroticIntensity` 値オブジェクト削除 | `src/domain/value_objects/erotic_intensity.py` |
| 14 | dead service 削除 | `EroticDensityController` / `EroticDiversityScore` 整理 | `src/services/erotic_density_controller.py` 等 |
| 15 | dead workflow 整理 | `RefineEroticWorkflow` を「明示オプトイン」化 | `src/backend/workflows/refine_erotic_workflow.py` |
| 16 | 重複 writer 統合 | `_writing.py` と `writing.py` を `agent.py` 系統に統一 | `src/agents/writing/` |
| 17 | SpiceGuard の名称整理 | "spice" を "narrative_edge_guard" に改名 (任意) | `src/easy_mode/spice_guard.py` 等 |
| 18 | Planner 拡張 | `create_hegemony_plan` が `enable_erotic`/`erotic_intensity` を反映 | `src/backend/planner.py` |
| 19 | Hook/Plot 連動 | 官能有効時にフック・プロットへ `romance_track` を追加 | `src/services/next_beats_service.py` 等 |
| 20 | 監査連動 | 官能有効率外時の `target_audit_score` を引き下げ | `src/services/pipeline_steps.py` |
| 21 | Export 連動 | 出版社 (Kakuyomu/Narou) 向け NSFW フラグ付与 | `src/services/publishers/` |
| 22 | メトリクス | 官能ON/OFF 別のエピソード品質メトリクス収集 | `src/services/book_score_service.py` |
| 23 | 統合テスト | エンドツーエンドで `enable_erotic=True` が本文に反映されることを確認 | `tests/integration/test_erotic_pipeline.py` |
| 24 | ドキュメント | README と AGENTS.md に運用手順を記載 | `README.md` / `AGENTS.md` |

各ステップを以下に詳述する。

---

## Step 1. テストハーネスとフィクスチャ整備

**目的**: 以降のステップで壊さないために、変更前後を比較できるベースラインテストを先に用意する。

**作業内容**:
1. `tests/fixtures/erotic_pipeline/` ディレクトリ新設。
2. `mock_preset.py`: 9ジャンル分の偽 `erotic_rules_*.yaml` を `monkeypatch` でロードさせる fixture。
3. `mock_engine.py`: `EroticEnhancer` が呼ぶ `agent.llm.generate_text` を捕捉するスタブ。**呼ばれた prompt のスナップショット**を保存できる。
4. `tests/unit/test_erotic_baseline.py` 新設:
   - `test_enhancer_gate_off`: `nsfw_enabled=False` なら `EroticEnhancer` は結果を改変しない
   - `test_enhancer_gate_on_intensity0`: `nsfw_enabled=True` でも `erotic_intensity=0` なら改変しない
   - `test_specialist_uses_yaml_when_present`: YAML 注入時に `build_scene_prompt` が YAML の `vocabulary_tier` を使う
5. `pytest tests/unit/test_erotic_baseline.py -v` で全件 PASS を確認 (ベースライン)。

**コミット**: `test(erotic): baseline fixtures and gates (Step 1)`

---

## Step 2. `EroticGate` 値オブジェクト新設 + 用語集約

**目的**: `enable_erotic` / `enable_nsfw` / `nsfw_enabled` の散在を **1つの型** に集約。

**新規ファイル**: `src/domain/value_objects/erotic_gate.py`

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EroticGate:
    """官能機能の有効状態を一つに集約する値オブジェクト。

    旧来は enable_erotic / enable_nsfw / nsfw_enabled / erotic_intensity が
    5箇所に散在していたが、本オブジェクトを唯一の真実とする。
    """
    enabled: bool           # NSFW全体許可 (UI: NSFW/官能コンテンツ許可)
    intensity: int          # 1-5 (UI: 官能強度スライダ)

    def is_active(self) -> bool:
        """シーン単位で官能を有効化するかを判定。"""
        return self.enabled and self.intensity > 0

    @classmethod
    def disabled(cls) -> "EroticGate":
        return cls(enabled=False, intensity=0)

    @classmethod
    def from_context(cls, ctx: dict | None) -> "EroticGate":
        """context dict から EroticGate を構築する後方互換ビルダー。

        旧キー (enable_erotic, enable_nsfw, nsfw_enabled) は全て
        enabled に集約される。intensity は erotic_intensity から取る。
        """
        if not ctx:
            return cls.disabled()
        enabled = bool(
            ctx.get("enable_erotic")
            or ctx.get("enable_nsfw")
            or ctx.get("nsfw_enabled")
            or ctx.get("is_nsfw_enabled")
        )
        intensity = int(ctx.get("erotic_intensity", 0) or 0)
        return cls(enabled=enabled, intensity=intensity)
```

**配置**: `src/domain/value_objects/erotic_gate.py`
**テスト**: `tests/unit/test_erotic_gate.py`
  - `from_context` が5種の旧キーを全て認識すること
  - `is_active()` が `enabled=True, intensity=0` の時に `False` を返すこと

**コミット**: `feat(erotic): introduce EroticGate VO (Step 2)`

---

## Step 3. Streamlit に官能強度スライダ追加

**目的**: ユーザーが強度を 1〜5 で調整できるようにする。

**ファイル**: `streamlit_app/pages/00_Settings.py`

**変更箇所**: 328-335 の NSFW トグル直後に追加。

```python
# 既存 (Step 3 後も維持)
nsfw_enabled = st.toggle(
    "NSFW/官能コンテンツ許可",
    value=getattr(cfg, "enable_nsfw", False),
    key="cfg_enable_nsfw",
    help="ONにすると官能シーンが執筆されます。",
)
cfg.enable_nsfw = nsfw_enabled
ConfigState.set("enable_nsfw", nsfw_enabled)  # ← 既存

# 新規追加
erotic_intensity = st.slider(
    "官能強度 (1=ほのめかし 〜 5=濃密)",
    min_value=0,
    max_value=5,
    value=st.session_state.get("cfg_erotic_intensity", 0),
    key="cfg_erotic_intensity",
    disabled=not nsfw_enabled,
    help="NSFWをONにしている場合のみ有効です。",
)
ConfigState.set("erotic_intensity", erotic_intensity)
```

**ポイント**: スライダは NSFW トグルが OFF の時は `disabled=True` でグレーアウト。

**コミット**: `feat(streamlit): expose erotic intensity slider (Step 3)`

---

## Step 4. `ConfigState` に `erotic_intensity` デフォルト

**目的**: `ConfigState._defaults` に `erotic_intensity` を追加して、初期化漏れを防ぐ。

**ファイル**: `streamlit_app/state.py`

**変更**: 38-47 の `_defaults` に1行追加。

```python
_defaults: dict[str, Any] = {
    "enable_draft_polish": True,
    "enable_actor_critic": True,
    "enable_heavy_audit": True,
    "enable_nsfw": False,
    "erotic_intensity": 0,            # ← 追加
    "safety_filter_level": "BLOCK_ONLY_HIGH",
    ...
}
```

**コミット**: `chore(streamlit): add erotic_intensity default (Step 4)`

---

## Step 5. `pipeline_param_mapper` が UI 値を Context に転写

**目的**: Streamlit の session_state → `WorkflowContext.easy_parameters` の **唯一の橋** を確立。

**ファイル**: `src/services/pipeline_param_mapper.py`

**確認**: 現在の `map_fullauto_kwargs_to_context` (line 9-) と `map_easy_mode_kwargs_to_context` (line 44-) のシグネチャをまず読む。

**変更方針**:
1. `map_*_kwargs_to_context` の直前に共通ヘルパ `_resolve_erotic_gate(kwargs) -> tuple[bool, int]` を新設。
2. 両マッパーで `easy_parameters` に `enable_erotic` と `erotic_intensity` を必ず書く (デフォルト `(False, 0)`)。
3. `WorkflowContext.is_nsfw_enabled` (Step 6 で新設) にも転写。

```python
def _resolve_erotic_gate(kwargs: dict) -> tuple[bool, int]:
    """Streamlit ConfigState / kwargs から (enable_erotic, erotic_intensity) を抽出。"""
    enable = bool(kwargs.get("enable_erotic", False) or kwargs.get("enable_nsfw", False))
    intensity = int(kwargs.get("erotic_intensity", 0) or 0)
    return enable, intensity

def map_fullauto_kwargs_to_context(kwargs: dict[str, Any]) -> WorkflowContext:
    enable, intensity = _resolve_erotic_gate(kwargs)
    ctx = WorkflowContext(...)
    ctx.easy_parameters["enable_erotic"] = enable
    ctx.easy_parameters["erotic_intensity"] = intensity
    ctx.is_nsfw_enabled = enable
    return ctx

def map_easy_mode_kwargs_to_context(kwargs: dict[str, Any]) -> WorkflowContext:
    # 同じ処理
```

**テスト**: `tests/unit/test_pipeline_param_mapper.py`
  - `enable_nsfw=True, erotic_intensity=3` を渡すと `easy_parameters` と `is_nsfw_enabled` が一致
  - 旧キー `enable_erotic=True` も受け入れる

**コミット**: `feat(pipeline): wire UI erotic params into WorkflowContext (Step 5)`

---

## Step 6. `WorkflowContext` に `is_nsfw_enabled` フィールド追加

**目的**: 公式のゲートフラグを Context に持たせる (旧 `enable_nsfw`/`nsfw_enabled` を一本化)。

**ファイル**: `src/services/pipeline_base.py`

**変更**: 40 行目付近に追加。

```python
class WorkflowContext(BaseModel):
    ...
    easy_parameters: dict[str, Any] = Field(default_factory=dict)

    # === 官能ゲート (EasyMode 由来設定とは独立) ===
    is_nsfw_enabled: bool = False
    erotic_intensity: int = 0   # 1-5, 0は無効

    # === EasyMode 由来設定 (SpiceGuard・監査リライト) ===
    ...
```

**後方互換**: 旧 `easy_parameters["enable_nsfw"]` を読むコードは当面残し、Step 16 で完全削除。

**コミット**: `feat(pipeline): add is_nsfw_enabled / erotic_intensity to WorkflowContext (Step 6)`

---

## Step 7. `PlanStep` の初期化フェーズで `enable_erotic` を必ず書く

**目的**: `PlanStep` が `easy_parameters` から **読む側** だけでなく **書く側** にもなる。今は「読んでも誰も書いていない」状態。

**ファイル**: `src/services/pipeline_steps.py`

**変更**: 86-91 で読む前に、PlanStep の冒頭で `easy_parameters` を初期化するロジックを追加。

```python
class PlanStep(WorkflowStep):
    async def execute(self, ctx, engine, reporter):
        # === Step 7 追加: easy_parameters が未初期化なら書く ===
        if not ctx.easy_parameters:
            ctx.easy_parameters = {}
        ctx.easy_parameters.setdefault("enable_erotic", ctx.is_nsfw_enabled)
        ctx.easy_parameters.setdefault("erotic_intensity", ctx.erotic_intensity)

        # === 以降は既存 ===
        ...
        book_id, bible = await engine.planner.create_hegemony_plan(
            ...
            enable_erotic=ctx.easy_parameters["enable_erotic"],
            erotic_intensity=ctx.easy_parameters["erotic_intensity"],
            ...
        )
        ...
```

**ポイント**: `setdefault` を使うことで、Step 5 ですでに値が入っていれば上書きしない (二段防御)。

**コミット**: `fix(pipeline): initialize enable_erotic in PlanStep (Step 7)`

---

## Step 8. `WriteStep` が context に `nsfw_enabled` / `erotic_intensity` を注入

**目的**: `EpisodeWriter.write` に渡される `context` dict に、ゲート値を **必ず注入** する。

**ファイル**: `src/services/pipeline_steps.py` (`WriteStep.execute`, 180-230 付近)

**変更**: `generate_episodes_pipeline` 呼び出しの前で `context_overrides` を構築し、書き込む context にマージ。

```python
class WriteStep(WorkflowStep):
    async def execute(self, ctx, engine, reporter):
        ...
        # === Step 8 追加: 官能ゲート値を context に注入 ===
        ctx_overrides = {
            "nsfw_enabled": ctx.is_nsfw_enabled,
            "erotic_intensity": ctx.erotic_intensity,
        }

        async def write_operation():
            return await engine.writer.generate_episodes_pipeline(
                ...
                is_easy_mode=ctx.is_easy_mode,
                context_overrides=ctx_overrides,   # ← 新規引数
                ...
            )
```

**`generate_episodes_pipeline` 側の変更** (Step 16 で実施): `context_overrides: dict | None = None` 引数を追加し、`write_episode` にそのまま渡す。

**テスト**: `tests/services/test_write_step_context.py`
  - `is_nsfw_enabled=True, erotic_intensity=3` の `ctx` で `WriteStep` を呼ぶと、内部の `generate_episodes_pipeline` に `context_overrides` が正しく伝わる (mock で検証)

**コミット**: `feat(pipeline): inject erotic gate into WriteStep context (Step 8)`

---

## Step 9. `WriteStep` が `preset["erotic"]` (YAML) を `context["erotic_rules_yaml"]` に積む

**目的**: 死蔵されている9個の YAML を **シーン context** まで届ける。

**ファイル**: `src/services/pipeline_steps.py`

**変更**: Step 8 の `ctx_overrides` 構築を拡張。

```python
async def execute(self, ctx, engine, reporter):
    ...
    # === Step 9 追加: ジャンルプリセットの官能YAML を context に積む ===
    from src.presets.loader import load_preset
    try:
        preset = load_preset(ctx.genre)
        erotic_yaml = preset.get("erotic", {})
    except Exception as e:
        reporter.report(f"⚠️ 官能プリセット読込失敗: {e}", "warning")
        erotic_yaml = {}

    ctx_overrides = {
        "nsfw_enabled": ctx.is_nsfw_enabled,
        "erotic_intensity": ctx.erotic_intensity,
        "erotic_rules_yaml": erotic_yaml,   # ← YAML を運ぶ
        "genre": ctx.genre,
    }
    ...
```

**コミット**: `feat(pipeline): inject erotic YAML preset into write context (Step 9)`

---

## Step 10. `EroticEnhancer` のゲート判定を `EroticGate` に委譲

**目的**: 5箇所に散在する `nsfw_enabled / erotic_intensity / enable_erotic` 判定を 1 箇所にまとめる。

**ファイル**: `src/agents/erotic_enhancer.py`

**変更**: 65-69 のゲート判定を差し替え。

```python
# Before
erotic_intensity = context.get("erotic_intensity", 0)
nsfw_enabled = context.get("nsfw_enabled", False)
if not (erotic_intensity > 0 and nsfw_enabled):
    return result

# After
from src.domain.value_objects.erotic_gate import EroticGate
gate = EroticGate.from_context(context)
if not gate.is_active():
    return result
erotic_intensity = gate.intensity
nsfw_enabled = gate.enabled
```

**波及**: 内部の `if specialist and erotic_intensity > 0 and nsfw_enabled:` (3箇所) は `if gate.is_active() and specialist:` に簡素化。

**コミット**: `refactor(erotic): centralize gate check via EroticGate (Step 10)`

---

## Step 11. `EroticSpecialist` が YAML を読んでプロンプトに反映

**目的**: `EroticSpecialist.build_scene_prompt` が `context["erotic_rules_yaml"]` を読めばジャンル毎チューニングが反映される。

**ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更**: `build_scene_prompt` (44-) の冒頭で YAML を取り込み、`_apply_yaml_overrides` ヘルパに渡す。

```python
def build_scene_prompt(self, curve, context, params=None):
    # === Step 11 追加: YAML プリセットがあれば優先 ===
    yaml_rules = context.get("erotic_rules_yaml") or {}
    if yaml_rules:
        self._apply_yaml_overrides(context, yaml_rules)
    # === 以降は既存 ===
    ...

def _apply_yaml_overrides(self, context: dict, yaml_rules: dict) -> None:
    """YAML の値を context にマージする（既存キーは上書きしない）。"""
    if "vocabulary_tier" in yaml_rules:
        context.setdefault("vocabulary_tier", yaml_rules["vocabulary_tier"])
    if "platform_preset" in yaml_rules:
        context.setdefault("platform_preset", yaml_rules["platform_preset"])
    if "allowed_phases" in yaml_rules:
        context.setdefault("allowed_phases", yaml_rules["allowed_phases"])
    if "sensory_priority" in yaml_rules:
        context.setdefault("sensory_priority", yaml_rules["sensory_priority"])
```

**テスト**: `tests/unit/test_erotic_specialist_yaml.py`
  - YAML に `vocabulary_tier: extreme` を入れて `build_scene_prompt` を呼ぶと、生成プロンプトに extreme 語彙が反映される
  - YAML が無い場合は既存のデフォルト動作

**コミット**: `feat(erotic): EroticSpecialist consumes YAML preset (Step 11)`

---

## Step 12. `media_mix.py` の `self.erotic_rules` デッドフィールド削除

**目的**: 代入だけで参照されないフィールドを削除し、「埋もれ」を物理的に除去。

**ファイル**: `src/easy_mode/phase3/media_mix.py` (line 464 付近)

**変更**: `__init__` の `self.erotic_rules = preset.get("erotic", {})` を削除。`preset` 引数自体が不要なら呼び出し側 (`__init__` の `preset=preset` キーワード) も除去。

**確認手順**:
1. `grep -rn "self.erotic_rules" src/` → 0件 になることを確認。
2. `pytest tests/integration/test_easy_mode_export.py -v` → 既存テストが全て PASS することを確認 (影響範囲チェック)。

**コミット**: `chore(cleanup): remove dead erotic_rules field in media_mix (Step 12)`

---

## Step 13. `EroticIntensity` 値オブジェクト削除

**目的**: 誰も import していない VO を削除。

**ファイル**: `src/domain/value_objects/erotic_intensity.py` (削除)

**確認手順**:
1. `grep -rn "EroticIntensity" src/ tests/` を実行し、参照箇所が0であることを再確認 (Step 2 で `EroticGate` に置換済み)。
2. 0件ならファイル削除。
3. `from src.domain.value_objects.erotic_intensity import EroticIntensity` を含む import 文があれば削除。

**コミット**: `chore(cleanup): remove orphan EroticIntensity VO (Step 13)`

---

## Step 14. `EroticDensityController` / `EroticDiversityScore` 整理

**目的**: テスト専用 / 孤立したサービスを整理する。完全削除か、必要なら再配線する。

**ファイル**:
- `src/services/erotic_density_controller.py`
- `src/services/erotic_diversity_score.py`

**確認**:
1. `grep -rn "EroticDensityController\|get_erotic_advice" src/` で参照箇所を網羅。
2. `EroticDensityController` のメソッド (`get_erotic_advice` 等) を呼ぶ **production コード** がなければ削除候補。
3. `EroticDiversityScore` は `tests/` からのみ参照されていれば、**`tests/unit/erotic_metrics/` にテスト専用モジュールとして移動** (or 完全削除)。

**判断基準**:
- 6ヶ月以内に使う予定あり → `EroticEnhancer.enhance_erotic_content` のアフターグロウ評価 (Step 14a) に再配線。
- ない → 削除し、`tests/unit/test_erotic_evaluators.py` も整理。

**コミット**: `chore(cleanup): remove or rewire orphan erotic evaluators (Step 14)`

---

## Step 15. `RefineEroticWorkflow` を「明示オプトイン」化

**目的**: 自動パイプラインから **呼ばれない** ワークフローをそのまま放置せず、明示オプトインに降格。

**ファイル**: `src/backend/workflows/refine_erotic_workflow.py` および登録箇所 (`__init__.py`)

**変更**:
1. `__init__.py` の re-export から外し、`src/backend/workflows/manual/refine_erotic.py` へ移動。
2. 移動先では CLI / API からのみ起動できる導線 (`POST /admin/refine-erotic`) を用意 (or README に手順を記載)。
3. テスト `tests/test_erotic_workflow.py` はそのまま残し、新パスを import するように修正。

**コミット**: `refactor(workflows): move RefineEroticWorkflow to manual opt-in (Step 15)`

---

## Step 16. 重複 writer 統合 (`_writing.py` / `writing.py` を `agent.py` 系統に統一)

**目的**: 並走する2系統の `EpisodeWriter` を1つに統合し、配線点を一意化する。

**ファイル**:
- `src/agents/writing/_writing.py`
- `src/agents/writing/writing.py`
- `src/agents/writing/agent.py`
- `src/agents/writing/episode_writer.py`

**手順**:
1. `grep -rn "from src.agents.writing._writing\|from src.agents.writing.writing\|from .writing\|from ._writing" src/` で参照を網羅。
2. `_writing.py` のクラスが `writing.py` と同等機能を持つなら `_writing.py` を **削除** し、参照を `writing.py` に張り替え。
3. `agent.py` の `WritingAgent` が `EpisodeWriter` を使う経路を **正本** と確定。`writing.py` 内の旧 `EpisodeWriter` は `agent.py` の `EpisodeWriter` に委譲する形にリファクタ。
4. `EpisodeWriter.write` 内に、Step 8 で注入された `context["nsfw_enabled"]` / `context["erotic_intensity"]` / `context["erotic_rules_yaml"]` を `EroticEnhancer` に渡すロジックが既にあるか確認。なければ Step 10 のゲートに揃える。

**コミット**: `refactor(writing): consolidate duplicated EpisodeWriter (Step 16)`

---

## Step 17. `SpiceGuard` の名称整理 (任意・影響大)

**目的**: "spice" の二義性 (ナラティブ尖り vs 官能) を解消。

**ファイル**:
- `src/easy_mode/spice_guard.py`
- `src/services/spice_guard_adapter.py`
- `src/services/pipeline_steps.py` (呼び出し側)
- `src/services/auto_workflow_pipeline.py`

**判断**: これは **破壊的変更** を含むため、影響範囲に応じて2案から選ぶ。

- **A案 (低リスク)**: 新名称 `NarrativeEdgeGuard` を別名で新設し、`SpiceGuard` は `NarrativeEdgeGuard` の旧名エイリアスとして残す。ドキュメントでは新名称を主、コード内コメントで「旧: SpiceGuard」と注記。
- **B案 (高リスク・推奨)**: 一括 rename (`spice_guard` → `narrative_edge_guard`、`SpiceGuard` → `NarrativeEdgeGuard`)。

**判断はユーザーに確認** (本計画書では A案をデフォルト推奨)。

**コミット**: `refactor(spice): clarify SpiceGuard as NarrativeEdgeGuard (Step 17)`

---

## Step 18. Planner が `enable_erotic`/`erotic_intensity` を反映

**目的**: 企画段階 (hegemony plan) で官能有効時にプロットに官能ビートを織り込む。

**ファイル**: `src/backend/planner.py` (`create_hegemony_plan` 周辺)

**確認**: 既に `enable_erotic` / `erotic_intensity` 引数を持っている場合、**その引数を実際に使うロジックが欠落** している可能性が高い。

**変更**:
1. `enable_erotic=True` の場合: `bible.romance_track` を有効化し、主要エピソード配列に `intimacy_beat` を挿入。
2. `erotic_intensity >= 3` の場合: 中盤〜後半に **explicit_arc** フラグを立てる (該当話数のテンションカーブを引き上げ)。
3. `enable_erotic=False`: 現行動作 (変更なし)。

**コミット**: `feat(planner): reflect enable_erotic in hegemony plan (Step 18)`

---

## Step 19. Hook / Plot 連動 (romance_track / intimacy_beat)

**目的**: プロット拡張 (`next_beats_service`) とフック生成 (`hook_templates`) が官能有効時に官能寄りフックを選好する。

**ファイル**:
- `src/services/next_beats_service.py`
- `src/services/hook_templates.py`

**変更**:
1. `next_beats_service` に `intimacy_level: int = 0` 引数を追加。`intimacy_level > 0` の時、`beats` の20-30%を `category="intimacy"` に割り振る。
2. `hook_templates` のフィルタに `category="intimacy"` を含め、`hook_params_<genre>.json` に `intimacy_*` タグがあれば優先。

**コミット**: `feat(beats): add intimacy track when erotic enabled (Step 19)`

---

## Step 20. 監査連動 — 官能有効時に `target_audit_score` を引き下げ

**目的**: 官能シーンは "entertainment score" が高くなりにくいため、`target_audit_score` を動的に調整して過度な再生成ループを防ぐ。

**ファイル**: `src/services/pipeline_steps.py` (`AuditRewriteStep`, 286-360 付近)

**変更**:
```python
# AuditRewriteStep 冒頭
target = ctx.target_audit_score
if ctx.is_nsfw_enabled and ctx.erotic_intensity >= 3:
    target = max(target - 5.0, 80.0)   # 官能シーンは 5 点甘め
```

**コミット**: `feat(audit): relax target score for erotic scenes (Step 20)`

---

## Step 21. Export 連動 — 出版社向け NSFW フラグ付与

**目的**: Kakuyomu / Narou / Kindle / Kobo のエクスポート時に、官能フラグをメタデータとして渡し、プラットフォーム側のガイドライン違反を防ぐ。

**ファイル**: `src/services/publishers/*.py`

**変更**:
1. `kakuyomu.py` / `narou.py`: シリーズ/話に `adult: bool` フィールドが付与可能な場合、それを使う (`is_nsfw_enabled` を context 経由で受け取る)。
2. `kindle.py` / `kobo.py`: EPUB の `metadata` に `<meta property="rendition:access">exclusive</meta>` のような内部識別子を付与 (任意)。

**コミット**: `feat(publishers): propagate NSFW flag to platform metadata (Step 21)`

---

## Step 22. 官能 ON/OFF 別のエピソード品質メトリクス収集

**目的**: BookScore に `erotic_enabled: bool` と `erotic_intensity: int` を渡し、官能有無別の品質トレンドを可視化。

**ファイル**: `src/services/book_score_service.py`

**変更**: `score_episode` の入力 dict に `erotic_enabled`, `erotic_intensity` を含め、BookScoreRecord テーブルに保存 (マイグレーションが必要)。

**マイグレーション**: `src/backend/alembic/versions/0002_erotic_metrics.py` 新設。

**コミット**: `feat(metrics): track erotic quality separately (Step 22)`

---

## Step 23. 統合テスト

**目的**: エンドツーエンドで NSFW トグル ON → 本文に官能要素が反映されることを確認。

**新規ファイル**: `tests/integration/test_erotic_pipeline.py`

**テストケース**:
1. `test_full_pipeline_with_nsfw_off`: `is_nsfw_enabled=False` → 出力テキストに官能語彙 (YAML の `vocabulary_tier: extreme` 由来) が出ない。
2. `test_full_pipeline_with_nsfw_on_intensity_3`: `is_nsfw_enabled=True, erotic_intensity=3` → YAML の `vocabulary_tier` がプロンプトに反映され、`AfterglowEvaluator` が動作する。
3. `test_yaml_propagation`: `genre="vrmmo"` の時、`vrmmo` の YAML にある `allowed_phases` が `EroticSpecialist` に渡る (mock で検証)。
4. `test_gate_disabled_does_not_call_llm_regeneration`: ゲート OFF の時、`EroticEnhancer` は LLM を再呼び出ししない (mock の呼び出し回数 = 1)。

**コミット**: `test(integration): end-to-end erotic pipeline (Step 23)`

---

## Step 24. ドキュメント

**目的**: 運用手順を残し、再度埋もれないようにする。

**ファイル**:
- `README.md`: 「官能モード」の章を追加。NSFW トグル・強度スライダの場所、影響範囲 (`EroticEnhancer`/`EroticSpecialist`/YAML/Planner/Audit/Export)、注意点を記載。
- `AGENTS.md`: 開発者向け。Step 2 の `EroticGate` を「真実の源」として参照、用語統一の経緯、YAML プリセットの編集手順。

**コミット**: `docs: erotic mode user & developer guide (Step 24)`

---

## リスクとロールバック戦略

| ステップ | リスク | ロールバック |
|---------|--------|--------------|
| 1-6 | 低 (テスト追加のみ) | git revert |
| 7-10 | 中 (ゲート判定の変更) | `EroticEnhancer` の旧判定を `if EroticGate.is_active() or True:` に一時退避 |
| 11 | 中 (プロンプト内容変化) | YAML が無い経路 (デフォルト) で従来動作を保証する |
| 12-15 | 低 (削除) | ファイルを `git revert` で復元 |
| 16 | 高 (writer 統合) | `_writing.py` を一旦退避、参照を `writing.py` に張り替えずに段階移行 |
| 17 | 中 (名称変更) | A案 (エイリアス) なら旧名は残るので安全 |
| 18-20 | 中 (企画品質変化) | `intimacy_beat` の挿入比率を 5% から始める |
| 21 | 中 (プラットフォーム規約) | NSFW OFF 時の動作は不変、ON のみ影響 |
| 22 | 低 (観測のみ) | ロールバック容易 |
| 23-24 | なし | テスト・ドキュメント追加のみ |

---

## 検証チェックリスト (全体完了後)

- [ ] Streamlit で NSFW トグルを ON にして強度 3 → 生成テキストに官能語彙が含まれる
- [ ] Streamlit で NSFW トグルを OFF → 官能語彙が消える (強度の値にかかわらず)
- [ ] `grep -rn "enable_nsfw\|nsfw_enabled\|enable_erotic" src/` で **3 種以上の同名変数が同居しない** こと (EroticGate 経由のみ)
- [ ] `pytest tests/unit/test_erotic_baseline.py tests/unit/test_erotic_gate.py tests/integration/test_erotic_pipeline.py -v` → 全 PASS
- [ ] `pytest tests/ -v` → 既存テスト全 PASS (回帰なし)
- [ ] `ruff check src/ tests/ streamlit_app/` → 0 errors
- [ ] `mypy src/domain/value_objects/erotic_gate.py src/agents/erotic_enhancer.py src/engine/prompts/erotic_specialist.py` → 0 errors

---

## 参考: 影響ファイル一覧

```
新規:
  src/domain/value_objects/erotic_gate.py
  src/backend/alembic/versions/0002_erotic_metrics.py
  tests/unit/test_erotic_gate.py
  tests/unit/test_erotic_baseline.py
  tests/unit/test_erotic_specialist_yaml.py
  tests/services/test_write_step_context.py
  tests/integration/test_erotic_pipeline.py

変更:
  streamlit_app/state.py
  streamlit_app/pages/00_Settings.py
  src/services/pipeline_base.py
  src/services/pipeline_param_mapper.py
  src/services/pipeline_steps.py
  src/services/auto_workflow_pipeline.py
  src/services/next_beats_service.py
  src/services/hook_templates.py
  src/services/book_score_service.py
  src/services/publishers/kakuyomu.py
  src/services/publishers/narou.py
  src/services/publishers/kindle.py
  src/services/publishers/kobo.py
  src/agents/erotic_enhancer.py
  src/agents/writing/agent.py        (Step 16)
  src/agents/writing/writing.py      (Step 16)
  src/agents/writing/episode_writer.py (Step 16)
  src/backend/planner.py             (Step 18)
  src/engine/prompts/erotic_specialist.py
  src/easy_mode/spice_guard.py       (Step 17, 任意)
  README.md / AGENTS.md              (Step 24)

削除:
  src/domain/value_objects/erotic_intensity.py      (Step 13)
  src/services/erotic_density_controller.py         (Step 14)
  src/services/erotic_diversity_score.py            (Step 14)
  src/easy_mode/phase3/media_mix.py:464 (1行)       (Step 12)
  src/agents/writing/_writing.py                    (Step 16)
```
