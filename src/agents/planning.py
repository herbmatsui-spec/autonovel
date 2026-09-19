# agents/planning.py
import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName
from src.config.commercial_beat_sheet import COMMERCIAL_40EP_BEATS
from src.models.beat_sheet import EpisodeBeat
from src.models.plot import ArcList
from src.models.subversion import SubversionEngine
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class PlanningAgent(SkillAgent):
    """企画・プロット立案を担当するエージェント。
    LLM にアーク生成プロンプトを投げ、JSON 形式でアーク案を受け取る。
    """

    def __init__(self, repo: Any = None, llm: LLMService | None = None, prompt_manager: Any = None):
        super().__init__(repo=repo, llm=llm)
        self.prompt_manager = prompt_manager

    # SubversionEngine 設定キー定数
    SUBVERSION_CONFIG_KEYS = {
        "subversion_interval",
        "subversion_enabled",
        "subversion_weights",
        "subversion_seed",
    }

    def _validate_subversion_config(self, kwargs: dict) -> None:
        """subversion_ プレフィックスの未知キーを警告"""
        unknown = {k for k in kwargs if k.startswith("subversion_")} - self.SUBVERSION_CONFIG_KEYS
        if unknown:
            logger.warning(f"Unknown subversion config keys: {unknown}")

    def _init_subversion_engine(self, kwargs: dict, title: str = "", target_eps: int = 0) -> SubversionEngine:
        """artifacts / kwargs から SubversionEngine を初期化"""
        # seed が指定されていない場合は title + target_eps から自動生成
        seed = kwargs.get("subversion_seed")
        if not seed and title:
            seed = f"{title}_{target_eps}"
        return SubversionEngine(
            interval=kwargs.get("subversion_interval", 3),
            enabled=kwargs.get("subversion_enabled", True),
            pattern_weights=kwargs.get("subversion_weights", {"A": 0.4, "B": 0.3, "C": 0.3}),
            seed=seed or "",
        )

    async def generate_arcs(
        self,
        title: str,
        synopsis: str,
        target_eps: int,
        start_ep: int = 1,
        **kwargs: Any,
    ) -> ArcList:
        """作品のアーク構成を生成する。

        Args:
            title: 作品タイトル
            synopsis: あらすじ
            target_eps: 生成対象の総話数
            start_ep: 再構築時の開始話数（デフォルト1 = 全文生成）
            **kwargs: その他のプロンプト引数

        Returns:
            生成されたアークリスト (ArcList)

        Raises:
            RuntimeError: アーク生成に失敗した場合
        """
        # 再構築（start_ep > 1）の場合は、生成する話数を開始話数で相殺し、
        # プロンプトにも「第N話以降」の指示を合成する。
        effective_eps = max(target_eps - start_ep + 1, 1)
        if start_ep > 1:
            synopsis = (
                f"【第{start_ep}話からの再構築】\n"
                f"以下は第{start_ep}話以降の物語構成である。\n"
                f"{synopsis}"
            )

        prompt = self.prompt_manager.build_arc_generation_prompt(
            title=title,
            synopsis=synopsis,
            target_eps=effective_eps,
            start_ep=start_ep,
            **kwargs,
        )
        result = await self.llm.generate_json(
            purpose="planning",
            prompt=prompt,
            response_schema=None,  # 必要に応じて Pydantic スキーマを指定
        )
        if not result.get("success"):
            raise RuntimeError("Arc generation failed")

        metadata = result.get("metadata", {})
        # プロンプト生成時の都合で start_ep が 1 に丸められているため、
        # 各アークの話数オフセットを start_ep に合わせて補正する。
        if start_ep > 1:
            metadata = self._shift_arcs_start_ep(metadata, start_ep)

        # ★追加: SubversionEngine 適用
        self._validate_subversion_config(kwargs)
        engine = self._init_subversion_engine(kwargs, title, target_eps)
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

        # 変更済みの arcs オブジェクトを返す（再バリデーションすると subversion が失われるため）
        return arcs

    @staticmethod
    def _shift_arcs_start_ep(metadata: Any, start_ep: int) -> Any:
        """生成されたアークの話数を start_ep ベースに補正する."""
        if not isinstance(metadata, dict):
            return metadata
        arcs = metadata.get("arcs")
        if not isinstance(arcs, list):
            return metadata
        for arc in arcs:
            if isinstance(arc, dict):
                for key in ("start_ep", "end_ep"):
                    if key in arc and isinstance(arc[key], int):
                        arc[key] = arc[key] + (start_ep - 1)
        return metadata

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """スキル実行エントリーポイント。run から呼ばれる。"""
        self.emit_event("planning.started", {
            "book_id": ctx.book_id,
            "title": ctx.artifacts.get("title"),
        })

        title = ctx.artifacts.get("title")
        synopsis = ctx.artifacts.get("synopsis", "")
        target_eps = ctx.artifacts.get("target_eps", 10)
        start_ep = ctx.artifacts.get("start_ep", 1)

        if not title:
            self.emit_event("planning.error", {
                "book_id": ctx.book_id,
                "error": "title is required in artifacts",
            })
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="title is required in artifacts",
            )

        arcs = await self.generate_arcs(
            title=title,
            synopsis=synopsis,
            target_eps=target_eps,
            start_ep=start_ep,
        )

        artifacts = {"arcs": arcs.model_dump()}

        # ★追加: subversion_engine を artifacts に露出（ダウンストリームで参照可能にする）
        self._validate_subversion_config(ctx.artifacts)
        # ctx.artifacts から設定を取得してエンジンを再構築
        engine = self._init_subversion_engine(ctx.artifacts, title, target_eps)
        engine.plan_schedule(target_eps, start_ep)
        artifacts["subversion_engine"] = engine.model_dump()

        # 企画ガチャ（3案並行生成）モードのサポート (Step 9)
        if ctx.artifacts.get("proposal_gacha", False):
            # ctx.artifacts から既知のパラメータを除外して渡す
            known_params = {"title", "synopsis", "target_eps", "start_ep", "proposal_gacha"}
            extra_kwargs = {k: v for k, v in ctx.artifacts.items() if k not in known_params}
            proposals = await self.generate_proposals_isolated(
                title=title,
                synopsis=synopsis,
                target_eps=target_eps,
                **extra_kwargs,
            )
            artifacts["proposals"] = proposals

        self.emit_event("planning.completed", {
            "book_id": ctx.book_id,
            "arc_count": len(arcs.arcs) if arcs.arcs else 0,
            "proposal_count": len(artifacts.get("proposals", {})),
        })

        return AgentResult(
            next_agent=AgentName.PLOT,
            artifacts=artifacts,
        )

    async def generate_proposals_isolated(
        self,
        title: str,
        synopsis: str,
        target_eps: int = 10,
        proposal_count: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate multiple proposal candidates using physical sandbox isolation (Step 9)."""
        from src.services.proposal_isolation import ProposalIsolationRunner, ProposalSandboxContext

        runner = ProposalIsolationRunner([f"proposal_{chr(ord('a') + i)}" for i in range(proposal_count)])

        async def _isolated_worker(sandbox_ctx: ProposalSandboxContext) -> dict[str, Any]:
            # 各案のシードやバリエーション指示
            variant_seed = f"Variant {sandbox_ctx.proposal_id.upper()}"
            sub_synopsis = f"{synopsis}\n【企画コンセプト変種: {variant_seed}】"

            # ★各提案ごとに独立シードで裏切りスケジュール生成
            prop_kwargs = {
                **kwargs,
                "subversion_seed": f"{kwargs.get('subversion_seed', '')}_{sandbox_ctx.proposal_id}"
            }
            arcs = await self.generate_arcs(
                title=f"{title} ({variant_seed})",
                synopsis=sub_synopsis,
                target_eps=target_eps,
                **prop_kwargs,
            )
            sandbox_ctx.record_interaction("system", f"Generated for {sandbox_ctx.proposal_id}")
            return {
                "proposal_id": sandbox_ctx.proposal_id,
                "title": f"{title} ({variant_seed})",
                "arcs": arcs.model_dump(),
            }

        return await runner.execute_isolated_proposals(_isolated_worker)

    async def generate_commercial_beat_sheet(
        self,
        title: str,
        synopsis: str,
        **kwargs: Any,
    ) -> list[EpisodeBeat]:
        """40話商業ビートシートを生成し、DBに保存するためのリストを返す。

        Args:
            title: 作品タイトル
            synopsis: あらすじ
            **kwargs: プロンプトマネージャに渡す追加引数

        Returns:
            40話分のEpisodeBeatリスト
        """
        from src.models.beat_sheet import EpisodeBeat

        # 商業ビートシート用プロンプトを構築
        prompt = await self.prompt_manager.render_async(
            "beat_sheet_generation.j2",
            {
                "title": title,
                "synopsis": synopsis,
                "commercial_beats": COMMERCIAL_40EP_BEATS,
                **kwargs,
            },
        )

        # LLMにJSON形式で結果を求める（ただしCSVテキストでも可とする）
        result = await self.llm.generate_json(
            purpose="planning",
            prompt=prompt,
            response_schema=None,  # CSVテキストをパースするためスキーマは使わない
        )
        if not result.get("success"):
            raise RuntimeError("Commercial beat sheet generation failed")

        # 結果からCSVテキストを取得し、EpisodeBeatオブジェクトに変換
        csv_text = result.get("data", "")
        beats = []
        lines = csv_text.strip().splitlines()
        if lines and lines[0].startswith("話数"):
            lines = lines[1:]  # ヘッダー行をスキップ
        for line in lines:
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            ep_num = int(parts[0])
            phase = parts[1]
            mission = parts[2]
            tension_target = float(parts[3])
            visual_scene_focus = parts[4]
            beats.append(
                EpisodeBeat(
                    ep_num=ep_num,
                    phase=phase,
                    mission=mission,
                    tension_target=tension_target,
                    visual_scene_focus=visual_scene_focus,
                )
            )

        # ★追加: ビートシートにも裏切り注入
        self._validate_subversion_config(kwargs)
        beat_engine = self._init_subversion_engine(kwargs, title, 40)
        beat_engine.plan_schedule(40, 1)
        for beat in beats:
            beat_engine.apply_to_beat(beat, beat.ep_num)

        # 40話分になるように補足（不足分はデフォルト値で埋める）
        if len(beats) < 40:
            for i in range(len(beats) + 1, 41):
                beats.append(
                    EpisodeBeat(
                        ep_num=i,
                        phase="不明",
                        mission="未実装",
                        tension_target=0.5,
                        visual_scene_focus="未設定",
                    )
                )
        return beats

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Orchestrator 用エントリーポイント。execute をラップする。"""
        return await self.execute(ctx)
