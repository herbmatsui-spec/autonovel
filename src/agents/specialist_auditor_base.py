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
        }


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
    ) -> tuple[float, str, list[str], float, str, str]:
        """Common LLM judge method for all specialist auditors (Step 63).

        Forces structured evaluation and returns (score, critique, suggestions, confidence, reasoning, raw).
        Raises LLMUnavailableError if LLM is missing or call fails.
        """
        if not self.llm:
            raise LLMUnavailableError("LLM client is not configured on specialist")

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"【システム役割】\n{system_prompt}\n\n{prompt}"

        # JSON 出力指示を付加（confidence, reasoning追加）
        instruction_suffix = (
            "\n\n必ず以下のJSON形式のみを出力してください（Markdownコードブロック可）:\n"
            "{\n"
            '  "score": 0〜100の数値,\n'
            '  "critique": "詳細な講評・評価理由",\n'
            '  "suggestions": ["具体的な改善提案1", "改善提案2"],\n'
            '  "confidence": 0.0〜1.0の数値（自己評価の信頼度）,\n'
            '  "reasoning": "判定根拠の要約（100字以内）"\n'
            "}"
        )
        if "必ず以下のJSON形式" not in full_prompt:
            full_prompt += instruction_suffix

        import inspect
        import json
        import re
        import statistics

        async def _single_judge(p: str) -> tuple[float, str, list[str], float, str, str]:
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

                # JSON 抽出試行
                score = 50.0
                critique = ""
                suggestions = []
                confidence = 0.5
                reasoning = ""

                json_match = re.search(r"\{.*\}", text_resp, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                        score = float(data.get("score", 50.0))
                        critique = str(data.get("critique", ""))
                        suggs = data.get("suggestions", [])
                        if isinstance(suggs, list):
                            suggestions = [str(s) for s in suggs]
                        elif isinstance(suggs, str):
                            suggestions = [suggs]
                        confidence = float(data.get("confidence", 0.5))
                        reasoning = str(data.get("reasoning", ""))
                    except Exception:
                        pass

                # JSONパース失敗時の正規表現フォールバック
                if not critique:
                    score_match = re.search(r"(?:score|スコア|点数)[:：\s]*([0-9]+(?:\.[0-9]+)?)", text_resp, re.IGNORECASE)
                    if score_match:
                        score = float(score_match.group(1))
                    critique = text_resp[:300]
                    suggestions = ["表現と構成の再確認"]
                    confidence = 0.3
                    reasoning = "JSON parse failed, regex fallback"

                # スコア範囲クリップ (0.0〜100.0)
                score = max(0.0, min(100.0, round(score, 1)))
                confidence = max(0.0, min(1.0, round(confidence, 2)))

                return score, critique, suggestions, confidence, reasoning, text_resp

            except Exception as e:
                if isinstance(e, LLMUnavailableError):
                    raise
                raise LLMUnavailableError(f"LLM execution error during audit: {e}") from e

        # Single sample mode (default)
        if self.LLM_SAMPLE_COUNT <= 1:
            return await _single_judge(full_prompt)

        # Multi-sample mode: run multiple times and check variance
        scores = []
        critiques = []
        suggestions_list = []
        confidences = []
        reasonings = []
        raw_responses = []

        for _ in range(self.LLM_SAMPLE_COUNT):
            s, c, sug, conf, reas, raw = await _single_judge(full_prompt)
            scores.append(s)
            critiques.append(c)
            suggestions_list.append(sug)
            confidences.append(conf)
            reasonings.append(reas)
            raw_responses.append(raw)

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
        )


__all__ = [
    "SpecialistAuditor",
    "SpecialistAuditResult",
    "LLMUnavailableError",
]