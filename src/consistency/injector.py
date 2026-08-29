"""consistency/injector.py - Finding → LLM プロンプト注入用フォーマット"""
from typing import List

from src.consistency.findings import Finding


def format_findings_for_prompt(findings: List[Finding], max_findings: int = 20) -> str:
    """Finding リストを LLM Guardian 用プロンプト断片に変換"""
    if not findings:
        return ""

    # Limit to max_findings
    findings = findings[:max_findings]

    lines = ["[整合性チェック結果]", "以下の潜在的な問題が検出されました。執筆・検証時に留意してください:", ""]

    for i, f in enumerate(findings, 1):
        sev = f.severity.upper()
        lines.append(f"{i}. [{sev}] {f.category}: {f.description}")
        if f.evidence:
            for ev in f.evidence:
                lines.append(f"   証拠: {ev.source} - {ev.text}")
        if f.suggestion:
            lines.append(f"   提案: {f.suggestion}")
        lines.append("")

    lines.append("※ これらは自動検出されたものです。意図的な場合は却下記録を参照してください。")
    return "\n".join(lines)


def format_findings_compact(findings: List[Finding]) -> str:
    """短縮版（トークン節約用）"""
    if not findings:
        return ""
    parts = []
    for f in findings[:10]:
        parts.append(f"[{f.severity}] {f.category}: {f.description[:80]}")
    return " | ".join(parts)