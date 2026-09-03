"""矛盾レポート生成サービス - 監査失敗から構造化されたレポートとdiffを生成"""

from __future__ import annotations

import difflib
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConflictItem:
    """個別の矛盾項目"""

    category: str  # worldbuilding, character, plot, causality, ability, deai
    severity: str  # critical, high, medium, low
    title: str
    description: str
    field_path: str | None = None  # 該当設定のパス (例: "world_rules.magic_system.mana_cost")
    current_value: str | None = None
    suggested_value: str | None = None
    evidence_past: str = ""
    evidence_current: str = ""
    constraint_for_next: str = ""
    confidence: float = 1.0


@dataclass
class ConflictReport:
    """構造化された矛盾レポート"""

    book_id: int
    ep_num: int
    patch_review_id: int | None
    conflicts: list[ConflictItem]
    summary: str
    total_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


class ConflictReportService:
    """監査失敗から矛盾レポートを生成するサービス"""

    # カテゴリ別の重要度デフォルト
    SEVERITY_BY_CATEGORY = {
        "fast_screen": "high",
        "logical_consistency": "high",
        "deai": "medium",
        "ability_consistency": "medium",
        "causal_integrity": "high",
    }

    CATEGORY_LABELS = {
        "fast_screen": "プロット構造",
        "logical_consistency": "論理整合性",
        "deai": "AI感・文体",
        "ability_consistency": "能力整合性",
        "causal_integrity": "因果律",
    }

    def __init__(self, repo=None):
        self.repo = repo

    def generate_conflict_report(
        self,
        book_id: int,
        ep_num: int,
        failed_audits: list[dict],
        bible_snapshot: dict | None = None,
        patch_review_id: int | None = None,
    ) -> ConflictReport:
        """監査失敗リストから構造化された矛盾レポートを生成"""
        conflicts = []

        for audit in failed_audits:
            audit_type = audit.get("type", "unknown")
            feedback = audit.get("feedback", "")
            severity = audit.get("severity", self.SEVERITY_BY_CATEGORY.get(audit_type, "medium"))

            # カテゴリからフィールドパスを推定
            field_path = self._infer_field_path(audit_type, feedback, bible_snapshot)

            # 現在値と推奨値を抽出
            current_value, suggested_value = self._extract_values(
                audit_type, feedback, bible_snapshot
            )

            conflict = ConflictItem(
                category=audit_type,
                severity=severity,
                title=self.CATEGORY_LABELS.get(audit_type, audit_type),
                description=feedback,
                field_path=field_path,
                current_value=current_value,
                suggested_value=suggested_value,
                confidence=0.8,  # デフォルト信頼度
            )
            conflicts.append(conflict)

        # サマリー生成
        summary = self._generate_summary(conflicts)

        # 重要度別カウント
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for c in conflicts:
            severity_counts[c.severity] = severity_counts.get(c.severity, 0) + 1

        return ConflictReport(
            book_id=book_id,
            ep_num=ep_num,
            patch_review_id=patch_review_id,
            conflicts=conflicts,
            summary=summary,
            total_count=len(conflicts),
            critical_count=severity_counts.get("critical", 0),
            high_count=severity_counts.get("high", 0),
            medium_count=severity_counts.get("medium", 0),
            low_count=severity_counts.get("low", 0),
        )

    def _infer_field_path(
        self, audit_type: str, feedback: str, bible_snapshot: dict | None
    ) -> str | None:
        """監査タイプとフィードバックから該当設定パスを推定"""
        # キーワードベースの簡易推定
        keywords_map = {
            "logical_consistency": ["world_rules", "causality_map", "magic_system", "setting"],
            "ability_consistency": ["characters", "abilities", "skills", "magic"],
            "causal_integrity": ["plot", "foreshadowing", "timeline", "event"],
            "deai": ["style", "tone", "voice", "persona"],
            "fast_screen": ["plot", "structure", "pacing"],
        }

        keywords = keywords_map.get(audit_type, [])
        for kw in keywords:
            if kw in feedback.lower():
                return f"{audit_type}.{kw}"

        return None

    def _extract_values(
        self, audit_type: str, feedback: str, bible_snapshot: dict | None
    ) -> tuple[str | None, str | None]:
        """フィードバックから現在値と推奨値を抽出（簡易版）"""
        # 実際の実装ではLLMやより高度なパースを使用
        current = None
        suggested = None

        # フィードバックから "現在Xだが、Yであるべき" パターンを検出
        import re

        patterns = [
            r"現在[はが](.+?)だが[、,]?(.+?)であるべき",
            r"現在の(.+?)は(.+?)だが[、,]?(.+?)が正しい",
            r"設定値[はが](.+?)だが[、,]?(.+?)に修正",
        ]
        for pattern in patterns:
            match = re.search(pattern, feedback)
            if match:
                current = match.group(1).strip()
                suggested = match.group(2).strip()
                break

        return current, suggested

    def _generate_summary(self, conflicts: list[ConflictItem]) -> str:
        """矛盾レポートのサマリーを生成"""
        if not conflicts:
            return "矛盾は検出されませんでした。"

        by_category = {}
        for c in conflicts:
            by_category[c.category] = by_category.get(c.category, 0) + 1

        parts = [f"合計 {len(conflicts)} 件の矛盾を検出:"]
        for cat, count in by_category.items():
            label = self.CATEGORY_LABELS.get(cat, cat)
            parts.append(f"  - {label}: {count} 件")

        critical = [c for c in conflicts if c.severity == "critical"]
        if critical:
            parts.append(f"\n⚠️ 緊急対応が必要: {len(critical)} 件")

        return "\n".join(parts)

    def generate_unified_diff(self, original: str, proposed: str, context_lines: int = 3) -> str:
        """unified diff 形式で差分を生成"""
        orig_lines = original.splitlines(keepends=True)
        prop_lines = proposed.splitlines(keepends=True)

        diff = difflib.unified_diff(
            orig_lines,
            prop_lines,
            fromfile="current",
            tofile="proposed",
            n=context_lines,
        )
        return "".join(diff)

    def generate_json_patch(self, original: dict, proposed: dict) -> list[dict[str, Any]]:
        """JSON Patch (RFC 6902) 形式で差分を生成（簡易版）"""
        # 実際の実装では jsonpatch ライブラリを使用推奨
        patches = []
        all_keys = set(original.keys()) | set(proposed.keys())

        for key in all_keys:
            orig_val = original.get(key)
            prop_val = proposed.get(key)

            if key not in original:
                patches.append({"op": "add", "path": f"/{key}", "value": prop_val})
            elif key not in proposed:
                patches.append({"op": "remove", "path": f"/{key}"})
            elif orig_val != prop_val:
                patches.append({"op": "replace", "path": f"/{key}", "value": prop_val})

        return patches

    def to_dict(self, report: ConflictReport) -> dict[str, Any]:
        """ConflictReport を辞書に変換（API レスポンス用）"""
        return {
            "book_id": report.book_id,
            "ep_num": report.ep_num,
            "patch_review_id": report.patch_review_id,
            "summary": report.summary,
            "total_count": report.total_count,
            "critical_count": report.critical_count,
            "high_count": report.high_count,
            "medium_count": report.medium_count,
            "low_count": report.low_count,
            "conflicts": [
                {
                    "category": c.category,
                    "severity": c.severity,
                    "title": c.title,
                    "description": c.description,
                    "field_path": c.field_path,
                    "current_value": c.current_value,
                    "suggested_value": c.suggested_value,
                    "evidence_past": c.evidence_past,
                    "evidence_current": c.evidence_current,
                    "constraint_for_next": c.constraint_for_next,
                    "confidence": c.confidence,
                }
                for c in report.conflicts
            ],
        }
