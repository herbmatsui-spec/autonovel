from typing import Tuple, List, Dict


class CharacterLoraMapper:
    """
    キャラクターの外見設定からLoRAタグを自動マッピングするマッパー。
    世界観Bibleのキャラクターデータ（髪型、目の色、服装、固有属性）から、
    画像生成プロンプト用LoRAタグを合成する。
    """

    def __init__(self) -> None:
        self.lora_database = self._load_lora_database()

    def _load_lora_database(self) -> Dict[str, Dict[str, str]]:
        """
        LoRAタグのマッピングデータベースを読み込む（設定ファイルから読み込む可能性あり）。
        """
        return {
            "hair_style": {
                "long_dark_hair": "lora:long_dark_hair_style",
                "short_white_hair": "lora:short_white_hair_style",
                "curly_red_hair": "lora:curly_red_hair_style",
                "bald": "lora:bald_look",
            },
            "eye_color": {
                "blue_eyes": "lora:blue_eyes_detail",
                "green_eyes": "lora:green_eyes_detail",
                "brown_eyes": "lora:brown_eyes_detail",
                "purple_eyes": "lora:purple_eyes_detail",
            },
            "clothing": {
                "ninja_uniform": "lora:ninja_uniform",
                "western_outfit": "lora:western_outfit",
                "traditional_dress": "lora:traditional_dress",
                "modern_armor": "lora:modern_armor",
            },
            "special_attributes": {
                "magical_aura": "lora:magical_aura_effect",
                "royal_crown": "lora:royal_crown",
                "animal_ears": "lora:animal_ears",
                "winged": "lora:winged_back",
            },
        }

    def get_prompt_tags_for_character(self, char_data: Dict[str, str]) -> Tuple[str, List[str]]:
        """
        キャラクターの属性からLoRAタグを合成してプロンプトタグを取得する。

        Args:
            char_data: キャラクターの設定データ（hair_style, eye_color, clothing, special_attributesなど）

        Returns:
            tuple: (プロンプトに追加する文字列, LoRA名リスト)
        """
        prompt_additions = []
        lora_tags = []

        # 髪型
        hair_style = char_data.get("hair_style")
        if hair_style and hair_style in self.lora_database["hair_style"]:
            prompt_additions.append(f"{hair_style.replace('_', ' ')}")
            lora_tags.append(self.lora_database["hair_style"][hair_style])

        # 目の色
        eye_color = char_data.get("eye_color")
        if eye_color and eye_color in self.lora_database["eye_color"]:
            prompt_additions.append(f"{eye_color.replace('_', ' ')}")
            lora_tags.append(self.lora_database["eye_color"][eye_color])

        # 服装
        clothing = char_data.get("clothing")
        if clothing and clothing in self.lora_database["clothing"]:
            prompt_additions.append(f"{clothing.replace('_', ' ')}")
            lora_tags.append(self.lora_database["clothing"][clothing])

        # 特殊属性
        special_attr = char_data.get("special_attributes")
        if special_attr and special_attr in self.lora_database["special_attributes"]:
            prompt_additions.append(f"{special_attr.replace('_', ' ')}")
            lora_tags.append(self.lora_database["special_attributes"][special_attr])

        # プロンプト文字列を作成
        prompt_suffix = ", ".join(prompt_additions)
        return prompt_suffix, lora_tags