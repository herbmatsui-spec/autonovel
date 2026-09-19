"""
Rule base, registry, regex rule, and core deterministic rewrite rules.
"""

from __future__ import annotations

import abc
import random
import re
from typing import Any, Callable, Dict, List, Optional, Union

from src.narrative.subtext_engine.models import (
    DialogueBlock,
    RewriteResult,
    RewriteRuleModel,
    SubtextContext,
)


class RuleBase(abc.ABC):
    """Abstract base class for all rewrite rules."""

    def __init__(
        self,
        rule_id: str,
        name: str = "",
        priority: int = 100,
        final: bool = False,
        skip_if_matched: bool = False,
        enabled: bool = True,
        tags: Optional[List[str]] = None,
        description: str = "",
    ) -> None:
        self.id = rule_id
        self.name = name or rule_id
        self.priority = priority
        self.final = final
        self.skip_if_matched = skip_if_matched
        self.enabled = enabled
        self.tags = tags or []
        self.description = description

    @abc.abstractmethod
    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        """Applies the rewrite rule to a DialogueBlock."""
        raise NotImplementedError

    def to_model(self) -> RewriteRuleModel:
        """Converts rule metadata into a serializable model."""
        return RewriteRuleModel(
            id=self.id,
            name=self.name,
            pattern=getattr(self, "pattern_str", ""),
            replacement=getattr(self, "replacement_str", ""),
            priority=self.priority,
            final=self.final,
            skip_if_matched=self.skip_if_matched,
            enabled=self.enabled,
            tags=self.tags,
            description=self.description,
        )


class RegexRule(RuleBase):
    """Regular-expression-based rewrite rule."""

    def __init__(
        self,
        rule_id: str,
        pattern: Union[str, re.Pattern],
        replacement: Union[str, Callable[[re.Match], str]],
        name: str = "",
        priority: int = 100,
        final: bool = False,
        skip_if_matched: bool = False,
        enabled: bool = True,
        flags: int = 0,
        tags: Optional[List[str]] = None,
        description: str = "",
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            name=name,
            priority=priority,
            final=final,
            skip_if_matched=skip_if_matched,
            enabled=enabled,
            tags=tags,
            description=description,
        )
        if isinstance(pattern, str):
            self.pattern_str = pattern
            self.regex = re.compile(pattern, flags)
        else:
            self.pattern_str = pattern.pattern
            self.regex = pattern

        self.replacement = replacement
        self.replacement_str = replacement if isinstance(replacement, str) else "<callable>"

    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(success=True, modified=False, block=block)

        if self.skip_if_matched and self.id in block.applied_rules:
            return RewriteResult(success=True, modified=False, block=block)

        original_text = block.raw_text()
        if not original_text:
            return RewriteResult(success=True, modified=False, block=block)

        # Check if regex matches
        match = self.regex.search(original_text)
        if not match:
            return RewriteResult(success=True, modified=False, block=block)

        try:
            if callable(self.replacement):
                new_text = self.regex.sub(self.replacement, original_text)
            else:
                new_text = self.regex.sub(self.replacement, original_text)
        except Exception as err:
            return RewriteResult(
                success=False,
                modified=False,
                block=block,
                diff_summary=f"Regex error in rule {self.id}: {err}",
            )

        if new_text != original_text:
            new_lines = new_text.split("\n")
            new_block = block.clone()
            new_block.lines = new_lines
            new_block.applied_rules.append(self.id)
            return RewriteResult(
                success=True,
                modified=True,
                block=new_block,
                applied_rule_id=self.id,
                diff_summary=f"Rule {self.id} modified text.",
            )

        return RewriteResult(success=True, modified=False, block=block)


