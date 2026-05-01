import json
from typing import Any, Dict, List, Tuple, Union
from database import DataRepository, PlotDbModel, CharacterDbModel

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
                except Exception:
                    reg = {}
                lines.append(
                    f"■ {c.name} ({c.role})\n"
                    f"  - Personality/Ability: {reg.get('personality', '')} / {reg.get('ability', '')}\n"
                    f"  - IronConst: {reg.get('iron_constraint') or reg.get('iron_const') or ''}\n"
                    f"  - State: {char_states.get(c.name, '通常')}\n"
                )
        return "\n".join(lines) if lines else "キャラクター情報なし"

    async def build_past_context(self, book_id: int, end_ep: int) -> str:
        all_past = await self.repo.get_chapters_before(book_id, end_ep)
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
            except Exception: pass

        ctx = ""
        if cumulative_summary: ctx += f"【物語の全体像（マクロ因果）】\n{cumulative_summary}\n\n"
        if threads:
            ctx += "【未解決の因果レジャー（伏線元帳）】\n"
            for t in threads:
                if isinstance(t, dict):
                    ctx += f"- [{t.get('status', 'Active')}] 内容: {t.get('description', '未定義')} (発生: 第{t.get('setup_episode', '?')}話 / 解消目標: 第{t.get('target_resolve_episode') or 'TBD'}話)\n"
                else:
                    ctx += f"- [Active] 内容: {str(t)}\n"
            ctx += "\n"
        
        ctx += "【直近の出来事と確定した事実】\n"
        for c in reversed(recent): ctx += f"- 第{c.ep_num}話: {c.summary} (確定事実: {c.ai_insight if c.ai_insight else 'なし'})\n"
        return ctx.strip()

    async def get_optimal_context(self, book_id: int, ep_num: int, plots: Union[PlotDbModel, List[PlotDbModel]], all_chars: List[CharacterDbModel]) -> Tuple[str, str]:
        """プロット生成時に最適な文体・過去文脈を構築する"""
        all_past = await self.repo.get_chapters_before(book_id, ep_num)
        char_states = {}
        if all_past:
            ws = all_past[0].world_state if isinstance(all_past[0].world_state, dict) else json.loads(all_past[0].world_state or "{}")
            char_states = ws.get("character_states", {})
        
        # 基本コンテキスト
        base_past_ctx = await self.build_past_context(book_id, ep_num)

        # RAGによる動的検索の追加
        # plots が単一オブジェクトかリストかに関わらず、安全に設計図テキストを抽出する
        if isinstance(plots, list):
            query = " ".join([p.detailed_blueprint or "" for p in plots])
        else:
            query = plots.detailed_blueprint or ""

        rag_ctx = await self.repo.get_relevant_past_logs(book_id, ep_num, query_text=query)
        
        prev_ctx = base_past_ctx + "\n" + rag_ctx
        char_ctx = self.filter_active_characters(plots, all_chars, char_states, recent_ctx=prev_ctx)
        return char_ctx, prev_ctx

    async def get_optimal_context_split(self, book_id: int, ep_num: int, plot: PlotDbModel, chars: List[CharacterDbModel]) -> Tuple[str, str, str]:
        """不変設定と動的状態に分けてコンテキストを構築"""
        all_past = await self.repo.get_chapters_before(book_id, ep_num)
        char_states = {}
        if all_past:
            try:
                ws = json.loads(all_past[0].world_state) if isinstance(all_past[0].world_state, str) else all_past[0].world_state
                char_states = ws.get("character_states", {})
            except Exception: pass
        
        prev_ctx = await self.build_past_context(book_id, ep_num)
        static_lines, dynamic_lines = [], []
        # 本文執筆時は、台本(script_content)も考慮して登場キャラを特定
        search_area = (plot.detailed_blueprint or "") + " " + (plot.script_content or "")
        for c in chars:
            is_important = any(role in (c.role or "") for role in ["主人公", "ヒロイン", "悪役", "ライバル"])
            if not c.name or (c.name not in search_area and not is_important): continue
            try:
                if hasattr(c, "registry_data"):
                    reg = c.registry_data if isinstance(c.registry_data, dict) else (json.loads(c.registry_data) if isinstance(c.registry_data, str) else {})
                elif hasattr(c, "model_dump"):
                    reg = c.model_dump()
                else:
                    reg = {}
            except Exception:
                reg = {}
            static_lines.append(f"■ {c.name} ({c.role}): {reg.get('tone')}\n  Ability: {reg.get('ability')}\n  IronConst: {reg.get('iron_constraint') or reg.get('iron_const') or ''}")
            # 案2: 動的変数（所在・負傷・所持品）を明示的に抽出
            state = char_states.get(c.name, "通常")
            dynamic_lines.append(f"■ {c.name}: {state}")
        return "\n".join(static_lines), "\n".join(dynamic_lines), prev_ctx
