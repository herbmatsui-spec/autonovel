from __future__ import annotations
from src.models.publishing_assistant import TargetPlatform

class AIDisclosureGenerator:
    """文化庁ガイドラインおよび各プラットフォーム規約に適合した
    AI利用明記文を自動生成するジェネレーター。
    """

    @staticmethod
    def generate_disclosure(platform: TargetPlatform | str, ai_role: str = "assisted") -> str:
        platform_str = platform.value if isinstance(platform, TargetPlatform) else str(platform).lower()

        if platform_str == TargetPlatform.KAKUYOMU.value or platform_str == "kakuyomu":
            return "※本作はAIツール（AutoNovel）による構成・執筆支援を活用して制作しています。"
        elif platform_str == TargetPlatform.NAROU.value or platform_str == "narou":
            return "【AI生成・支援に関する表記】本作はAI支援ツールを用いてプロット構築および推敲を行っています。"
        elif platform_str == TargetPlatform.ALPHAPOLIS.value or platform_str == "alphapolis":
            return "※本作の制作にあたってはAIアシスタントツール（AutoNovel）の支援を受けています。"
        elif platform_str == TargetPlatform.KINDLE.value or platform_str == "kindle":
            return "This work was created with AI-assistance (AutoNovel) for plotting and structuring."
        
        return "Generated / Assisted with AI (AutoNovel)"
