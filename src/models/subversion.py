# src/models/subversion.py
from __future__ import annotations
import hashlib
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator
from src.models.base import BaseEngine, MODEL_CONFIG_DEFAULTS


class SubversionPattern(BaseModel):
    pattern_type: Literal["A", "B", "C"] = Field(description="裏切りパターン種別")
    trigger_ep: int = Field(description="発火話数")
    description: str = Field(description="具体的な裏切り内容")
    cost: str = Field(description="代償・リスク・後々の伏線")
    payoff_hint: str = Field(default="", description="将来の回収ヒント")
    setup_ep: int | None = Field(default=None, description="伏線設置話数（遡及込み）")

    model_config = MODEL_CONFIG_DEFAULTS


class SubversionEngine(BaseEngine):
    schedule: list[SubversionPattern] = Field(default_factory=list)
    last_applied_ep: int = Field(default=0)
    applied_patterns: list[SubversionPattern] = Field(default_factory=list)
    interval: int = Field(default=3, description="裏切り間隔（話数）")
    enabled: bool = Field(default=True)
    pattern_weights: dict[str, float] = Field(
        default_factory=lambda: {"A": 0.4, "B": 0.3, "C": 0.3}
    )
    seed: str = Field(default="", description="再現性用シード")

    @classmethod
    def get_routing_keys(cls) -> list[str]:
        return ["schedule", "last_applied_ep", "applied_patterns", "interval", "enabled", "pattern_weights", "seed"]

    @model_validator(mode="after")
    def _normalize_weights(self) -> "SubversionEngine":
        total = sum(self.pattern_weights.values())
        if abs(total - 1.0) > 0.001 or total == 0:
            self.pattern_weights = {"A": 0.4, "B": 0.3, "C": 0.3}
        else:
            self.pattern_weights = {k: v/total for k, v in self.pattern_weights.items()}
        return self

    def plan_schedule(self, total_eps: int, start_ep: int = 1) -> list[SubversionPattern]:
        schedule = []
        for ep in range(start_ep + self.interval - 1, total_eps + 1, self.interval):
            seed = f"subversion_{self.seed}_{ep}_{total_eps}_{self.interval}"
            hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
            rand = (hash_val % 100) / 100.0

            cum = 0.0
            selected = "A"
            for pat, weight in self.pattern_weights.items():
                cum += weight
                if rand <= cum:
                    selected = pat
                    break

            pattern = SubversionPattern(
                pattern_type=selected,  # type: ignore[arg-type]
                trigger_ep=ep,
                description=self._generate_description(selected, ep),
                cost=self._generate_cost(selected, ep),
                payoff_hint=self._generate_payoff_hint(selected, ep),
                setup_ep=max(1, ep - 2)
            )
            schedule.append(pattern)
        self.schedule = schedule
        return schedule

    def _generate_description(self, pat: str, ep: int) -> str:
        return {
            "A": f"第{ep}話：チート能力覚醒の代償として「人間性の一部（感情/記憶/倫理）」を永久に失う",
            "B": f"第{ep}話：追放の張本人・小悪党が、一族を守るため自ら囮となり命を散らす覚悟を見せる",
            "C": f"第{ep}話：ざまぁ完遂の瞬間、主人公と敵対者の双方を呑み込む「第三の災厄（古代兵器/外宇宙存在/概念的崩壊）」が出現",
        }[pat]

    def _generate_cost(self, pat: str, ep: int) -> str:
        return {
            "A": "能力使用ごとに人格が侵食。最終話で「誰だったか忘れる」エンドリスク",
            "B": "読者の共感ベクトルが逆転。以降、敵キャラへの感情移入が主軸に移る",
            "C": "復讐完了が無期限延期。新たな共通目的（生存/世界救済）へ強制ピボット",
        }[pat]

    def _generate_payoff_hint(self, pat: str, ep: int) -> str:
        return {
            "A": "失った人間性の欠片が、最終決戦で「鍵」になる伏線",
            "B": "悪役の遺した「遺言/アイテム/血統」が主人公の真の力を引き出す",
            "C": "第三の災厄の正体＝主人公の力の源泉（因果律ループ）",
        }[pat]

    def apply_to_arc(self, arc: Any, ep_num: int) -> Any:
        if not self.enabled:
            return arc
        for pat in self.schedule:
            if pat.trigger_ep == ep_num:
                if not hasattr(arc, "subversion"):
                    arc.subversion = pat
                arc.thematic_milestone = f"【裏切り-{pat.pattern_type}】{pat.description}"
                self.last_applied_ep = ep_num
                self.applied_patterns.append(pat)
                break
        return arc

    def apply_to_beat(self, beat: Any, ep_num: int) -> Any:
        if not self.enabled:
            return beat
        for pat in self.schedule:
            if pat.trigger_ep == ep_num:
                beat.mission = f"【裏切り-{pat.pattern_type}】{pat.description}"
                beat.visual_scene_focus = f"代償の可視化：{pat.cost}"
                beat.tension_target = min(1.0, getattr(beat, "tension_target", 0.5) + 0.3)
                break
        return beat

    def validate_coherence(self, total_eps: int) -> list[str]:
        errors = []
        eps = [p.trigger_ep for p in self.schedule]
        if len(eps) != len(set(eps)):
            errors.append("重複発火話数あり")
        for i in range(1, len(eps)):
            if eps[i] - eps[i-1] < self.interval:
                errors.append(f"間隔不足: {eps[i-1]}話→{eps[i]}話")
        for pat in self.schedule:
            if pat.payoff_hint and pat.trigger_ep > total_eps - 5:
                errors.append(f"第{pat.trigger_ep}話の回収ヒントが終盤すぎる（残り{total_eps - pat.trigger_ep}話）")
        return errors
