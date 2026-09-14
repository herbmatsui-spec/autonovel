from __future__ import annotations
from typing import List
from src.models.publishing_assistant import TargetPlatform
from src.config.platform_compliance_rules import get_platform_rule

class ComplianceValidator:
    """投稿前の規約違反（文字数オーバー、タイトル制限、ガイドライン違反表現）を
    事前検査するバリデーター。
    """

    @staticmethod
    def validate_chapter(
        platform: TargetPlatform | str,
        chapter_title: str,
        main_content: str,
        foreword: str = "",
        afterword: str = ""
    ) -> List[str]:
        platform_str = platform.value if isinstance(platform, TargetPlatform) else str(platform).lower()
        rule = get_platform_rule(platform_str)
        warnings: List[str] = []

        # タイトル長チェック
        if len(chapter_title) > rule.max_title_chars:
            warnings.append(
                f"タイトル文字数（{len(chapter_title)}文字）がプラットフォーム上限（{rule.max_title_chars}文字）を超えています。"
            )

        # 総文字数チェック
        total_chars = len(foreword) + len(main_content) + len(afterword)
        if total_chars > rule.max_chapter_chars:
            warnings.append(
                f"話の総文字数（{total_chars}文字）が上限（{rule.max_chapter_chars}文字）を超えています。"
            )

        # AI開示・タグ推奨通知
        if rule.requires_ai_disclosure:
            warnings.append(
                "【確認】各投稿プラットフォームの設定画面にて、AI利用作品タグまたは開示設定が正しく行われているか確認してください。"
            )

        # 簡易的な成人向け表現・過激表現の検出（一般向けサイトでの注意喚起）
        sensitive_keywords = ["成人向け", "R18", "グロテスク", "過激な性描写"]
        combined_text = foreword + main_content + afterword
        for kw in sensitive_keywords:
            if kw in combined_text and platform_str in ["kakuyomu", "narou"]:
                warnings.append(
                    f"【警告】テキスト内に「{kw}」に関連する表現が検出されました。一般向けレーティングの規約に抵触しないかご確認ください。"
                )

        return warnings
