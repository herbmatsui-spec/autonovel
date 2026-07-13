import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel

from src.backend.database import CharacterDbModel, DataRepository, PlotDbModel
from src.models import CharacterRegistry

logger = logging.getLogger(__name__)

class ImmutableInput(BaseModel):
    past_summary: str
    active_subplots: List[str]
    locked_foreshadowings: List[str]
    static_character_profiles: Dict[str, str]

class SystemConfig(BaseModel):
    active_constraints: List[Dict[str, str]]
    pacing_instruction: str

class DynamicState(BaseModel):
    character_states: Dict[str, str]
    current_tension: int
    unresolved_threads: List[str]

class ContextData(BaseModel):
    immutable: ImmutableInput
    config: SystemConfig
    dynamic: DynamicState


class ContextManager:
    """プロンプト用文脈（長期記憶）の構築"""
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def filter_active_characters(self, plots: Union[PlotDbModel, List[PlotDbModel]], all_chars: List[CharacterDbModel], char_states: Dict[str, str], recent_ctx: str = "") -> str:
        plot_list = plots if isinstance(plots, list) else [plots]
        # 検索範囲を拡大：設計図だけでなく、あらすじや台本案からもキャラを検出
        search_area = " ".join([
            (p.detailed_blueprint or "") + " " +
            (p.summary or "") + " " +
            (p.script_content or "")
            for p in plot_list
        ])

        lines = []
        for c in all_chars:
            if not c.name: continue
            # 重要キャラクター（主人公・ヒロイン・ヴィラン・ライバル）は常に含めるか、登場が確認された場合のみに絞る
            is_important = any(role in (c.role or "") for role in ["主人公", "ヒロイン", "悪役", "ライバル"])
            if (c.name in search_area) or (c.name in recent_ctx) or is_important:
                try:
                    if hasattr(c, "registry_data"):
                        reg = c.registry_data if isinstance(c.registry_data, dict) else (json.loads(c.registry_data) if isinstance(c.registry_data, str) else {})
                    elif hasattr(c, "model_dump"):
                        reg = c.model_dump()
                    else:
                        reg = {}
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse registry_data for character {getattr(c, 'name', 'unknown')}: {e}")
                    reg = {}
                except Exception as e:
                    logger.error(f"Unexpected error reading character data: {e}")
                    reg = {}
                lines.append(
                    f"■ {c.name} ({c.role})\n"
                    f"  - Personality/Ability: {reg.get('personality', '')} / {reg.get('ability', '')}\n"
                    f"  - IronConst: {reg.get('iron_constraint') or reg.get('iron_const') or ''}\n"
                    f"  - State: {char_states.get(c.name, '通常')}\n"
                )
        return "\n".join(lines) if lines else "キャラクター情報なし"

    async def build_past_context(self, book_id: int, end_ep: int, active_char_names: Optional[List[str]] = None) -> str:
        book = await self.repo.get_book(book_id)
        branch_id = book.current_branch_id if book and book.current_branch_id else 1
        all_past = await self.repo.get_chapters_before(branch_id, end_ep)
        recent = all_past[:3]
        cumulative_summary = ""
        threads = []
        char_states = {}
        if all_past:
            try:
                # 直近の数話から、有効なデータを遡って探索する（1話前のデータが壊れていても記憶を維持）
                # all_past は ep_num 降順
                for chap in all_past[:10]:
                    ws = json.loads(chap.world_state) if isinstance(chap.world_state, str) else chap.world_state
                    if not isinstance(ws, dict):
                        continue
                    if not cumulative_summary and ws.get("cumulative_summary"):
                        cumulative_summary = ws["cumulative_summary"]
                    if not char_states and ws.get("character_states"):
                        char_states = ws.get("character_states", {})
                    if not threads:
                        threads = ws.get("story_threads", [])
                    if cumulative_summary and threads: break
            except (json.JSONDecodeError, AttributeError) as e:
                logger.debug(f"Could not parse world_state at line 89: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error building past context: {e}")

        ctx = ""
        if cumulative_summary: ctx += f"【物語の全体像（マクロ因果）】\n{cumulative_summary}\n\n"
        if threads:
            ctx += "【未解決の因果レジャー（伏線元帳）】\n"
            filtered_threads = []
            for t in threads:
                if isinstance(t, dict):
                    status = t.get('status', 'Active')
                    if status in ('Dormant', 'Closed'):
                        continue
                    desc = t.get('description', '未定義')
                    if active_char_names:
                        # 伏線に関連するキャラがいずれか含まれているか、またはキャラ名への言及がない汎用伏線なら残す
                        has_active_char = any(name in desc for name in active_char_names)
                        if not has_active_char and any(k in desc for k in char_states.keys() if k not in active_char_names):
                            continue
                    filtered_threads.append(
                        f"- [{status}] 内容: {desc} (発生: 第{t.get('setup_episode', '?')}話 / 解消目標: 第{t.get('target_resolve_episode') or 'TBD'}話)"
                    )
                else:
                    desc_str = str(t)
                    if active_char_names:
                        has_active_char = any(name in desc_str for name in active_char_names)
                        if not has_active_char and any(k in desc_str for k in char_states.keys() if k not in active_char_names):
                            continue
                    filtered_threads.append(f"- [Active] 内容: {desc_str}")

            if filtered_threads:
                ctx += "\n".join(filtered_threads) + "\n\n"
            else:
                ctx += "- （関連する未解決の伏線なし）\n\n"

        ctx += "【直近の出来事と確定した事実】\n"
        for c in reversed(recent): ctx += f"- 第{c.ep_num}話: {c.summary} (確定事実: {c.ai_insight if c.ai_insight else 'なし'})\n"
        return ctx.strip()

    async def get_optimal_context(self, book_id: int, ep_num: int, plots: Union[PlotDbModel, List[PlotDbModel]], all_chars: List[CharacterDbModel]) -> Tuple[str, str]:
        """プロット生成時に最適な文体・過去文脈を構築する"""
        book = await self.repo.get_book(book_id)
        branch_id = book.current_branch_id if book and book.current_branch_id else 1
        all_past = await self.repo.get_chapters_before(branch_id, ep_num)
        char_states = {}
        if all_past:
            ws = all_past[0].world_state if isinstance(all_past[0].world_state, dict) else json.loads(all_past[0].world_state or "{}")
            char_states = ws.get("character_states", {})

        # 検索範囲を拡大
        plot_list = plots if isinstance(plots, list) else [plots]
        search_area = " ".join([
            (p.detailed_blueprint or "") + " " +
            (p.summary or "") + " " +
            (p.script_content or "")
            for p in plot_list
        ])
        active_char_names = [c.name for c in all_chars if c.name and c.name in search_area]

        # 基本コンテキスト
        base_past_ctx = await self.build_past_context(book_id, ep_num, active_char_names=active_char_names)

        # RAGによる動的検索の追加
        if isinstance(plots, list):
            query = " ".join([p.detailed_blueprint or "" for p in plots])
        else:
            query = plots.detailed_blueprint or ""

        rag_ctx = await self.repo.get_relevant_past_logs(branch_id, ep_num, query_text=query)

        prev_ctx = base_past_ctx + "\n" + rag_ctx
        char_ctx = self.filter_active_characters(plots, all_chars, char_states, recent_ctx=prev_ctx)
        return char_ctx, prev_ctx

    async def get_optimal_context_split(self, book_id: int, ep_num: int, plot: PlotDbModel, chars: List[CharacterRegistry]) -> Tuple[str, str, str]:
        """不変設定と動的状態に分けてコンテキストを構築（提案3: 視点/シーンベースのフィルタリング適用）"""
        book = await self.repo.get_book(book_id)
        branch_id = book.current_branch_id if book and book.current_branch_id else 1
        all_past = await self.repo.get_chapters_before(branch_id, ep_num)
        char_states = {}
        if all_past:
            try:
                ws = json.loads(all_past[0].world_state) if isinstance(all_past[0].world_state, str) else all_past[0].world_state
                char_states = ws.get("character_states", {})
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.debug(f"Could not parse world_state at line 172: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error in get_optimal_context_split: {e}")

        # 本文執筆時は、台本(script_content)も考慮して登場キャラを特定
        search_area = (plot.detailed_blueprint or "") + " " + (plot.script_content or "")
        active_char_names = [c.name for c in chars if c.name and c.name in search_area]

        # 提案3: 視点ベースで過去の文脈をフィルタリングして構築
        prev_ctx = await self.build_past_context(book_id, ep_num, active_char_names=active_char_names)
        static_lines, dynamic_lines = [], []

        # 主人公の特定
        mc_name = next((c.name for c in chars if c.role and "主人公" in c.role), None)
        is_mc_active = mc_name in active_char_names if mc_name else True

        for c in chars:
            if not c.name: continue
            is_important = any(role in (c.role or "") for role in ["主人公", "ヒロイン", "悪役", "ライバル"])

            # 提案3: 主人公がシーンに登場しないPOVの場合、不要な詳細情報を遮断する
            if c.name == mc_name and not is_mc_active:
                static_lines.append(f"■ {c.name} ({c.role}): （※このシーンには登場しません。メタ認知漏洩を防ぐため詳細プロファイルは非活性化されています）")
                state = char_states.get(c.name, "通常")
                dynamic_lines.append(f"■ {c.name} (不在): {state}")
                continue

            if c.name not in search_area and not is_important: continue
            try:
                if hasattr(c, "registry_data"):
                    reg = c.registry_data if isinstance(c.registry_data, dict) else (json.loads(c.registry_data) if isinstance(c.registry_data, str) else {})
                elif hasattr(c, "model_dump"):
                    reg = c.model_dump()
                else:
                    reg = {}
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse registry_data for character: {e}")
                reg = {}
            except AttributeError as e:
                logger.warning(f"Character has no registry_data attribute: {e}")
                reg = {}
            except Exception as e:
                logger.error(f"Unexpected error reading character registry: {e}")
                reg = {}
            static_lines.append(f"■ {c.name} ({c.role}): {reg.get('tone')}\n  Ability: {reg.get('ability')}\n  IronConst: {reg.get('iron_constraint') or reg.get('iron_const') or ''}")
            state = char_states.get(c.name, "通常")
            dynamic_lines.append(f"■ {c.name}: {state}")
        return "\n".join(static_lines), "\n".join(dynamic_lines), prev_ctx

    async def get_structured_context_split(self, book_id: int, ep_num: int, plot: PlotDbModel, chars: List[Any], active_constraints: List[Dict]=None, pacing_instruction: str="") -> ContextData:
        """提案6: データの構造を不変入力、システム設定、状態出力に明確に分割したモデルを返す"""
        static_str, dyn_str, prev_ctx = await self.get_optimal_context_split(book_id, ep_num, plot, chars)

        # Parse the strings back into dicts/lists for the structured model (mock implementation for architectural transition)
        static_profiles = {}
        for line in static_str.split("\n"):
            if line.startswith("■"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    static_profiles[parts[0].replace("■ ", "").strip()] = parts[1].strip()

        char_states = {}
        for line in dyn_str.split("\n"):
            if line.startswith("■"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    char_states[parts[0].replace("■ ", "").strip()] = parts[1].strip()

        return ContextData(
            immutable=ImmutableInput(
                past_summary=prev_ctx,
                active_subplots=[],
                locked_foreshadowings=[],
                static_character_profiles=static_profiles
            ),
            config=SystemConfig(
                active_constraints=active_constraints or [],
                pacing_instruction=pacing_instruction
            ),
            dynamic=DynamicState(
                character_states=char_states,
                current_tension=50,
                unresolved_threads=[]
            )
        )


