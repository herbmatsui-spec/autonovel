# PLAN_B3: PlanningAgent への SubversionEngine 適用フック実装（12ステップ）

**対象ファイル:** `src/agents/planning.py`（既存編集）  
**依存:** `PLAN_B1`, `PLAN_B2` 完了済み  
**ゴール:** アーク生成・ビートシート生成の両パイプラインで、決定論的裏切りスケジュールが自動適用・検証・永続化される

---

## Step 1: インポート追加
**作業:** `src/agents/planning.py` に `SubversionEngine` インポート追加。
**テスト:** `python -c "from src.agents.planning import PlanningAgent; print('import ok')"`

```python
# 既存インポート付近に追加
from src.models.subversion import SubversionEngine
```

---

## Step 2: generate_arcs() に engine 初期化ヘルパー追加
**作業:** `PlanningAgent` クラス内に `_init_subversion_engine(kwargs)` プライベートメソッドを追加。artifacts / kwargs から `interval`, `enabled`, `pattern_weights`, `seed` を読み取り `SubversionEngine` 生成・返却。
**テスト:** 単体で呼び出し、デフォルト値・上書き値それぞれで正しく初期化されること確認。

```python
    def _init_subversion_engine(self, kwargs: dict) -> SubversionEngine:
        """artifacts / kwargs から SubversionEngine を初期化"""
        return SubversionEngine(
            interval=kwargs.get("subversion_interval", 3),
            enabled=kwargs.get("subversion_enabled", True),
            pattern_weights=kwargs.get("subversion_weights", {"A": 0.4, "B": 0.3, "C": 0.3}),
        )
```

---

## Step 3: generate_arcs() 内でスケジュール生成・適用
**作業:** 既存 `generate_arcs` の LLM生成直後（`ArcList.model_validate(metadata)` 前後）に以下を挿入：
1. `engine = self._init_subversion_engine(kwargs)`
2. `engine.plan_schedule(target_eps, start_ep)`
3. 各 `arc` に対して `for ep in range(arc.start_ep, arc.end_ep + 1): engine.apply_to_arc(arc, ep)`
4. `errors = engine.validate_coherence(target_eps)` → 警告ログ
5. `metadata["subversion_engine"] = engine.model_dump()` で永続化
**テスト:** モックLLMで生成したアークに `thematic_milestone` が注入されること確認。

```python
        # 既存: result = await self.llm.generate_json(...)
        # 既存: metadata = result.get("metadata", {})
        # 既存: if start_ep > 1: metadata = self._shift_arcs_start_ep(metadata, start_ep)
        
        # ★追加: SubversionEngine 適用
        engine = self._init_subversion_engine(kwargs)
        engine.plan_schedule(target_eps, start_ep)
        
        # 一旦 ArcList に変換してから適用（ArcBlueprint オブジェクト操作のため）
        arcs = ArcList.model_validate(metadata)
        for arc in arcs.arcs:
            for ep in range(arc.start_ep, arc.end_ep + 1):
                engine.apply_to_arc(arc, ep)
        
        errors = engine.validate_coherence(target_eps)
        if errors:
            logger.warning(f"Subversion coherence warnings: {errors}")
        
        # エンジン状態をメタデータに埋め込み（extra_engines 経由で永続化）
        metadata["subversion_engine"] = engine.model_dump()
        
        return ArcList.model_validate(metadata)
```

---

## Step 4: generate_commercial_beat_sheet() にビート適用追加
**作業:** 既存の `beats` リスト生成ループ（`for i in range(len(beats) + 1, 41):` の直前）に `engine.apply_to_beat(beat, beat.ep_num)` を挿入。engine は同メソッド内で初期化（`target_eps=40` 固定）。
**テスト:** 生成された `EpisodeBeat` の `mission`, `visual_scene_focus`, `tension_target` が 3話ごとに更新されること確認。

```python
        # 既存: beats = [] ... CSVパースループ ...
        
        # ★追加: ビートシートにも裏切り注入
        beat_engine = self._init_subversion_engine(kwargs)
        beat_engine.plan_schedule(40, 1)
        for beat in beats:
            beat_engine.apply_to_beat(beat, beat.ep_num)
        
        # 既存: 不足分デフォルト補完ループ ...
```

---

## Step 5: execute() / run() で artifacts へ engine 状態露出
**作業:** `execute()` の戻り値 `artifacts` に `"subversion_engine": engine.model_dump()` を追加（Step 3 で metadata に入れたものをそのまま流用）。ダウンストリームエージェント（PlotAgent等）が参照可能にする。
**テスト:** `execute()` 実行後、`result.artifacts["subversion_engine"]["schedule"]` に 3,6,9... のエントリがあること。

