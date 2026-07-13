from __future__ import annotations

"""
database/repo_plot.py - プロット(Plots)データ操作用のリポジトリMixin
"""
import json
from typing import Any, List, Optional

from sqlalchemy import delete, select, update

from src.backend.database.core import retry_with_logging
from src.backend.database.models import Book, Branch, EntertainmentCheckLog, Plot
from src.models import PlotDbModel


class PlotRepositoryMixin:
    """Plotテーブルに関するDB操作をまとめたMixin"""

    @retry_with_logging()
    async def get_plot(self, book_id_or_branch_id: int, ep_num: int, branch_id: Optional[int] = None) -> Optional[PlotDbModel]:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        async with self._get_session() as session:
            result = await session.execute(
                select(Plot).where(Plot.branch_id == target_branch_id).where(Plot.ep_num == ep_num)
            )
            plot = result.scalar_one_or_none()
            if not plot:
                return None
            return PlotDbModel(**self._parse_row(self._to_dict(plot), ['scenes', 'next_hook', 'healed_fields']))

    @retry_with_logging()
    async def get_all_plots(self, book_id_or_branch_id: int, branch_id: Optional[int] = None) -> List[PlotDbModel]:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        async with self._get_session() as session:
            result = await session.execute(
                select(Plot).where(Plot.branch_id == target_branch_id).order_by(Plot.ep_num)
            )
            plots = result.scalars().all()
            return [PlotDbModel(**self._parse_row(self._to_dict(p), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score'])) for p in plots]

    @retry_with_logging()
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
        stress: Optional[int] = None
    ) -> None:
        if stress is not None:
            tension_delta = stress

        async with self._get_session() as session:
            result = await session.execute(
                select(Plot).where(Plot.branch_id == branch_id).where(Plot.ep_num == ep_num)
            )
            plot_obj = result.scalar_one_or_none()
            if not plot_obj:
                plot_obj = Plot(branch_id=branch_id, ep_num=ep_num)
                session.add(plot_obj)

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

    @retry_with_logging()
    async def save_plot(self, branch_id: int, ep_num: int, plot: Any) -> None:
        """Pydanticモデル（PlotEpisode）をデータベースのplotテーブルに一括登録/更新する。"""
        async with self._get_session() as session:
            branch_result = await session.execute(select(Branch.book_id).where(Branch.id == branch_id))
            row = branch_result.fetchone()
            if not row:
                book_result = await session.execute(select(Book.id).order_by(Book.id.desc()).limit(1))
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
            scenes=scenes_data,
            status=getattr(plot, "status", "expanded") or "expanded",
            misunderstanding_gap=getattr(plot, "misunderstanding_gap", "") or "",
            lite_model_director_notes=getattr(plot, "lite_model_director_notes", "") or "",
            script_content=getattr(plot, "script_content", "") or "",
            current_chain_phase=getattr(plot, "current_chain_phase", "Friction") or "Friction",
            resolution_style=getattr(plot, "resolution_style", "Cheat") or "Cheat",
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
            is_locked=bool(getattr(plot, "is_locked", False))
        )

    @retry_with_logging()
    async def update_plot_status_tension_love(self, branch_id: int, ep_num: int, tension_delta: int, love_meter: int) -> None:
        async with self._get_session() as session:
            await session.execute(
                update(Plot)
                .where(Plot.branch_id == branch_id)
                .where(Plot.ep_num == ep_num)
                .values(status='completed', tension_delta=tension_delta, love_meter=love_meter)
            )

    @retry_with_logging()
    async def reset_plot_status(self, branch_id: int, ep_num: int) -> None:
        """プロットのステータスを計画済みに戻し、設計図や個別統計を完全にリセットする"""
        async with self._get_session() as session:
            await session.execute(
                update(Plot)
                .where(Plot.branch_id == branch_id)
                .where(Plot.ep_num == ep_num)
                .values(
                    status='planned', tension_delta=0, love_meter=0,
                    detailed_blueprint='', thought_process='',
                    script_content='', scenes='[]', is_locked=False
                )
            )

    @retry_with_logging()
    async def update_plot_blueprint(self, branch_id: int, ep_num: int, detailed_blueprint: str) -> None:
        """プロットの設計図を直接更新する"""
        async with self._get_session() as session:
            await session.execute(
                update(Plot)
                .where(Plot.branch_id == branch_id)
                .where(Plot.ep_num == ep_num)
                .values(detailed_blueprint=detailed_blueprint)
            )

    @retry_with_logging()
    async def update_plot_lock_status(self, branch_id: int, ep_num: int, is_locked: bool) -> None:
        """プロットのロック状態を更新する"""
        async with self._get_session() as session:
            await session.execute(
                update(Plot)
                .where(Plot.branch_id == branch_id)
                .where(Plot.ep_num == ep_num)
                .values(is_locked=is_locked)
            )

    @retry_with_logging()
    async def delete_plots_from(self, branch_id: int, start_ep: int) -> None:
        async with self._get_session() as session:
            await session.execute(
                delete(Plot).where(Plot.branch_id == branch_id).where(Plot.ep_num >= start_ep)
            )

    @retry_with_logging()
    async def get_plots_before_limit_1(self, branch_id: int, ep_num: int) -> Optional[PlotDbModel]:
        """ep_num より前の最新プロットを1件取得（直前プロットの状態参照用）"""
        async with self._get_session() as session:
            result = await session.execute(
                select(Plot)
                .where(Plot.branch_id == branch_id)
                .where(Plot.ep_num < ep_num)
                .order_by(Plot.ep_num.desc())
                .limit(1)
            )
            plot = result.scalar_one_or_none()
            if not plot:
                return None
            return PlotDbModel(**self._parse_row(self._to_dict(plot), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score']))

    @retry_with_logging()
    async def get_plots_between(self, branch_id: int, start_ep: int, end_ep: int) -> List[PlotDbModel]:
        """start_ep〜end_ep の範囲のプロットを取得"""
        async with self._get_session() as session:
            result = await session.execute(
                select(Plot)
                .where(Plot.branch_id == branch_id)
                .where(Plot.ep_num.between(start_ep, end_ep))
                .order_by(Plot.ep_num)
            )
            plots = result.scalars().all()
            return [PlotDbModel(**self._parse_row(self._to_dict(p), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score'])) for p in plots]

    @retry_with_logging()
    async def get_erotic_intensity(self, branch_id: int, ep_num: int) -> int:
        """指定エピソードの官能強度を返す。未設定なら0。"""
        async with self._get_session() as session:
            result = await session.execute(
                select(Plot)
                .where(Plot.branch_id == branch_id)
                .where(Plot.ep_num == ep_num)
            )
            plot = result.scalar_one_or_none()
            if plot is None:
                return 0
            return getattr(plot, 'erotic_intensity', 0) or 0

    @retry_with_logging()
    async def get_total_episodes(self, book_id: int) -> int:
        """指定された本の全エピソード数を取得する。"""
        async with self._get_session() as session:
            result = await session.execute(
                select(Plot.ep_num).where(Plot.book_id == book_id).order_by(Plot.ep_num.desc()).limit(1)
            )
            max_ep = result.scalar_one_or_none()
            return max_ep if max_ep is not None else 0

    @retry_with_logging()
    async def update_plot_target_tension(self, book_id: int, ep_num: int, target_tension: float) -> None:
        """プロットの目標テンション値を更新する。"""
        async with self._get_session() as session:
            await session.execute(
                update(Plot)
                .where(Plot.book_id == book_id)
                .where(Plot.ep_num == ep_num)
                .values(target_tension=target_tension)
            )

    @retry_with_logging()
    async def update_erotic_intensity(self, branch_id: int, ep_num: int, intensity: int) -> None:
        """指定エピソードの官能強度を更新する。"""
        async with self._get_session() as session:
            await session.execute(
                update(Plot)
                .where(Plot.branch_id == branch_id)
                .where(Plot.ep_num == ep_num)
                .values(erotic_intensity=max(0, min(5, intensity)))
            )

    @retry_with_logging()
    async def update_plot_quality_polish_status(self, book_id: int, ep_num: int, status: str) -> None:
        """品質磨き上げステータスを更新する。"""
        async with self._get_session() as session:
            await session.execute(
                update(Plot)
                .where(Plot.book_id == book_id)
                .where(Plot.ep_num == ep_num)
                .values(quality_polish_status=status)
            )

    @retry_with_logging()
    async def get_entertainment_check_logs_by_book(self, book_id: int) -> List[Dict[str, Any]]:
        """entertainment_check_log を book_id で取得する。"""
        async with self._get_session() as session:
            result = await session.execute(
                select(
                    EntertainmentCheckLog.ep_num,
                    EntertainmentCheckLog.interest_score,
                    EntertainmentCheckLog.physiological_reaction,
                    EntertainmentCheckLog.would_continue_reading,
                    EntertainmentCheckLog.feedback,
                    EntertainmentCheckLog.created_at,
                )
                .where(EntertainmentCheckLog.book_id == book_id)
                .order_by(EntertainmentCheckLog.ep_num.asc())
            )
            rows = result.all()
            return [
                {
                    "ep_num": r.ep_num,
                    "interest_score": r.interest_score,
                    "physiological_reaction": r.physiological_reaction,
                    "would_continue_reading": r.would_continue_reading,
                    "feedback": r.feedback,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    @retry_with_logging()
    async def save_entertainment_check_log(
        self,
        book_id: int,
        ep_num: int,
        interest_score: int,
        physiological_reaction: str,
        would_continue_reading: bool,
        feedback: str,
    ) -> None:
        """早期面白さ検証結果を entertainment_check_log に保存する。"""
        async with self._get_session() as session:
            log = EntertainmentCheckLog(
                book_id=book_id,
                ep_num=ep_num,
                interest_score=interest_score,
                physiological_reaction=physiological_reaction,
                would_continue_reading=would_continue_reading,
                feedback=feedback,
            )
            session.add(log)
            await session.flush()