class RuleRegistry:
    """Registry managing rewrite rules in priority order."""

    _instance: Optional[RuleRegistry] = None

    def __init__(self) -> None:
        self._rules: Dict[str, RuleBase] = {}

    @classmethod
    def get_instance(cls) -> RuleRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Resets the singleton registry for tests."""
        cls._instance = cls()

    def register(self, rule: RuleBase, overwrite: bool = True) -> None:
        if rule.id in self._rules and not overwrite:
            raise ValueError(f"Rule '{rule.id}' already exists in registry.")
        self._rules[rule.id] = rule

    def unregister(self, rule_id: str) -> Optional[RuleBase]:
        return self._rules.pop(rule_id, None)

    def get(self, rule_id: str) -> Optional[RuleBase]:
        return self._rules.get(rule_id)

    def list_rules(self, enabled_only: bool = False) -> List[RuleBase]:
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        # Sort by priority ascending (lower number = earlier execution)
        rules.sort(key=lambda r: (r.priority, r.id))
        return rules

    def clear(self) -> None:
        self._rules.clear()


# ==============================================================================
# Core Rewrite Rules (Steps 7 - 14)
# ==============================================================================

EXPLANATORY_BEATS = [
    "沈黙が張り詰める。",
    "視線を逸らす。",
    "指先で杯を弄ぶ。",
    "マントの裾を握りしめる。",
    "深く息を吐く。",
]


class ExplanatoryCompressRule(RuleBase):
    """Step 7: Compresses 3 or more consecutive explanatory dialogue lines,

    keeping the last line and converting the preceding ones into subtext beats.
    """

    def __init__(
        self,
        rule_id: str = "rule_01_explanatory_compress",
        priority: int = 10,
        beats: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            name="Explanatory Dialogue Compression",
            priority=priority,
            final=False,
            tags=["compression", "dialogue_beat"],
            description="Compress 3+ consecutive lines of dialogue into beats and final line.",
        )
        self.beats = beats or EXPLANATORY_BEATS

    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(success=True, modified=False, block=block)

        # Fast path check: must have at least 3 dialogue lines
        raw = block.raw_text()
        if raw.count("「") < 3:
            return RewriteResult(success=True, modified=False, block=block)

        dialogue_line_indices = [
            i for i, line in enumerate(block.lines)
            if line.strip().startswith("「") and line.strip().endswith("」")
        ]

        # Check for sequences of 3 or more consecutive dialogue lines
        sequences: List[List[int]] = []
        cur_seq: List[int] = []
        for idx in dialogue_line_indices:
            if not cur_seq or idx == cur_seq[-1] + 1:
                cur_seq.append(idx)
            else:
                if len(cur_seq) >= 3:
                    sequences.append(cur_seq)
                cur_seq = [idx]
        if len(cur_seq) >= 3:
            sequences.append(cur_seq)

        if not sequences:
            return RewriteResult(success=True, modified=False, block=block)

        new_block = block.clone()
        # Seed random choice deterministically if context provides turn_index
        rnd = random.Random(context.turn_index if context else 42)

        # Process sequences in reverse index order to avoid shifting issues
        for seq in reversed(sequences):
            last_line = new_block.lines[seq[-1]]
            beat = rnd.choice(self.beats)
            # Replace sequence with beat + last_line
            new_block.lines[seq[0] : seq[-1] + 1] = [f"（{beat}）", last_line]

        new_block.applied_rules.append(self.id)
        return RewriteResult(
            success=True,
            modified=True,
            block=new_block,
            applied_rule_id=self.id,
            diff_summary="Compressed explanatory dialogue into beats.",
        )


EMOTION_ACTION_DICT = {
    "悲し": "悲しげな表情で、拳を握りしめ",
    "怒っ": "怒気を孕んだ瞳で、テーブルを叩く",
    "恨ん": "冷たく目を細め、静かに息を呑み",
    "悔し": "奥歯を噛み締め、爪を手のひらに食い込ませ",
    "寂し": "微かに肩を震わせ、虚空を見つめ",
    "腹立たし": "眉根を寄せ、荒々しく首を振り",
    "ムカつ": "舌打ちを呑み込み、顔を背け",
}


class EmotionToActionRule(RuleBase):
    """Step 8: Replaces direct emotion claims with physical subtext actions."""

    def __init__(
        self,
        rule_id: str = "rule_02_emotion_to_action",
        priority: int = 20,
        actions: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            name="Emotion to Action Converter",
            priority=priority,
            tags=["emotion", "action_beat"],
            description="Replaces direct emotion words with physical stage direction beats.",
        )
        self.actions = actions or EMOTION_ACTION_DICT
        pattern_keys = "|".join(re.escape(k) for k in self.actions.keys())
        # Matches e.g. 「私は悲しい」「怒っている」 but avoids simple negation like 悲しくない
        self.regex = re.compile(
            rf"([^\w]*)({pattern_keys})(い|いだ|いよ|くて|かった|ている|てる|た)?([。！？…」]*)",
            re.UNICODE,
        )

    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(success=True, modified=False, block=block)

        modified = False
        new_lines: List[str] = []

        for line in block.lines:
            matched_key = None
            for key in self.actions:
                if key in line and f"{key}くない" not in line and f"{key}くはない" not in line:
                    matched_key = key
                    break

            if matched_key:
                action_desc = self.actions[matched_key]
                # If line is enclosed dialogue 「...」, insert stage direction before or after
                if line.startswith("「") and line.endswith("」"):
                    inner = line[1:-1]
                    # Sub out the emotion word or soften it
                    inner_subbed = re.sub(rf"{matched_key}(い|くて|かった|ている|てる|た)?", "……", inner)
                    cleaned_inner = re.sub(r"……+", "……", inner_subbed).strip()
                    if not cleaned_inner or cleaned_inner == "……":
                        cleaned_line = f"（{action_desc}）"
                    else:
                        cleaned_line = f"「{cleaned_inner}」——{action_desc}。"
                else:
                    cleaned_line = f"{line}——{action_desc}。"

                new_lines.append(cleaned_line)
                modified = True
            else:
                new_lines.append(line)

        if modified:
            new_block = block.clone()
            new_block.lines = new_lines
            new_block.applied_rules.append(self.id)
            return RewriteResult(
                success=True,
                modified=True,
                block=new_block,
                applied_rule_id=self.id,
                diff_summary="Replaced direct emotions with subtext actions.",
            )

        return RewriteResult(success=True, modified=False, block=block)


IRONY_POOL = [
    "そう。好きにすればいいわ",
    "君に何が分かる",
    "期待しないことにする",
]


class CausalToIronyRule(RuleBase):
    """Step 9: Transforms causal explanatory connectives into ironic deflection or beats."""

    def __init__(
        self,
        rule_id: str = "rule_03_causal_to_irony",
        priority: int = 30,
        irony_pool: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            name="Causal Connective to Irony",
            priority=priority,
            tags=["irony", "causal"],
            description="Transforms logical explanatory connectives into ironic subtext.",
        )
        self.irony_pool = irony_pool or IRONY_POOL
        self.regex = re.compile(r"(なぜなら|理由は|〜から|〜ため|ゆえに)(.+)")

    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(success=True, modified=False, block=block)

        rnd = random.Random(context.turn_index if context else 101)
        modified = False
        new_lines: List[str] = []

        for line in block.lines:
            match = self.regex.search(line)
            if match:
                irony = rnd.choice(self.irony_pool)
                # If within dialogue brackets
                if line.startswith("「") and line.endswith("」"):
                    new_line = f"「……{irony}」"
                else:
                    new_line = f"……{irony}。"
                new_lines.append(new_line)
                modified = True
            else:
                new_lines.append(line)

        if modified:
            new_block = block.clone()
            new_block.lines = new_lines
            new_block.applied_rules.append(self.id)
            return RewriteResult(
                success=True,
                modified=True,
                block=new_block,
                applied_rule_id=self.id,
                diff_summary="Converted causal explanations to irony.",
            )

        return RewriteResult(success=True, modified=False, block=block)


class SubjectiveInternalizeRule(RuleBase):
    """Step 10: Internalizes subjective declarations ('私は〜思う/感じる/信じる') into physical beats."""

    def __init__(
        self,
        rule_id: str = "rule_04_subjective_internalize",
        priority: int = 40,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            name="Subjective Assertion Internalization",
            priority=priority,
            tags=["subjective", "stage_direction"],
            description="Internalizes '私は〜と思う/感じる' declarations into stage directions.",
        )
        self.regex = re.compile(
            r"「?(?:私|僕|俺)は(.+?)(?:と)?(思う|感じる|信じて|確信し)(?:ます|る|ている|ています)?」?[。！？]?"
        )

    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(success=True, modified=False, block=block)

        modified = False
        new_lines: List[str] = []

        for line in block.lines:
            match = self.regex.search(line)
            if match:
                content = match.group(1).strip()
                verb = match.group(2).strip()
                replacement = f"（……{content}{verb}げな素振りを見せ、言葉を飲み込む）"
                new_lines.append(replacement)
                modified = True
            else:
                new_lines.append(line)

        if modified:
            new_block = block.clone()
            new_block.lines = new_lines
            new_block.applied_rules.append(self.id)
            return RewriteResult(
                success=True,
                modified=True,
                block=new_block,
                applied_rule_id=self.id,
                diff_summary="Internalized subjective assertion into stage beat.",
            )

        return RewriteResult(success=True, modified=False, block=block)


COLD_PHRASES = [
    "二度目はない",
    "選ぶのは君だ",
    "覚えておくことね",
    "その言葉、忘れずに",
]

THREAT_ACTIONS = [
    "冷笑を浮かべ、静かに背を向けた",
    "瞳の奥に冷たい殺意を宿し、杯を置いた",
    "息を殺し、相手の首筋へ視線を走らせた",
]


class ThreatSubtextRule(RuleBase):
    """Step 11: Converts direct threat/declaration words into cold subtext phrases + threat action."""

    def __init__(
        self,
        rule_id: str = "rule_05_threat_subtext",
        priority: int = 50,
        cold_phrases: Optional[List[str]] = None,
        threat_actions: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            name="Threat Direct to Subtext",
            priority=priority,
            final=True,
            tags=["threat", "cold"],
            description="Replaces direct threats with cold restrained phrases and tense actions.",
        )
        self.cold_phrases = cold_phrases or COLD_PHRASES
        self.threat_actions = threat_actions or THREAT_ACTIONS
        self.regex = re.compile(r"(殺す|殺し|潰す|潰し|復讐|後悔させ|許さな)(?:てやる|てみせる|ぞ|わ|よ|い)?")

    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(success=True, modified=False, block=block)

        rnd = random.Random(context.turn_index if context else 505)
        modified = False
        new_lines: List[str] = []

        for line in block.lines:
            if self.regex.search(line):
                phrase = rnd.choice(self.cold_phrases)
                action = rnd.choice(self.threat_actions)
                new_line = f"「……{phrase}」——{action}。"
                new_lines.append(new_line)
                modified = True
            else:
                new_lines.append(line)

        if modified:
            new_block = block.clone()
            new_block.lines = new_lines
            new_block.applied_rules.append(self.id)
            return RewriteResult(
                success=True,
                modified=True,
                block=new_block,
                applied_rule_id=self.id,
                diff_summary="Converted direct threat into cold subtext.",
            )

        return RewriteResult(success=True, modified=False, block=block)


class ComplianceSubvertRule(RuleBase):
    """Step 12: Subverts direct compliance/agreement ('はい/わかりました') into irony (60%) or silent beat (40%)."""

    def __init__(
        self,
        rule_id: str = "rule_06_compliance_subvert",
        priority: int = 60,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            name="Compliance Subversion",
            priority=priority,
            final=True,
            tags=["compliance", "subversion"],
            description="Subverts agreement into irony or silent refusal.",
        )
        self.regex = re.compile(
            r"^「?(はい|わかりました|承知|従う|言う通り)(?:いたし|し)?(?:です|ました)?[。!]?」?$"
        )

    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(success=True, modified=False, block=block)

        rnd = random.Random(context.turn_index if context else 606)
        modified = False
        new_lines: List[str] = []

        for line in block.lines:
            match = self.regex.match(line.strip())
            if match:
                # 60% irony, 40% silent beat
                val = rnd.random()
                if val < 0.6:
                    new_line = "「……仰せのままに。望む結果が得られるとよいですが」"
                else:
                    new_line = "（無言のままわずかに頭を下げ、冷めた眼差しを向けた）"
                new_lines.append(new_line)
                modified = True
            else:
                new_lines.append(line)

        if modified:
            new_block = block.clone()
            new_block.lines = new_lines
            new_block.applied_rules.append(self.id)
            return RewriteResult(
                success=True,
                modified=True,
                block=new_block,
                applied_rule_id=self.id,
                diff_summary="Subverted simple compliance.",
            )

        return RewriteResult(success=True, modified=False, block=block)


class AddressDistanceRule(RuleBase):
    """Step 13: Adjusts honorifics and pronouns to create psychological distance based on context."""

    def __init__(
        self,
        rule_id: str = "rule_07_address_distance",
        priority: int = 70,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            name="Addressing Distance Modulation",
            priority=priority,
            tags=["distance", "honorific"],
            description="Modulates addressing and honorifics based on psychological distance.",
        )
        self.regex = re.compile(r"(君|お前|あなた)([、。！？\s]|$)")

    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(success=True, modified=False, block=block)

        # Distance logic: if context is hostile or superior/inferior, replace with cold address or gaze
        if context and context.relationship in ["enemy", "former_ally"]:
            replacement_address = "貴方"
        elif context and context.power_dynamic == "superior":
            replacement_address = "お前"
        else:
            replacement_address = "君"

        modified = False
        new_lines: List[str] = []

        for line in block.lines:
            if self.regex.search(line):
                new_line = self.regex.sub(rf"{replacement_address}\2", line)
                if new_line != line:
                    new_lines.append(new_line)
                    modified = True
                    continue
            new_lines.append(line)

        if modified:
            new_block = block.clone()
            new_block.lines = new_lines
            new_block.applied_rules.append(self.id)
            return RewriteResult(
                success=True,
                modified=True,
                block=new_block,
                applied_rule_id=self.id,
                diff_summary="Adjusted addressing distance.",
            )

        return RewriteResult(success=True, modified=False, block=block)


# ==============================================================================
# Extension Rules (Step 14: Rules 8 - 15)
# ==============================================================================

class ExtensionRule(RuleBase):
    """Generic template for extension rules (Rules 8-15)."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        pattern: str,
        replacement: str,
        priority: int = 80,
        tags: Optional[List[str]] = None,
        description: str = "",
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            name=name,
            priority=priority,
            tags=tags or ["extension"],
            description=description,
        )
        self.pattern_str = pattern
        self.replacement_str = replacement
        self.regex = re.compile(pattern)

    def apply(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(success=True, modified=False, block=block)

        modified = False
        new_lines: List[str] = []
        for line in block.lines:
            if self.regex.search(line):
                new_line = self.regex.sub(self.replacement_str, line)
                new_lines.append(new_line)
                modified = True
            else:
                new_lines.append(line)

        if modified:
            new_block = block.clone()
            new_block.lines = new_lines
            new_block.applied_rules.append(self.id)
            return RewriteResult(
                success=True,
                modified=True,
                block=new_block,
                applied_rule_id=self.id,
                diff_summary=f"Applied extension rule {self.id}.",
            )

        return RewriteResult(success=True, modified=False, block=block)


def create_extension_rules() -> List[ExtensionRule]:
    """Creates default extension rules (Rules 8-15)."""
    return [
        ExtensionRule(
            rule_id="rule_08_apology_deflection",
            name="Apology Deflection",
            pattern=r"「?(ごめんなさい|すみません|申し訳ありません)[。！？]?」?",
            replacement=r"「……謝られても、何も戻らない」",
            priority=80,
            tags=["apology", "subtext"],
            description="Replaces plain apology with heavy subtext deflection.",
        ),
        ExtensionRule(
            rule_id="rule_09_hesitation_stutter",
            name="Hesitation Breath",
            pattern=r"「([あえうお])っ、([あえうお])っ」",
            replacement=r"（息を詰まらせ、喉をかすかに震わせる）",
            priority=85,
            tags=["hesitation", "beat"],
            description="Replaces stutter with physiological tension beat.",
        ),
        ExtensionRule(
            rule_id="rule_10_secretive_whisper",
            name="Secretive Whisper",
            pattern=r"「ここだけの話(だけど|ですが)」",
            replacement=r"「……壁に耳があるわ」",
            priority=90,
            tags=["secret", "tension"],
            description="Sharpens secretive opening to tense caution.",
        ),
        ExtensionRule(
            rule_id="rule_11_rhetorical_evasion",
            name="Rhetorical Evasion",
            pattern=r"「どうしてそんなこと(を聞くの|言うの)？」",
            replacement=r"「……それを知って、どうするつもり？」",
            priority=95,
            tags=["evasion", "counter_question"],
            description="Turns defensive question into counter-probing question.",
        ),
        ExtensionRule(
            rule_id="rule_12_condescending_politeness",
            name="Condescending Politeness",
            pattern=r"「ご親切にどうも」",
            replacement=r"「……余計なお気遣い、感服いたしますわ」",
            priority=100,
            tags=["politeness", "irony"],
            description="Sharpens superficial politeness into condescending edge.",
        ),
        ExtensionRule(
            rule_id="rule_13_gaze_aversion",
            name="Gaze Aversion Beat",
            pattern=r"「見ないで(よ|ください)！」",
            replacement=r"（咄嗟に顔を背け、手の甲で表情を隠す）",
            priority=105,
            tags=["gaze", "beat"],
            description="Replaces exclamation with protective bodily gesture.",
        ),
        ExtensionRule(
            rule_id="rule_14_monologue_cutoff",
            name="Monologue Cutoff",
            pattern=r"「独り言(よ|さ|だ)」",
            replacement=r"「……なんでもない。忘れて」",
            priority=110,
            tags=["monologue", "cutoff"],
            description="Turns self-justifying mutter into cold cutoff.",
        ),
        ExtensionRule(
            rule_id="rule_15_unspoken_tension",
            name="Unspoken Tension Trailing",
            pattern=r"「言いたいことはそれだけ(か|よ)？」",
            replacement=r"「……それ以上は、お互いのためにならない」",
            priority=115,
            tags=["tension", "boundary"],
            description="Converts challenge into a dangerous unspoken boundary line.",
        ),
    ]