```python
        # 既存: artifacts = {"arcs": arcs.model_dump()}
        
        # ★追加: subversion_engine を artifacts に露出
        artifacts["subversion_engine"] = metadata.get("subversion_engine", {})
        
        # 既存: proposal_gacha 分岐 ...
```

---

## Step 6: 設定キー命名規則統一・ドキュメント化
**作業:** 受け入れる kwargs キーを `subversion_interval`, `subversion_enabled`, `subversion_weights`, `subversion_seed` の4つに固定。クラス定数 `SUBVERSION_CONFIG_KEYS = [...]` として定義し、バリデーションヘルパー `_validate_subversion_config(kwargs)` を追加（不明キーは警告）。
**テスト:** 正常キー・タイポキー混在で警告が出ること確認。

```python
    SUBVERSION_CONFIG_KEYS = {
        "subversion_interval", "subversion_enabled", 
        "subversion_weights", "subversion_seed"
    }

    def _validate_subversion_config(self, kwargs: dict) -> None:
        unknown = set(kwargs.keys()) & {k for k in kwargs if k.startswith("subversion_")} - self.SUBVERSION_CONFIG_KEYS
        if unknown:
            logger.warning(f"Unknown subversion config keys: {unknown}")
```

---

## Step 7: seed 対応（再現性強化）
**作業:** `SubversionEngine` に `seed: str` フィールド追加（PLAN_B1 Step 3 で `seed` 文字列に含めるよう修正済み前提）。`_init_subversion_engine` で `kwargs.get("subversion_seed")` または `f"{title}_{target_eps}"` を自動生成して渡す。
**テスト:** 同一 seed で複数回実行→完全同一スケジュール。異なる seed で異なるスケジュール。

```python
    # SubversionEngine 側（PLAN_B1 Step 5 修正）
    seed: str = Field(default="", description="再現性用シード")
    
    def plan_schedule(self, total_eps: int, start_ep: int = 1) -> list[SubversionPattern]:
        # seed 使用
        seed = f"subversion_{self.seed}_{ep}_{total_eps}_{self.interval}"
        ...
```

---

## Step 8: proposal_gacha モード対応
**作業:** `generate_proposals_isolated()` 内の `_isolated_worker` でも同様に `SubversionEngine` 初期化・適用を行う。各提案ごとに独立したシード（`proposal_id` 含む）でバリエーションを出す。
**テスト:** `proposal_gacha=True` で3案生成し、各案の `subversion_engine.schedule` が異なるパターン配分になっていること確認。

```python
        async def _isolated_worker(sandbox_ctx: ProposalSandboxContext) -> dict[str, Any]:
            variant_seed = f"Variant {sandbox_ctx.proposal_id.upper()}"
            sub_synopsis = f"{synopsis}\n【企画コンセプト変種: {variant_seed}】"
            
            # ★各提案ごとに独立シードで裏切りスケジュール生成
            prop_kwargs = {**kwargs, "subversion_seed": f"{kwargs.get('subversion_seed', '')}_{sandbox_ctx.proposal_id}"}
            arcs = await self.generate_arcs(
                title=f"{title} ({variant_seed})",
                synopsis=sub_synopsis,
                target_eps=target_eps,
                **prop_kwargs,
            )
            ...
```

---

## Step 9: 単体テストファイル作成
**作業:** `tests/test_planning_subversion.py` 作成。`PlanningAgent` をモックLLMでインスタンス化し、以下を検証：
1. `generate_arcs` 戻り値のアークに `thematic_milestone` 裏切り注入済み
2. `generate_commercial_beat_sheet` 戻り値のビートに `mission` 裏切り注入済み
3. `artifacts["subversion_engine"]` にスケジュール含む
4. `proposal_gacha` 時、各提案で独立スケジュール
5. `subversion_enabled=False` で無効化動作
**テスト:** `pytest tests/test_planning_subversion.py -v` 全パス

