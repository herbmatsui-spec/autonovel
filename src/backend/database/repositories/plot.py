from __future__ import annotations

"""
database/repo_plot.py - プロット(Plots)データ操作用のリポジトリMixin
"""
import json
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import delete, select, update

from services.errors import retry_on_lock
from src.backend.database.models import Book, Branch, CharacterArc, Foreshadowing, Plot

if TYPE_CHECKING:
    from src.models import PlotDbModel


from src.backend.database.repositories.base import BaseRepository


class PlotRepository(BaseRepository):
    """Plotテーブルに関するDB操作をまとめたMixin"""
    async def get_plot(self, book_id_or_branch_id: int, ep_num: int, branch_id: Optional[int] = None) -> Optional['PlotDbModel']:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        result = await self.session.execute(
            select(Plot).where(Plot.branch_id == target_branch_id).where(Plot.ep_num == ep_num)
        )
        plot = result.scalar_one_or_none()
        if not plot:
            return None
        from src.models import PlotDbModel
        return PlotDbModel(**self._parse_row(self._to_dict(plot), ['scenes', 'next_hook', 'healed_fields']))
    async def get_all_plots(self, book_id_or_branch_id: int, branch_id: Optional[int] = None) -> List['PlotDbModel']:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        result = await self.session.execute(
            select(Plot).where(Plot.branch_id == target_branch_id).order_by(Plot.ep_num)
        )
        plots = result.scalars().all()
        from src.models import PlotDbModel
        return [PlotDbModel(**self._parse_row(self._to_dict(p), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score'])) for p in plots]

    async def get_plots_with_tension(self, book_id: int, from_ep: int = 1, to_ep: int = 9999) -> List[PlotDbModel]:
        """指定範囲のプロットをtension順に取得する（波パターン分析用）"""
        result = await self.session.execute(
            select(Plot)
            .where(Plot.branch_id == book_id)
            .where(Plot.ep_num.between(from_ep, to_ep))
            .order_by(Plot.ep_num)
        )
        plots = result.scalars().all()
        from src.models import PlotDbModel
        return [PlotDbModel(**self._parse_row(self._to_dict(p), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score'])) for p in plots]
    @retry_on_lock()
    async def create_or_replace_plot(
        self, book_id: int, ep_num: int, thought_process: str, title: str, summary: str, detailed_blueprint: str,
        next_hook: str, tension: int, tension_delta: int = 0, catharsis: int = 0, love_meter: int = 0, is_catharsis: bool = False, catharsis_type: str = "なし",
        scenes: Any = None, status: str = "expanded", misunderstanding_gap: str = "",
        lite_model_director_notes: str = "", script_content: str = "",
        current_chain_phase: str = "Friction",
        resolution_style: str = "Cheat", burned_cost_or_loot: str = "なし",
        antagonist_status: str = "現状維持", thematic_milestone: str = "なし",
        state_integrity_score: int = 100, emotional_resonance_score: int = 0, healed_fields: Any = None, branch_id: int = 1,
        is_micro_catharsis: bool = False, information_asymmetry_level: float = 0.0,
        cost_score: float = 0.0,
        qol_delta: int = 0, discovery_item: str = "", sanctuary_event: str = "", is_locked: bool = False,
        stress: Optional[int] = None, is_plot_twist: bool = False,
        is_simulation: bool = False, simulation_id: Optional[str] = None,
        candidates: str = "[]",
        erotic_intensity: int = 0
    ) -> None:
        if stress is not None:
            tension_delta = stress
        sim_id = simulation_id if simulation_id is not None else ""
        result = await self.session.execute(
            select(Plot).where(Plot.branch_id == branch_id).where(Plot.ep_num == ep_num).where(Plot.simulation_id == sim_id)
        )
        plot_obj = result.scalar_one_or_none()
        if not plot_obj:
            plot_obj = Plot(branch_id=branch_id, ep_num=ep_num, simulation_id=sim_id)
            self.session.add(plot_obj)

        plot_obj.book_id = book_id
        plot_obj.thought_process = thought_process
        plot_obj.title = title
        plot_obj.summary = summary
        plot_obj.detailed_blueprint = detailed_blueprint
        plot_obj.next_hook = json.dumps(next_hook, ensure_ascii=False) if isinstance(next_hook, (dict, list)) else (next_hook or "{}")
        plot_obj.tension = tension
        plot_obj.tension_delta = tension_delta
        plot_obj.catharsis = catharsis
        plot_obj.love_meter = love_meter
        plot_obj.is_catharsis = is_catharsis
        plot_obj.catharsis_type = catharsis_type
        plot_obj.scenes = json.dumps(scenes, ensure_ascii=False) if isinstance(scenes, (list, dict)) else (scenes or "[]")
        plot_obj.status = status
        plot_obj.misunderstanding_gap = misunderstanding_gap
        plot_obj.lite_model_director_notes = lite_model_director_notes
        plot_obj.script_content = script_content
        plot_obj.current_chain_phase = current_chain_phase
        plot_obj.resolution_style = resolution_style
        plot_obj.is_plot_twist = is_plot_twist
        plot_obj.burned_cost_or_loot = burned_cost_or_loot
        plot_obj.antagonist_status = antagonist_status
        plot_obj.thematic_milestone = thematic_milestone
        plot_obj.state_integrity_score = state_integrity_score
        plot_obj.emotional_resonance_score = emotional_resonance_score
        plot_obj.healed_fields = json.dumps(healed_fields, ensure_ascii=False) if isinstance(healed_fields, list) else (healed_fields or "[]")
        plot_obj.is_micro_catharsis = is_micro_catharsis
        plot_obj.information_asymmetry_level = information_asymmetry_level
        plot_obj.cost_score = cost_score
        plot_obj.qol_delta = qol_delta
        plot_obj.discovery_item = discovery_item
        plot_obj.sanctuary_event = sanctuary_event
        plot_obj.is_locked = is_locked
        plot_obj.is_simulation = is_simulation
        plot_obj.simulation_id = sim_id
        plot_obj.candidates = candidates
        plot_obj.erotic_intensity = erotic_intensity
    @retry_on_lock()
    async def save_plot(self, branch_id: int, ep_num: int, plot: Any) -> None:
        """Pydanticモデル（PlotEpisode）をデータベースのplotテーブルに一括登録/更新する。"""
        branch_result = await self.session.execute(select(Branch.book_id).where(Branch.id == branch_id))
        row = branch_result.fetchone()
        if not row:
            book_result = await self.session.execute(select(Book.id).order_by(Book.id.desc()).limit(1))
            latest_book = book_result.scalar_one_or_none()
            if latest_book:
                book_id = latest_book
            else:
                raise ValueError(f"Branch with ID {branch_id} does not exist and no books found.")
        else:
            book_id = row[0]

        next_hook_data = {}
        if hasattr(plot, "next_hook") and plot.next_hook:
            if hasattr(plot.next_hook, "model_dump"):
                next_hook_data = plot.next_hook.model_dump()
            elif isinstance(plot.next_hook, dict):
                next_hook_data = plot.next_hook
            else:
                next_hook_data = {"type": getattr(plot.next_hook, "type", ""), "description": getattr(plot.next_hook, "description", "")}

        scenes_data = []
        if hasattr(plot, "scenes") and plot.scenes:
            for s in plot.scenes:
                if hasattr(s, "model_dump"):
                    scenes_data.append(s.model_dump())
                elif isinstance(s, dict):
                    scenes_data.append(s)

        healed_fields_data = []
        if hasattr(plot, "healed_fields") and plot.healed_fields:
            healed_fields_data = list(plot.healed_fields)

        await self.create_or_replace_plot(
            book_id=book_id,
            ep_num=ep_num,
            thought_process=getattr(plot, "thought_process", "") or "",
            title=getattr(plot, "title", "") or f"第{ep_num}話",
            summary=getattr(plot, "one_line_summary", "") or "",
            detailed_blueprint=getattr(plot, "detailed_blueprint", "") or "",
            next_hook=next_hook_data,
            tension=int(getattr(plot, "tension", 50) or 50),
            tension_delta=int(getattr(plot, "tension_delta", 0) or 0),
            catharsis=int(getattr(plot, "catharsis", 0) or 0),
            love_meter=int(getattr(plot, "love_meter", 0) or 0),
            is_catharsis=bool(getattr(plot, "is_catharsis", False)),
            catharsis_type=getattr(plot, "catharsis_type", "なし") or "なし",
            status=getattr(plot, "status", "expanded") or "expanded",
            misunderstanding_gap=getattr(plot, "misunderstanding_gap", "") or "",
            lite_model_director_notes=getattr(plot, "lite_model_director_notes", "") or "",
            script_content=getattr(plot, "script_content", "") or "",
            current_chain_phase=getattr(plot, "current_chain_phase", "Friction") or "Friction",
            resolution_style=getattr(plot, "resolution_style", "Cheat") or "Cheat",
            is_plot_twist=bool(getattr(plot, "is_plot_twist", False)),
            burned_cost_or_loot=str(getattr(plot, "burned_cost_or_loot", "なし") or "なし"),
            antagonist_status=getattr(plot, "antagonist_status", "現状維持") or "現状維持",
            thematic_milestone=getattr(plot, "thematic_milestone", "なし") or "なし",
            state_integrity_score=int(getattr(plot, "state_integrity_score", 100) or 100),
            emotional_resonance_score=int(getattr(plot, "emotional_resonance_score", 0) or 0),
            healed_fields=healed_fields_data,
            branch_id=branch_id,
            is_micro_catharsis=bool(getattr(plot, "is_micro_catharsis", False)),
            information_asymmetry_level=float(getattr(plot, "information_asymmetry_level", 0.0) or 0.0),
            cost_score=float(getattr(plot, "cost_score", 0.0) or 0.0),
            qol_delta=int(getattr(plot, "qol_delta", 0) or 0),
            discovery_item=getattr(plot, "discovery_item", "") or "",
            sanctuary_event=getattr(plot, "sanctuary_event", "") or "",
            is_locked=bool(getattr(plot, "is_locked", False)),
            candidates=json.dumps(getattr(plot, "candidates", []), ensure_ascii=False) if hasattr(plot, "candidates") else "[]",
            erotic_intensity=int(getattr(plot, "erotic_intensity", 0) or 0)
        )
    @retry_on_lock()
    async def update_plot_status_tension_love(self, branch_id: int, ep_num: int, tension_delta: int, love_meter: int) -> None:
        await self.session.execute(
            update(Plot)
            .where(Plot.branch_id == branch_id)
            .where(Plot.ep_num == ep_num)
            .values(status='completed', tension_delta=tension_delta, love_meter=love_meter)
        )
    @retry_on_lock()
    async def reset_plot_status(self, branch_id: int, ep_num: int) -> None:
        """プロットのステータスを計画済みに戻し、設計図や個別統計を完全にリセットする"""
        await self.session.execute(
            update(Plot)
            .where(Plot.branch_id == branch_id)
            .where(Plot.ep_num == ep_num)
            .values(
                status='planned', tension_delta=0, love_meter=0,
                detailed_blueprint='', thought_process='',
                script_content='', scenes='[]', is_locked=False
            )
        )
    @retry_on_lock()
    async def update_plot_blueprint(self, branch_id: int, ep_num: int, detailed_blueprint: str) -> None:
        """プロットの設計図を直接更新する"""
        await self.session.execute(
            update(Plot)
            .where(Plot.branch_id == branch_id)
            .where(Plot.ep_num == ep_num)
            .values(detailed_blueprint=detailed_blueprint)
        )
    @retry_on_lock()
    async def update_plot_lock_status(self, branch_id: int, ep_num: int, is_locked: bool) -> None:
        """プロットのロック状態を更新する"""
        await self.session.execute(
            update(Plot)
            .where(Plot.branch_id == branch_id)
            .where(Plot.ep_num == ep_num)
            .values(is_locked=is_locked)
        )
    @retry_on_lock()
    async def delete_plots_from(self, branch_id: int, start_ep: int) -> None:
        await self.session.execute(
            delete(Plot).where(Plot.branch_id == branch_id).where(Plot.ep_num >= start_ep)
        )
    async def get_plots_before_limit_1(self, branch_id: int, ep_num: int) -> Optional['PlotDbModel']:
        """ep_num より前の最新プロットを1件取得（直前プロットの状態参照用）"""
        result = await self.session.execute(
            select(Plot)
            .where(Plot.branch_id == branch_id)
            .where(Plot.ep_num < ep_num)
            .order_by(Plot.ep_num.desc())
            .limit(1)
        )
        plot = result.scalar_one_or_none()
        if not plot:
            return None
        from src.models import PlotDbModel
        return PlotDbModel(**self._parse_row(self._to_dict(plot), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score']))
    async def get_plots_between(self, branch_id: int, start_ep: int, end_ep: int) -> List['PlotDbModel']:
        """start_ep〜end_ep の範囲のプロットを取得"""
        result = await self.session.execute(
            select(Plot)
            .where(Plot.branch_id == branch_id)
            .where(Plot.ep_num.between(start_ep, end_ep))
            .order_by(Plot.ep_num)
        )
        plots = result.scalars().all()
        from src.models import PlotDbModel
        return [PlotDbModel(**self._parse_row(self._to_dict(p), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score'])) for p in plots]

    @retry_on_lock()
    async def add_foreshadowing(self, book_id: int, branch_id: int, fw_id: str, description: str, placement_ep: int, importance: int = 1, note: str = "") -> None:
        """伏線を新しく登録する"""
        fw = Foreshadowing(
            book_id=book_id,
            branch_id=branch_id,
            fw_id=fw_id,
            description=description,
            placement_ep=placement_ep,
            importance=importance,
            note=note,
            status="pending"
        )
        self.session.add(fw)

    @retry_on_lock()
    async def update_foreshadowing_recovery(self, fw_id: str, recovery_ep: int, note: str = "") -> None:
        """伏線の回収エピソードを登録し、ステータスを recovered に更新する"""
        await self.session.execute(
            update(Foreshadowing)
            .where(Foreshadowing.fw_id == fw_id)
            .values(recovery_ep=recovery_ep, status="recovered", note=note)
        )

    async def get_unrecovered_foreshadowings(self, book_id: int, branch_id: int = 1) -> List[Foreshadowing]:
        """未回収の伏線一覧を取得する"""
        result = await self.session.execute(
            select(Foreshadowing)
            .where(Foreshadowing.book_id == book_id)
            .where(Foreshadowing.branch_id == branch_id)
            .where(Foreshadowing.status == "pending")
            .order_by(Foreshadowing.placement_ep)
        )
        return result.scalars().all()

    async def get_all_foreshadowings(self, book_id: int, branch_id: int = 1) -> List[Foreshadowing]:
        """全ての伏線一覧を取得する"""
        result = await self.session.execute(
            select(Foreshadowing)
            .where(Foreshadowing.book_id == book_id)
            .where(Foreshadowing.branch_id == branch_id)
            .order_by(Foreshadowing.placement_ep)
        )
        return result.scalars().all()

    async def get_tension_curve(self, branch_id: int) -> List[Dict[str, Any]]:
        """指定したブランチの全エピソードの緊張感スコアを時系列で取得する"""
        result = await self.session.execute(
            select(Plot.ep_num, Plot.tension)
            .where(Plot.branch_id == branch_id)
            .order_by(Plot.ep_num)
        )
        rows = result.all()
        return [{"ep_num": row[0], "tension": row[1]} for row in rows]

    @retry_on_lock()
    async def save_character_arc(self, book_id: int, branch_id: int, character_id: int, ep_num: int, state_summary: str, arc_delta: Optional[str] = None, trigger_event: Optional[str] = None, confidence: float = 1.0) -> None:
        """キャラクターアークの状態を保存または更新する"""
        result = await self.session.execute(
            select(CharacterArc).where(
                CharacterArc.branch_id == branch_id,
                CharacterArc.character_id == character_id,
                CharacterArc.ep_num == ep_num
            )
        )
        arc_obj = result.scalar_one_or_none()
        if not arc_obj:
            arc_obj = CharacterArc(branch_id=branch_id, character_id=character_id, ep_num=ep_num)
            self.session.add(arc_obj)

        arc_obj.book_id = book_id
        arc_obj.state_summary = state_summary
        arc_obj.arc_delta = arc_delta
        arc_obj.trigger_event = trigger_event
        arc_obj.confidence = confidence

    async def get_character_arc_history(self, branch_id: int, character_id: int) -> List[CharacterArc]:
        """特定のキャラクターの全エピソードにおけるアーク履歴を取得する"""
        result = await self.session.execute(
            select(CharacterArc)
            .where(CharacterArc.branch_id == branch_id)
            .where(CharacterArc.character_id == character_id)
            .order_by(CharacterArc.ep_num)
        )
        return result.scalars().all()

    async def get_latest_character_arc(self, branch_id: int, character_id: int, ep_num: int) -> Optional[CharacterArc]:
        """指定エピソード以前の最新のキャラクター状態を取得する"""
        result = await self.session.execute(
            select(CharacterArc)
            .where(CharacterArc.branch_id == branch_id)
            .where(CharacterArc.character_id == character_id)
            .where(CharacterArc.ep_num < ep_num)
            .order_by(CharacterArc.ep_num.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
