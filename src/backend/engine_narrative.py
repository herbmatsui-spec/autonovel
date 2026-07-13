import logging
import random
from typing import TYPE_CHECKING, Any, Dict, List

from config import (
    DEFAULT_GOLDEN_PEAKS,
    STRESS_CATHARSIS_THRESHOLD,
    STRESS_CLIMAX_BONUS,
    STRESS_FILLER_THRESHOLD,
    STRESS_HATE_GAIN_BASE,
)
from src.models import ChapterDbModel, PlotDbModel, NarrativeWavePattern

if TYPE_CHECKING:
    pass

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
        mid_twist_ep = total_eps // 2
        late_twist_ep = int(total_eps * 0.8)

        if ep_num == 1:
            if is_light:
                return {"instruction": "【第1話】主人公の日常的な『ついてなさ』をコミカルに描写。チート能力による快進撃の予感を描け。", "density": "情報密度: 低", "temp": 0.85}
            return {"instruction": "【第1話】主人公の理不尽な不遇・絶望を五感で執拗に描写。最後に能力の片鱗が現れるが、無双で終わらせるな。", "density": "情報密度: 低", "temp": 0.8}
        elif ep_num == mid_twist_ep:
            return {
                "instruction": "【🚨大どんでん返し（中盤）🚨】これまでの前提を覆す衝撃の事実が発覚。信頼していた味方の予期せぬ裏切りや、世界の前提がひっくり返る展開を描け。",
                "density": "情報密度: 高",
                "is_plot_twist": True,
                "temp": 0.85
            }
        elif ep_num == late_twist_ep:
            return {
                "instruction": "【🚨大どんでん返し（終盤）🚨】真の黒幕の正体発覚や、これまでのすべての真実が根底から覆るクライマックス前夜の衝撃の転換点を描け。",
                "density": "情報密度: 高",
                "is_plot_twist": True,
                "temp": 0.9
            }
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
    def __init__(self, repo, pm, ctx_mgr, generate_json, logic_validator, auditor):
        self.repo = repo
        self.pm = pm
        self.ctx_mgr = ctx_mgr
        self.generate_json = generate_json
        self.logic_validator = logic_validator
        self.auditor = auditor

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

        # Proposal 6: Fuzzy stress threshold control based on genre and random variance
        base_threshold = STRESS_CATHARSIS_THRESHOLD  # デフォルト 85
        base_filler = STRESS_FILLER_THRESHOLD        # デフォルト 35

        genre_lower = genre.lower()
        if any(x in genre_lower for x in ["コメディ", "スローライフ", "日常", "ギャグ", "飯テロ"]):
            base_threshold = 45
            base_filler = 15
        elif any(x in genre_lower for x in ["シリアス", "ダーク", "追放", "復讐", "ざまぁ"]):
            base_threshold = 100
            base_filler = 45

        # エピソードごとの再現性（シード値固定）を持たせた揺らぎを付与
        rng = random.Random(ep_num + 777)
        threshold_delta = rng.randint(-15, 15)
        filler_delta = rng.randint(-10, 10)

        effective_threshold = max(30, base_threshold + threshold_delta)
        effective_filler = max(10, base_filler + filler_delta)

        if current_stress >= effective_threshold:
            force_catharsis = True
            adjusted_stress = max(0, current_stress - STRESS_CLIMAX_BONUS)
            phase_instruction = (
                f"\n\n【🚨 強制カタルシスモード 🚨】蓄積ストレス {current_stress} (目標閾値: {effective_threshold})。全解放せよ。"
            )
        elif current_stress <= effective_filler and ep_num > 3:
            gain = self.get_dynamic_hate_gain(genre)
            adjusted_stress += gain
            phase_instruction = (
                f"\n\n【📉 ストレス蓄積モード 📉】蓄積ストレス不足 (下限閾値: {effective_filler})。理不尽なヘイトを積め。"
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

    def get_integrity_threshold(self, genre: str, prev_integrity: int = 100, engine_key: str = "") -> float:
        base = 0.6
        genre_lower = genre.lower()
        if any(x in genre_lower for x in ["シリアス", "ダーク", "復讐", "ミステリ", "推理"]):
            base = 0.7
        elif any(x in genre_lower for x in ["スローライフ", "日常", "ギャグ", "コメディ"]):
            base = 0.5
        if prev_integrity < 70:
            base += 0.1
        return min(0.9, base)


class WavePatternAnalyzer:
    """ストレス/カタルシスの波パターンを分析するクラス"""
    def __init__(self, threshold: int = 65, reset_value: int = 0):
        self.threshold = threshold
        self.reset_value = reset_value

    def analyze(self, tension_history: List[int]) -> NarrativeWavePattern:
        """tension履歴から波パターンを分析する"""
        issues: List[str] = []
        catharsis_indices: List[int] = []
        emotional_peaks: List[int] = []
        trough_markers: List[int] = []
        cumulative = 0
        prev_tension = 50

        for idx, tension in enumerate(tension_history):
            delta = tension - prev_tension
            cumulative += max(0, delta)
            prev_tension = tension

            if cumulative >= self.threshold:
                catharsis_indices.append(idx + 1)
                if cumulative >= 80:
                    emotional_peaks.append(idx + 1)
                cumulative = self.reset_value
                trough_markers.append(idx + 1)

        wave_score = self._calculate_wave_score(tension_history, catharsis_indices)
        is_healthy = len(issues) == 0

        return NarrativeWavePattern(
            stress_levels=tension_history,
            catharsis_indices=catharsis_indices,
            emotional_peaks=emotional_peaks,
            trough_markers=trough_markers,
            wave_score=wave_score,
            is_healthy=is_healthy,
            issues=issues,
        )

    def _calculate_wave_score(self, tension_history: List[int], catharsis_indices: List[int]) -> float:
        """波パターンの成熟度を0.0-100.0でスコアリング"""
        if not tension_history:
            return 0.0
        total_eps = len(tension_history)
        catharsis_count = len(catharsis_indices)
        if total_eps <= 1:
            return 50.0

        expected_catharsis = total_eps / 7
        ratio_score = min(100.0, (catharsis_count / expected_catharsis) * 100) if expected_catharsis > 0 else 0.0
        variance_score = 100.0 - min(100.0, abs(len(catharsis_indices) - expected_catharsis) * 20)
        return (ratio_score + variance_score) / 2.0