```python
# tests/test_planning_subversion.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.planning import PlanningAgent
from src.models.plot import ArcList, ArcBlueprint

class TestPlanningSubversion:
    @pytest.fixture
    def agent(self):
        llm = MagicMock()
        llm.generate_json = AsyncMock(return_value={
            "success": True,
            "metadata": {
                "arcs": [
                    {"arc_num": 1, "start_ep": 1, "end_ep": 10, "title": "序章", "summary": "test"}
                ]
            }
        })
        pm = MagicMock()
        pm.build_arc_generation_prompt.return_value = "prompt"
        return PlanningAgent(llm=llm, prompt_manager=pm)

    @pytest.mark.asyncio
    async def test_generate_arcs_injects_subversion(self, agent):
        arcs = await agent.generate_arcs("Test", "Synopsis", 10, subversion_enabled=True)
        # アーク内の thematic_milestone に裏切り文言
        assert any("裏切り" in arc.thematic_milestone for arc in arcs.arcs)

    @pytest.mark.asyncio
    async def test_generate_beat_sheet_injects_subversion(self, agent):
        beats = await agent.generate_commercial_beat_sheet("Test", "Synopsis", subversion_enabled=True)
        subversion_beats = [b for b in beats if "裏切り" in b.mission]
        assert len(subversion_beats) >= 3  # 3,6,9,12,15,18,21,24,27,30,33,36,39

    @pytest.mark.asyncio
    async def test_disabled(self, agent):
        arcs = await agent.generate_arcs("Test", "Synopsis", 10, subversion_enabled=False)
        assert all("裏切り" not in arc.thematic_milestone for arc in arcs.arcs)

    @pytest.mark.asyncio
    async def test_proposal_gacha_independent_schedules(self, agent):
        # proposal_gacha は統合テストで別途
        pass
```

---

## Step 10: 統合テスト（オーケストレータ経由）
**作業:** `tests/test_orchestrator_subversion_flow.py` 作成。実際の `Orchestrator` → `PlanningAgent` → `PlotAgent` の流れで、artifacts 経由で `subversion_engine` が引き継がれるか確認。
**テスト:** 実行後、DB保存されたエピソードレコードの `extra_engines.subversion` にスケジュールが残っていること。

---

## Step 11: 既存テスト回帰確認
**作業:** `pytest tests/ -k "planning"` 既存テスト全実行。LLMモック差し替えで副作用がないか確認。
**テスト:** 既存テスト全パス。

---

## Step 12: 設定例ドキュメント・CLI動作確認
**作業:** `docs/subversion_config.md` 作成（kwargs 4キーの説明・JSON例）。`scripts/test_subversion_full.py` でエンドツーエンド実行（アーク生成→ビートシート→検証）し、コンソールにサマリー表示。
**テスト:** スクリプト実行でエラーなし・サマリー出力。

```python
# scripts/test_subversion_full.py
import asyncio
from src.agents.planning import PlanningAgent
from src.services.llm_service import LLMService

async def main():
    # モックLLMで高速実行
    llm = LLMService()  # 実際はモック差し替え
    agent = PlanningAgent(llm=llm, prompt_manager=...)
    
    arcs = await agent.generate_arcs("Test Novel", "Hero exiled, gets cheat power", 40,
                                     subversion_enabled=True, subversion_interval=3)
    print(f"Arcs: {len(arcs.arcs)}")
    for arc in arcs.arcs:
        if hasattr(arc, "subversion") and arc.subversion:
            print(f"  Arc{arc.arc_num} Ep{arc.subversion.trigger_ep}: {arc.subversion.pattern_type}")
    
    beats = await agent.generate_commercial_beat_sheet("Test Novel", "Synopsis", subversion_enabled=True)
    sub_beats = [b for b in beats if "裏切り" in b.mission]
    print(f"Subversion beats: {len(sub_beats)}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 完了基準
- [ ] `src/agents/planning.py` に適用フック実装完了
- [ ] `tests/test_planning_subversion.py` 全パス
- [ ] `tests/test_orchestrator_subversion_flow.py` 全パス
- [ ] 既存 planning テスト全パス（回帰なし）
- [ ] `mypy` / `ruff` クリーン
- [ ] `scripts/test_subversion_full.py` 正常出力

---

## 3計画書の依存順序まとめ

| 計画 | ファイル | 依存 | 実行順序 |
|------|----------|------|----------|
| **PLAN_B1** | `src/models/subversion.py` (新規) | なし | 1st |
| **PLAN_B2** | `src/models/plot.py` (編集) | B1 | 2nd |
| **PLAN_B3** | `src/agents/planning.py` (編集) | B1, B2 | 3rd |

各計画は **12ステップ × 3 = 36 ステップ** で完結。  
低性能LLMでも「1ステップ＝1ファイル編集＋対応テスト」の粒度で迷わず実装可能。