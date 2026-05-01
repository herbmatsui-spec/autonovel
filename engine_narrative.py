import json
import asyncio
import random
import threading
from typing import Any, Dict, List, Tuple, TYPE_CHECKING
from config import STRESS_CATHARSIS_THRESHOLD, STRESS_FILLER_THRESHOLD, STRESS_CLIMAX_BONUS, STRESS_HATE_GAIN_BASE, MODEL_PLOT_EXPANSION, CHEAT_DESCRIPTIONS, ROUTINE_VARIATIONS, NARRATIVE_PROPS, DAILY_MICRO_HOOKS, TRAGEDY_VARIATIONS, DEFAULT_GOLDEN_PEAKS
from engine_utils import is_light_style
from models import PlotEpisode, PlotDbModel, ChapterDbModel
import logging

if TYPE_CHECKING:
    from engine import UltimateHegemonyEngine

logger = logging.getLogger(__name__)

class PlanningStateMachine:
    """企画ウィザードの進行状態を管理する"""
    def __init__(self):
        self.current_step = 1
        self.audit_result = None
    def next_step(self): self.current_step += 1
    def prev_step(self): self.current_step = max(1, self.current_step - 1)

class PacingGraph:
    """物語の各話における情報密度や温度感（Pacing）を定義"""
    @staticmethod
    def get_instruction(ep_num: int, total_eps: int = 50, is_light: bool = False) -> Dict[str, Any]:
        if ep_num == 1:
            if is_light:
                return {"instruction": "【第1話】主人公の日常的な『ついてなさ』をコミカルに描写。チート能力による快進撃の予感を描け。", "density": "情報密度: 低", "temp": 0.85}
            return {"instruction": "【第1話】主人公の理不尽な不遇・絶望を五感で執拗に描写。最後に能力の片鱗が現れるが、無双で終わらせるな。", "density": "情報密度: 低", "temp": 0.8}
        elif 2 <= ep_num <= 4:
            return {"instruction": "【導入】能力の特異性とヒロインとの関係性を描写。小さなトラブルを代償や機転で解決させよ。", "density": "情報密度: 中", "temp": 0.8}
        elif ep_num == 5:
            return {"instruction": "【第1の爆発】1〜4話の伏線を一気に回収。最初の明確なカタルシスを描け。", "density": "情報密度: 高", "temp": 0.85}
        elif 24 <= ep_num <= 26:
            return {"instruction": "【第1部クライマックス】最大級のカタルシス。これまでの伏線を全回収せよ。", "density": "情報密度: 特高", "multiplier": 1.5, "temp": 0.9}
        elif ep_num >= total_eps - 2:
            return {"instruction": "【グランドフィナーレ】余韻を残しつつ、読者が満足できる大団円を。", "density": "情報密度: 高", "temp": 0.85}
        else:
            return {"instruction": "【展開・溜め回】物語を着実に進行させよ。新たな謎の提示、キャラの深掘り。", "density": "標準", "temp": 0.75}


