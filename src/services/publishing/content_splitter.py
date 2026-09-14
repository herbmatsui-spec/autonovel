from __future__ import annotations
import re
from typing import Tuple, Dict, Any

class ContentSplitter:
    """小説本文から「前書き」「本文」「後書き」を自動抽出・構造化し、
    プラットフォーム別のルビ記法変換を行うエンジン。
    """

    @staticmethod
    def split_chapter_content(raw_text: str) -> Dict[str, str]:
        """テキストから前書き、本文、後書きを抽出する。
        マーカー:
          【前書き】 または 【まえがき】
          【後書き】 または 【あとがき】 または ――次回予告――
        """
        foreword = ""
        main_content = raw_text
        afterword = ""

        # 前書きの抽出
        foreword_match = re.search(r"【(?:前書き|まえがき)】\s*(.*?)(?=\n\s*\n|【(?:本文|本編|後書き|あとがき)】|――次回予告――|$)", raw_text, re.DOTALL)
        if foreword_match:
            foreword = foreword_match.group(1).strip()
            # 本文から前書き部分を除去
            main_content = raw_text.replace(foreword_match.group(0), "", 1)

        # 後書きの抽出
        afterword_match = re.search(r"(?:【(?:後書き|あとがき)】|――次回予告――)\s*(.*)$", main_content, re.DOTALL)
        if afterword_match:
            afterword = afterword_match.group(0).strip()
            main_content = main_content.replace(afterword_match.group(0), "", 1)

        return {
            "foreword": foreword.strip(),
            "main_content": main_content.strip(),
            "afterword": afterword.strip()
        }

    @staticmethod
    def convert_ruby(text: str, target_platform: str) -> str:
        """ルビ記法の相互変換
        - kakuyomu: |漢字《ルビ》
        - narou: 漢字(るび) または ｜漢字《ルビ》
        """
        if target_platform == "kakuyomu":
            # narou style (漢字(るび)) -> kakuyomu style (|漢字《ルビ》)
            # 例: 漢字(るび) -> |漢字《るび》
            # ただし既に|漢字《ルビ》形式ならそのまま
            # 簡易変換: ｜?([^（\(]+)[（\(]([^）\)]+)[）\)]
            def replace_to_kakuyomu(m: re.Match) -> str:
                kanji = m.group(1)
                ruby = m.group(2)
                return f"|{kanji}《{ruby}》"
            
            converted = re.sub(r"｜?([一-龥ぁ-んァ-ン]+)[（\(]([ぁ-んァ-ンー]+)[）\)]", replace_to_kakuyomu, text)
            return converted

        elif target_platform == "narou":
            # kakuyomu style (|漢字《ルビ》 または 漢字《ルビ》) -> narou style (漢字(るび))
            def replace_to_narou(m: re.Match) -> str:
                kanji = m.group(1)
                ruby = m.group(2)
                return f"{kanji}({ruby})"

            converted = re.sub(r"\|?([一-龥ぁ-んァ-ン]+)《([^》]+)》", replace_to_narou, text)
            return converted

        return text
