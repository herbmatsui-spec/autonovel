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

    def to_dict(self) -> dict[str, Any]:
        return {
            "specialist_name": self.specialist_name,
            "score": self.score,
            "feedback": self.feedback,
            "suggestions": list(self.suggestions),
            "degraded": self.degraded,
            "error": self.error,
        }


class SpecialistAuditor(ABC):
    """Abstract base for all 8 specialist auditors.

    Subclasses MUST define ``specialist_name`` (one of:
    consistency / creativity / reader_hook / emotion_curve / style /
    factual / structure / multimodal) and implement ``audit``.
    """

    specialist_name: str = ""

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm

    @abstractmethod
    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Run audit on the context. MUST be async and MUST return a
        SpecialistAuditResult with score in [0, 100].
        """

    async def _safe_audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        try:
            return await self.audit(ctx)
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
    ) -> tuple[float, str, list[str]]:
        """Common LLM judge method for all specialist auditors (Step 63).

        Forces structured evaluation and returns (score, critique, suggestions).
        Raises LLMUnavailableError if LLM is missing or call fails.
        """
        if not self.llm:
            raise LLMUnavailableError("LLM client is not configured on specialist")

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"【システム役割】\n{system_prompt}\n\n{prompt}"

        # JSON 出力指示を付加
        instruction_suffix = (
            "\n\n必ず以下のJSON形式のみを出力してください（Markdownコードブロック可）:\n"
            "{\n"
            '  "score": 0〜100の数値,\n'
            '  "critique": "詳細な講評・評価理由",\n'
            '  "suggestions": ["具体的な改善提案1", "改善提案2"]\n'
            "}"
        )
        if "必ず以下のJSON形式" not in full_prompt:
            full_prompt += instruction_suffix

        import inspect
        import json
        import re

        try:
            if hasattr(self.llm, "ainvoke"):
                raw = self.llm.ainvoke(full_prompt)
            elif hasattr(self.llm, "generate"):
                raw = self.llm.generate(full_prompt)
            elif hasattr(self.llm, "invoke"):
                raw = self.llm.invoke(full_prompt)
            elif callable(self.llm):
                raw = self.llm(full_prompt)
            else:
                raise LLMUnavailableError(f"Unsupported LLM interface: {type(self.llm)}")

            if inspect.isawaitable(raw):
                raw = await raw

            text_resp = str(getattr(raw, "content", raw)).strip()

            # JSON 抽出試行
            score = 50.0
            critique = ""
            suggestions = []

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
                except Exception:
                    pass

            # JSONパース失敗時の正規表現フォールバック
            if not critique:
                score_match = re.search(r"(?:score|スコア|点数)[:：\s]*([0-9]+(?:\.[0-9]+)?)", text_resp, re.IGNORECASE)
                if score_match:
                    score = float(score_match.group(1))
                critique = text_resp[:300]
                suggestions = ["表現と構成の再確認"]

            # スコア範囲クリップ (0.0〜100.0)
            score = max(0.0, min(100.0, round(score, 1)))

            return score, critique, suggestions

        except Exception as e:
            if isinstance(e, LLMUnavailableError):
                raise
            raise LLMUnavailableError(f"LLM execution error during audit: {e}") from e


__all__ = [
    "SpecialistAuditor",
    "SpecialistAuditResult",
    "LLMUnavailableError",
]