class NarrativeController:
    """物語の感情曲線とフェーズ遷移を制御する（engine.pyより移譲）"""
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine
        self._local = threading.local()

    @property
    def plot_sem(self) -> asyncio.Semaphore:
        """イベントループごとにセマフォを初期化または取得する"""
        loop = asyncio.get_running_loop()
        stored_loop = getattr(self._local, "loop", None)
        if not hasattr(self._local, "sem") or stored_loop is not loop or (loop.is_closed()):
            self._local.sem = asyncio.Semaphore(4)
            self._local.loop = loop
        return self._local.sem

    def _is_climax_ep(self, ep_num: int, settings: Dict[str, Any]) -> bool:
        """指定された話数がクライマックス（アークの終点）か判定する"""
        arcs = settings.get("arcs", [])
        for arc in arcs:
            if isinstance(arc, dict) and arc.get("end_ep") == ep_num:
                return True
        # 黄金比ピークに該当する場合もクライマックス扱いとする
        return ep_num in DEFAULT_GOLDEN_PEAKS

    def get_dynamic_hate_gain(self, genre: str) -> int:
        modifiers = {
            "追放": 3.0, "復讐": 2.5, "ざまぁ": 2.0, "悪役令嬢": 1.5, "恋愛": 1.2,
            "スローライフ": 0.2, "飯テロ": 0.1, "コメディ": 0.5
        }
        multiplier = 1.0
        for key, mult in modifiers.items():
            if key in genre:
                multiplier = mult
                break
        return max(1, int(STRESS_HATE_GAIN_BASE * multiplier))

    def compute_stress_phase(self, ep_num: int, current_stress: int, is_planned_catharsis: bool, genre: str = "default") -> Dict[str, Any]:
        force_catharsis = False
        phase_instruction = ""
        adjusted_stress = current_stress

        if current_stress >= STRESS_CATHARSIS_THRESHOLD:
            force_catharsis = True
            adjusted_stress = max(0, current_stress - STRESS_CLIMAX_BONUS)
            phase_instruction = (
                f"\n\n【🚨 強制カタルシスモード 🚨】蓄積ストレス {current_stress}。全解放せよ。"
            )
        elif current_stress <= STRESS_FILLER_THRESHOLD and ep_num > 3:
            gain = self.get_dynamic_hate_gain(genre)
            adjusted_stress += gain
            phase_instruction = (
                f"\n\n【📉 ストレス蓄積モード 📉】蓄積ストレス不足。理不尽なヘイトを積め。"
            )
        elif is_planned_catharsis:
            phase_instruction = "\n\n【✨ Payoffフェーズ ✨】予定されたカタルシスを描け。"
            adjusted_stress = max(0, current_stress - STRESS_CLIMAX_BONUS // 2)
        
        return {
            "instruction": phase_instruction,
            "force_catharsis": force_catharsis,
            "next_stress": adjusted_stress
        }

    def get_stress_history_data(self, chapters: List[ChapterDbModel], plots: List[PlotDbModel]) -> List[Dict[str, Any]]:
        """各エピソードのストレス蓄積値を可視化用に整形して返す"""
        stress_data = []
        for ch in chapters:
            stress_val = 0
            for p in plots:
                if p.ep_num == ch.ep_num:
                    stress_val = p.stress or 0
                    break
            stress_data.append({"話数": ch.ep_num, "ストレス蓄積値": stress_val})
        return stress_data

    async def expand_plots(self, book_id: int, target_ep_list: list, arcs: list, reporter=None, force: bool = False) -> list:
        """エピソードプロットを1話ずつ順次生成する（engine.pyより詳細ロジックを継承）"""
        bible = await self.engine.repo.get_latest_bible(book_id)
        book = await self.engine.repo.get_book(book_id)
        if not book:
            logger.error(f"Book ID {book_id} not found.")
            return []
        chars = await self.engine.repo.get_all_characters(book_id)
        settings = (bible.settings if bible and isinstance(bible.settings, dict) else json.loads(bible.settings or "{}")) if bible else {}
        
        style_dna = json.loads(book.style_dna) if isinstance(book.style_dna, str) else (book.style_dna or {})
        genre_str = book.genre or "ファンタジー"
        is_light = is_light_style(style_dna.get("mode", ""), genre_str)

        results = []

        async def _expand_single(ep):
            if reporter and reporter.state.should_stop(): return
            
            existing = await self.engine.repo.get_plot(book_id, ep)
            # force=Trueでない限り、既に詳細な設計図がある場合はスキップ
            if not force and existing and existing.detailed_blueprint and len(existing.detailed_blueprint) > 100:
                results.append(existing)
                return

            async with self.plot_sem:
                char_ctx, prev_ctx = await self.engine.ctx_mgr.get_optimal_context(book_id, ep, existing or PlotDbModel(book_id=book_id, ep_num=ep), chars)
                pacing = PacingGraph.get_instruction(ep, book.target_eps or 50, is_light)
                
                is_climax = self._is_climax_ep(ep, settings)
                villain_inst = self.engine.pm.get_villain_instruction(genre_str)
                cheat_inst = CHEAT_DESCRIPTIONS.get(settings.get("cheat_scale", 4), "")
                
                # 多様性強制
                routine_type = random.choice(ROUTINE_VARIATIONS) + f" (Prop: {random.choice(NARRATIVE_PROPS)})"
                
                # 直近展開の重複回避
                past_plots = await self.engine.repo.get_plots_between(book_id, max(1, ep-3), ep-1)
                used_tropes = [p.catharsis_type for p in past_plots if p.catharsis_type and p.catharsis_type != "なし"]
                avoidance_inst = f"\n【🚨展開の重複禁止🚨】直近（{', '.join(used_tropes)}）と異なるカタルシスを考案せよ。" if used_tropes else ""

                # 伏線と制約の抽出 (Category B: Integration)
                foreshadowing_inst = ""
                if settings.get("foreshadowing_map"):
                    f_list = settings["foreshadowing_map"]
                    active_f = [f for f in f_list if f.get("setup_ep") == f"第{ep}話"]
                    if active_f:
                        foreshadowing_inst = "\n【今話で仕込む伏線と露出度】\n" + "\n".join([
                            f"- {f['description']} (露出度:{f.get('exposure_level', 3)}/5: 1なら隠蔽、5なら露骨に)" for f in active_f
                        ])

                constraint_inst = ""
                if settings.get("active_constraints"):
                    constraint_inst = "\n【絶対遵守すべき論理制約(Assertions)】\n" + "\n".join([f"- {c['subject']}: {c['constraint']}" for c in settings["active_constraints"]])

                mode_label = "💎 精密生成" if is_climax else "⚡ 高速生成"
                
                sys_inst = (
                    f"あなたはカクヨム1位を獲るプロデューサーです。\n"
                    f"{self.engine.pm.get_plot_common_rules()}\n"
                    "出力は必ず純粋なJSON形式で行い、解説は不要です。"
                )

                # --- STAGE 1: 構造と論理の確定 (軽量) ---
                stage1_prompt = (
                    f"【第{ep}話プロット：構造確定】{mode_label}\n"
                    f"{avoidance_inst}\n"
                    f"{foreshadowing_inst}\n"
                    f"{constraint_inst}\n"
                    f"【構造的指令】日常義務: {routine_type} / 絶望: {random.choice(TRAGEDY_VARIATIONS)}\n"
                    f"1. [thought_process]: 3ステップ思考（矛盾検証、反証、統合結論）を行え。\n"
                    f"2. [detailed_blueprint]: 2000文字の超詳細設計図を作成せよ。\n"
                    f"3. [parameters]: resolution_style, burned_cost_or_loot, antagonist_status を定義せよ。\n"
                    f"【キャラクター】\n{char_ctx}\n【文脈】\n{prev_ctx}\n"
                    "※この段階では scenes は空で構いません。"
                )

                res1 = await self.engine._generate_json(MODEL_PLOT_EXPANSION, stage1_prompt, system_instruction=sys_inst, expected_ep_num=ep)
                meta, _ = res1.unwrap_or({}, "")

                # --- STAGE 2: シーン詳細展開 (肉付け) ---
                stage2_prompt = (
                    f"【第{ep}話プロット：シーン展開】\n"
                    f"以下の設計図を元に、各シーンの具体的ビート(Beats)を肉付けせよ。\n"
                    f"【確定設計図】: {meta.get('detailed_blueprint')}\n"
                    "【指令】全シーンに対し、各ビート150文字以上の描写材料を含めた詳細な [scenes] リストを生成せよ。\n"
                    "【引き】読者が即座に次をクリックしたくなる [next_hook] を作成せよ。\n"
                )
                res2 = await self.engine._generate_json(MODEL_PLOT_EXPANSION, stage2_prompt, response_schema=PlotEpisode, system_instruction=sys_inst)
                meta_detail, _ = res2.unwrap_or({}, "")
                
                # 統合
                meta.update({
                    "scenes": meta_detail.get("scenes", []),
                    "next_hook": meta_detail.get("next_hook", {"type": "Quiet Foreshadowing", "description": "続く"}),
                    "self_critique": meta_detail.get("self_critique", "")
                })

                # 有機的結合: プロット段階で「勘違いの論理構造」が破綻していないか先行検証
                if meta.get("misunderstanding_gap"):
                    passed, steps = await self.engine.writer.logic_validator.validate_misunderstanding_flow(meta.get("detailed_blueprint", ""), meta.get("misunderstanding_gap", ""))
                    if not passed and reporter:
                        reporter.report(f"⚠️ 第{ep}話のプロット構造に論理的不備を検知: {', '.join(steps)}", "warning")

                # 有機的結合: 生成されたプロットを即座に論理監査
                audit_res = await self.engine.auditor.audit_plot(book_id, ep, meta.get("detailed_blueprint", ""), meta.get("script_content", ""))
                if not audit_res.is_consistent and audit_res.severity == "Critical":
                    if reporter:
                        reporter.report(f"⚠️ 第{ep}話のプロットに重大な矛盾を検知: {audit_res.conflict_points[0]}", "warning")
                
                await self.engine.repo.create_or_replace_plot(
                    book_id=book_id, ep_num=ep,
                    thought_process=meta.get("thought_process", ""),
                    title=meta.get("title", f"第{ep}話"),
                    summary=meta.get("one_line_summary", ""),
                    detailed_blueprint=meta.get("detailed_blueprint", "") or meta.get("summary", ""),
                    next_hook=json.dumps(meta.get("next_hook", {}), ensure_ascii=False) if isinstance(meta.get("next_hook"), dict) else str(meta.get("next_hook", "続く")),
                    tension=meta.get("tension", 50),
                    stress=meta.get("stress", 0), catharsis=meta.get("catharsis", 0),
                    love_meter=meta.get("love_meter", 0),
                    is_catharsis=meta.get("is_catharsis", is_climax),
                    catharsis_type=meta.get("catharsis_type", "ざまぁ" if is_climax else "なし"),
                    scenes=meta.get("scenes", []),
                    status="planned",
                    misunderstanding_gap=meta.get("misunderstanding_gap", ""),
                    lite_model_director_notes=meta.get("self_critique", ""),
                    script_content=meta.get("script_content", ""),
                    current_chain_phase=meta.get("current_chain_phase", "Hate")
                )
                
                # メタデータに ep_num が欠落している場合を補完して結果に追加
                meta["ep_num"] = ep
                results.append(meta)
        await asyncio.gather(*[_expand_single(ep) for ep in target_ep_list])
        results.sort(key=lambda x: x.get("ep_num", 0))
        return results
