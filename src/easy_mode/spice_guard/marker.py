"""
SpiceGuard マーカー操作・プロンプト構築
"""

from __future__ import annotations

import re
from typing import List

from src.easy_mode.models import SpiceElement


class SpiceMarkerInjector:
    """尖り要素を保護マーカーで囲む"""

    def inject(self, text: str, elements: List[SpiceElement]) -> str:
        """尖り要素を保護マーカーで囲む"""
        # 後ろから置換（位置がずれないように）
        sorted_elements = sorted(elements, key=lambda x: x.position, reverse=True)

        result = text
        for elem in sorted_elements:
            pos = elem.position
            length = len(elem.text)
            if pos >= 0 and length > 0 and pos + length <= len(result):
                # 元のテキストと一致するか確認
                if result[pos : pos + length] == elem.text:
                    marker_id = f"{elem.type}_{pos}"
                    before = result[:pos]
                    target = result[pos : pos + length]
                    after = result[pos + length :]
                    result = before + f"<<<SPICE:{marker_id}>>> {target} <<</SPICE>>>" + after

        return result

    def remove(self, text: str) -> str:
        """SPICEマーカーを除去"""
        return re.sub(r"<<<SPICE:[^>]+>>>|<<</SPICE>>>", "", text)

    def clean_output(self, text: str) -> str:
        """出力からSPICEマーカーを除去"""
        return self.remove(text)


class RewritePromptBuilder:
    """SpiceGuard付きリライトプロンプト構築"""

    def __init__(self, marker_injector: Optional[SpiceMarkerInjector] = None):
        self.marker_injector = marker_injector or SpiceMarkerInjector()

    def build(
        self, content: str, improvements: List[str], elements: List[SpiceElement]
    ) -> str:
        """SpiceGuard付きリライトプロンプト構築"""
        protected_content = self.marker_injector.inject(content, elements)

        improvements_text = "\n".join(f"- {imp}" for imp in improvements)

        prompt = f"""以下の小説を改善せよ。ただし、<<<SPICE:...>>> で囲まれた部分は
『絶対に変更するな。一文字も触るな。そこがこの話の『命』だ。』

【改善指示】
{improvements_text}

【原文】
{protected_content}

改善後の本文のみを出力せよ。SPICEマーカーはそのまま残せ。"""

        return prompt
