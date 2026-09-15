class IllustrationPromptGenerator:
    """イラストレーションプロンプトジェネレーター"""
    
    def build_prompt(self, character_desc: str, mood: str, style: str) -> str:
        """シーンからプロンプトを生成する"""
        # 簡易実装：キャラクター説明、ムード、スタイルを組み合わせる
        prompt_parts = []
        if character_desc:
            prompt_parts.append(character_desc)
        if mood:
            prompt_parts.append(f"mood: {mood}")
        if style:
            prompt_parts.append(f"style: {style}")
        return ", ".join(prompt_parts)