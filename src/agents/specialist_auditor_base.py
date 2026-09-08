"""Specialist Auditor base class.

Phase 2 / Guideline #3: 8 specialist auditors share this interface.
Each specialist receives an AgentContext-like dict and returns a
SpecialistAuditResult with a 0-100 score, feedback dict and suggestions.
LLM-using specialists may raise LLMUnavailableError to fall back to the
rule-based path; the aggregator captures this and records a missing status.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMUnavailableError(RuntimeError):
    """Raised by an LLM-using specialist when the LLM is down. The
    aggregator will catch this and fall back to the rule-based path of
    the same specialist.
    """


@dataclass
class ActionableDiff:
    """Represents a concrete, actionable text improvement suggestion."""
    location: str  # e.g., "第1段落 冒頭", "末尾2文"
    original_quote: str  # 原文の問題箇所
    improved_suggestion: str  # 改善後の具体的な文章
    rationale: str  # 改善すべき理由・背景

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "original_quote": self.original_quote,
            "improved_suggestion": self.improved_suggestion,
            "rationale": self.rationale,
        }


@dataclass
class SpecialistAuditResult:
    specialist_name: str
    score: float  # 0-100
    feedback: dict[str, Any] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    degraded: bool = False  # True if fell back to rule-based path
    error: str | None = None
    confidence: float = 1.0  # 0-1, LLM self-assessed confidence
    reasoning_trace: str = ""  # Reasoning summary for debugging
    llm_raw_response: str = ""  # Raw LLM output for auditing
    actionable_diffs: list[ActionableDiff] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "specialist_name": self.specialist_name,
            "score": self.score,
            "feedback": self.feedback,
            "suggestions": list(self.suggestions),
            "degraded": self.degraded,
            "error": self.error,
            "confidence": self.confidence,
            "reasoning_trace": self.reasoning_trace,
            "llm_raw_response": self.llm_raw_response,
            "actionable_diffs": [
                d.to_dict() if hasattr(d, "to_dict") else d
                for d in self.actionable_diffs
            ],
        }


def parse_actionable_diffs(raw_diffs: Any) -> list[ActionableDiff]:
    """Robustly parse actionable diffs from various LLM response formats."""
    diffs: list[ActionableDiff] = []
    if not raw_diffs:
        return diffs

    if isinstance(raw_diffs, dict):
        raw_diffs = [raw_diffs]
    elif not isinstance(raw_diffs, list):
        return diffs

    for item in raw_diffs:
        if not isinstance(item, dict):
            continue

        loc = (
            item.get("location")
            or item.get("target")
            or item.get("section")
            or item.get("part")
            or item.get("箇所")
            or ""
        )
        orig = (
            item.get("original_quote")
            or item.get("original")
            or item.get("quote")
            or item.get("before")
            or item.get("原文")
            or ""
        )
        impr = (
            item.get("improved_suggestion")
            or item.get("improved")
            or item.get("suggestion")
            or item.get("after")
            or item.get("rewrite")
            or item.get("改善案")
            or ""
        )
        rat = (
            item.get("rationale")
            or item.get("reason")
            or item.get("why")
            or item.get("background")
            or item.get("理由")
            or ""
        )

        if str(orig).strip() or str(impr).strip():
            diffs.append(
                ActionableDiff(
                    location=str(loc).strip(),
                    original_quote=str(orig).strip(),
                    improved_suggestion=str(impr).strip(),
                    rationale=str(rat).strip(),
                )
            )
    return diffs


def parse_audit_response_json(text_resp: str) -> tuple[float, str, list[str], float, str, list[ActionableDiff]]:
    """Robustly extract and parse audit fields from arbitrary LLM text."""
    import json
    import re

    score = 50.0
    critique = ""
    suggestions: list[str] = []
    confidence = 0.5
    reasoning = ""
    actionable_diffs: list[ActionableDiff] = []

    # 1. Markdown コードブロック抽出 (```json ... ``` または ``` ... ```)
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text_resp, re.DOTALL)
    json_candidate = code_block_match.group(1) if code_block_match else None

    # 2. コードブロックがない場合は最外郭の波括弧
    if not json_candidate:
        brace_match = re.search(r"\{.*\}", text_resp, re.DOTALL)
        if brace_match:
            json_candidate = brace_match.group(0)

    parsed_dict: dict[str, Any] | None = None
    if json_candidate:
        # トレイリングカンマや制御文字の除去クリーンアップ
        cleaned = re.sub(r",\s*([\]}])", r"\1", json_candidate)
        try:
            parsed_dict = json.loads(cleaned)
        except Exception:
            try:
                # 二重引用符エスケープなど軽微な修正
                parsed_dict = json.loads(json_candidate)
            except Exception:
                parsed_dict = None

    if isinstance(parsed_dict, dict):
        try:
            score = float(parsed_dict.get("score", 50.0))
        except (ValueError, TypeError):
            score = 50.0

        critique = str(parsed_dict.get("critique", parsed_dict.get("feedback", "")))

        suggs = parsed_dict.get("suggestions", parsed_dict.get("suggestion", []))
        if isinstance(suggs, list):
            suggestions = [str(s) for s in suggs if s]
        elif isinstance(suggs, str) and suggs.strip():
            suggestions = [suggs.strip()]

        try:
            confidence = float(parsed_dict.get("confidence", 0.5))
        except (ValueError, TypeError):
            confidence = 0.5

        reasoning = str(parsed_dict.get("reasoning", parsed_dict.get("rationale", "")))

        # 揺らぎキーからの diffs 抽出
        raw_diffs = (
            parsed_dict.get("actionable_diffs")
            or parsed_dict.get("diffs")
            or parsed_dict.get("actionable_diff")
            or parsed_dict.get("improvements")
            or []
        )
        actionable_diffs = parse_actionable_diffs(raw_diffs)

    # 3. JSON パース完全失敗時の正規表現フォールバック
    if not critique:
        score_match = re.search(r"(?:score|スコア|点数)[:：\s]*([0-9]+(?:\.[0-9]+)?)", text_resp, re.IGNORECASE)
        if score_match:
            try:
                score = float(score_match.group(1))
            except ValueError:
                score = 50.0
        critique = text_resp[:300].strip()
        suggestions = ["表現と構成の再確認"]
        confidence = 0.3
        reasoning = "JSON parse failed, regex fallback"

    # スコア範囲クリップ (0.0〜100.0)
    score = max(0.0, min(100.0, round(score, 1)))
    confidence = max(0.0, min(1.0, round(confidence, 2)))

    return score, critique, suggestions, confidence, reasoning, actionable_diffs


class SpecialistAuditor(ABC):
    """Abstract base for all 8 specialist auditors.

    Subclasses MUST define ``specialist_name`` (one of:
    consistency / creativity / reader_hook / emotion_curve / style /
    factual / structure / multimodal) and implement ``audit``.
    """

    specialist_name: str = ""

    # Confidence threshold for auto-fallback (0.0-1.0)
    # If LLM returns confidence below this, fall back to rule-based
    CONFIDENCE_THRESHOLD = 0.6

    # Multi-sampling settings (enabled via environment variable AUDIT_LLM_SAMPLES)
    # Number of samples to take for variance checking
    LLM_SAMPLE_COUNT = 1
    # Maximum allowed standard deviation across samples (0-100)
    LLM_MAX_SCORE_STDEV = 15.0

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm
        from src.agents.specialists.windowing import NovelSectionExtractor
        self.section_extractor = NovelSectionExtractor()
        # Allow runtime override via environment variable
        import os
        samples = os.getenv("AUDIT_LLM_SAMPLES")
        if samples:
            try:
                self.LLM_SAMPLE_COUNT = max(1, int(samples))
            except ValueError:
                pass

    @abstractmethod
    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Run audit on the context. MUST be async and MUST return a
        SpecialistAuditResult with score in [0, 100].
        """

    async def _safe_audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        try:
            result = await self.audit(ctx)
            # Auto-fallback if LLM confidence is too low
            if result.confidence < self.CONFIDENCE_THRESHOLD:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"{self.specialist_name}: low confidence {result.confidence:.2f} "
                    f"< {self.CONFIDENCE_THRESHOLD}, falling back to rule-based"
                )
                fb = self._fallback(ctx)
                fb.error = f"low_confidence: {result.confidence:.2f}"
                fb.feedback["llm_confidence"] = result.confidence
                fb.feedback["llm_reasoning"] = result.reasoning_trace
                return fb
            return result
        except LLMUnavailableError as e:
            fb = self._fallback(ctx)
            fb.degraded = True
            fb.error = f"llm_unavailable: {e}"
            return fb
        except Exception as e:
            return SpecialistAuditResult(
                specialist_name=self.specialist_name,
                score=0.0,
                feedback={"exception": str(e)},
                suggestions=[],
                degraded=True,
                error=repr(e),
            )

    safe_audit = _safe_audit

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback used when LLM is unavailable.
        Default: return a neutral 50 score. Specialists override this
        to provide meaningful rule-based scoring.
        """
        return SpecialistAuditResult(
            specialist_name=self.specialist_name,
            score=50.0,
            feedback={"fallback": "rule-based default"},
            suggestions=["LLM unavailable; consider manual review"],
            degraded=True,
        )

    async def _judge_with_llm(
        self,
        prompt: str,
        system_prompt: str | None = None,
        inject_anchors: bool = True,
    ) -> tuple[float, str, list[str], float, str, str, list[ActionableDiff]]:
        """Common LLM judge method for all specialist auditors (Step 63, enhanced in Phase 4).

        Forces structured evaluation and returns (score, critique, suggestions, confidence, reasoning, raw, actionable_diffs).
        Raises LLMUnavailableError if LLM is missing or call fails.
        """
        if not self.llm:
            raise LLMUnavailableError("LLM client is not configured on specialist")

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"【システム役割】\n{system_prompt}\n\n{prompt}"

        # Step 7: アンカープリセットの自動注入（未注入かつ有効な場合）
        if inject_anchors and self.specialist_name:
            try:
                from src.agents.specialists.anchors import get_anchor_preset
                anchor_preset = get_anchor_preset(self.specialist_name)
                if anchor_preset and "【採点基準アンカー" not in full_prompt:
                    anchor_text = anchor_preset.format_for_prompt()
                    full_prompt = f"{full_prompt}\n\n{anchor_text}"
            except Exception:
                pass  # アンカー取得失敗時は元プロンプトを維持

        # JSON 出力指示を付加（confidence, reasoning, actionable_diffs追加）
        instruction_suffix = (
            "\n\n必ず以下のJSON形式のみを出力してください（Markdownコードブロック可）:\n"
            "{\n"
            '  "score": 0〜100の数値,\n'
            '  "critique": "詳細な講評・評価理由",\n'
            '  "suggestions": ["具体的な改善提案1", "改善提案2"],\n'
            '  "confidence": 0.0〜1.0の数値（自己評価の信頼度）,\n'
            '  "reasoning": "判定根拠の要約（100字以内）",\n'
            '  "actionable_diffs": [\n'
            "    {\n"
            '      "location": "指摘箇所の位置（例: 冒頭段落、末尾結末など）",\n'
            '      "original_quote": "問題のある原文の抜粋",\n'
            '      "improved_suggestion": "改善後の具体的なリライト提案文",\n'
            '      "rationale": "書き換え理由"\n'
            "    }\n"
            "  ]\n"
            "}"
        )
        if "必ず以下のJSON形式" not in full_prompt:
            full_prompt += instruction_suffix

        import inspect
        import json
        import re
        import statistics

        async def _single_judge(p: str) -> tuple[float, str, list[str], float, str, str, list[ActionableDiff]]:
            """Single LLM call returning parsed result."""
            try:
                if hasattr(self.llm, "ainvoke"):
                    raw = self.llm.ainvoke(p)
                elif hasattr(self.llm, "generate"):
                    raw = self.llm.generate(p)
                elif hasattr(self.llm, "invoke"):
                    raw = self.llm.invoke(p)
                elif callable(self.llm):
                    raw = self.llm(p)
                else:
                    raise LLMUnavailableError(f"Unsupported LLM interface: {type(self.llm)}")

                if inspect.isawaitable(raw):
                    raw = await raw

                text_resp = str(getattr(raw, "content", raw)).strip()
                score, critique, suggestions, confidence, reasoning, actionable_diffs = parse_audit_response_json(text_resp)
                return score, critique, suggestions, confidence, reasoning, text_resp, actionable_diffs

            except LLMUnavailableError:
                raise
            except Exception as e:
                raise LLMUnavailableError(f"LLM call failed: {e}") from e

        # Multi-sample mode: run multiple times and check variance
        scores: list[float] = []
        critiques: list[str] = []
        suggestions_list: list[list[str]] = []
        confidences: list[float] = []
        reasonings: list[str] = []
        raw_responses: list[str] = []
        all_diffs: list[ActionableDiff] = []

        for _ in range(self.LLM_SAMPLE_COUNT):
            sc, cr, sg, cf, reas, raw, diffs = await _single_judge(full_prompt)
            scores.append(sc)
            critiques.append(cr)
            suggestions_list.append(sg)
            confidences.append(cf)
            reasonings.append(reas)
            raw_responses.append(raw)
            if diffs and not all_diffs:
                all_diffs = diffs

        # Check variance
        if len(scores) >= 2:
            stdev = statistics.stdev(scores)
            if stdev > self.LLM_MAX_SCORE_STDEV:
                raise LLMUnavailableError(
                    f"High score variance across {self.LLM_SAMPLE_COUNT} samples: "
                    f"scores={scores}, stdev={stdev:.1f} > {self.LLM_MAX_SCORE_STDEV}"
                )

        # Return average score, first critique/suggestions, average confidence, combined reasoning
        avg_score = statistics.mean(scores)
        avg_confidence = statistics.mean(confidences)
        combined_reasoning = " | ".join(reasonings[:3])  # Limit to first 3
        combined_raw = " || ".join(raw_responses[:2])  # Limit to first 2

        return (
            round(avg_score, 1),
            critiques[0] if critiques else "",
            suggestions_list[0] if suggestions_list else [],
            round(avg_confidence, 2),
            combined_reasoning,
            combined_raw,
            all_diffs,
        )


__all__ = [
    "SpecialistAuditor",
    "SpecialistAuditResult",
    "ActionableDiff",
    "LLMUnavailableError",
    "parse_actionable_diffs",
    "parse_audit_response_json",
]