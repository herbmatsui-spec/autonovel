class PromptBuilder:
    """
    ライトノベル画像生成用のプロンプトビルダー。
    標準的なネガティブプロンプトとプロンプト構築ロジックを提供する。
    """

    # ライトノベル標準ネガティブプロンプト
    STANDARD_LIGHT_NOVEL_NEGATIVE = (
        "bad anatomy, blurry, watermark, text, signature, low quality, extra limbs, bad hands, "
        "extra fingers, mutated hands, poorly drawn hands, poorly drawn face, "
        "deformed, ugly, disfigured, bad proportions, gross, disfigured, "
        "mutation, ugly, disgusting, poorly drawn, bad art, amateur, "
        "cropped, worst quality, jpeg artifacts, deformed iris, "
        "deformed pupils, deformed eyes, bad eyelids,"
    )

    # クオリティ向上ポジティブプロンプト
    QUALITY_ENHANCEMENT_POSITIVE = (
        "masterpiece, best quality, ultra detailed, 8k wallpaper, sharp focus, "
        "studio lighting, cinematic lighting, award winning, professional, "
        "beautiful and aesthetic, intricate details, elegant"
    )

    @classmethod
    def build_negative_prompt(
        cls, custom_negative: str | None = None, include_standard: bool = True
    ) -> str:
        """
        ネガティブプロンプトを構築する。

        Args:
            custom_negative: カスタムネガティブプロンプト
            include_standard: 標準ネガティブプロンプトを含むかどうか

        Returns:
            構築されたネガティブプロンプト文字列
        """
        parts = []
        if include_standard:
            parts.append(cls.STANDARD_LIGHT_NOVEL_NEGATIVE)
        if custom_negative:
            parts.append(custom_negative)
        return ", ".join(filter(None, parts))

    @classmethod
    def build_positive_prompt(
        cls,
        base_prompt: str,
        character_additions: str | None = None,
        quality_enhancement: bool = True,
        custom_positive: str | None = None,
    ) -> str:
        """
        ポジティブプロンプトを構築する。

        Args:
            base_prompt: 基本プロンプト
            character_additions: キャラクター固有の追加プロンプト
            quality_enhancement: クオリティ向上プロンプトを含むかどうか
            custom_positive: カスタムポジティブプロンプト

        Returns:
            構築されたポジティブプロンプト文字列
        """
        parts = [base_prompt]
        if character_additions:
            parts.append(character_additions)
        if quality_enhancement:
            parts.append(cls.QUALITY_ENHANCEMENT_POSITIVE)
        if custom_positive:
            parts.append(custom_positive)
        return ", ".join(filter(None, parts))