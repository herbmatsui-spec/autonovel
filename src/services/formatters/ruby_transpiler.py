"""Ruby and Bouten Transpiler for Novel Publishing Platforms (Steps 50, 51)."""

from __future__ import annotations

import re
from enum import Enum


class PublishPlatform(str, Enum):
    """Supported novel publishing platforms."""
    NAROU = "narou"             # 小説家になろう
    KAKUYOMU = "kakuyomu"       # カクヨム
    ALPHAPOLIS = "alphapolis"   # アルファポリス
    KDP_EPUB = "kdp_epub"       # Amazon KDP (縦書き電子書籍)
    AOZORA = "aozora"           # 青空文庫形式


class RubyTranspiler:
    """Converts internal ruby/bouten syntax into target platform formats."""

    # Internal format: ｜漢字《ルビ》 or |漢字《ルビ》
    RUBY_PATTERN = re.compile(r"[|｜]([^《\r\n]+)《([^》\r\n]+)》")
    # Bouten format: 《《強調テキスト》》
    BOUTEN_PATTERN = re.compile(r"《《([^》\r\n]+)》》")

    @classmethod
    def transpile_ruby(cls, text: str, target: PublishPlatform | str) -> str:
        """Transpile ruby annotations to match the target platform's syntax."""
        target_str = target.value if isinstance(target, PublishPlatform) else str(target).lower()

        if target_str == PublishPlatform.ALPHAPOLIS.value:
            # Alphapolis uses #漢字(ルビ)#
            return cls.RUBY_PATTERN.sub(r"#\1(\2)#", text)
        elif target_str == PublishPlatform.NAROU.value:
            # Narou accepts |漢字《ルビ》 (half-width pipe preferred)
            return cls.RUBY_PATTERN.sub(r"|\1《\2》", text)
        elif target_str == PublishPlatform.KAKUYOMU.value:
            # Kakuyomu accepts |漢字《ルビ》
            return cls.RUBY_PATTERN.sub(r"|\1《\2》", text)
        elif target_str == PublishPlatform.AOZORA.value:
            # Aozora accepts ｜漢字《ルビ》 (full-width pipe)
            return cls.RUBY_PATTERN.sub(r"｜\1《\2》", text)
        else:
            # Default / KDP: retain ｜漢字《ルビ》
            return cls.RUBY_PATTERN.sub(r"｜\1《\2》", text)

    @classmethod
    def transpile_bouten(cls, text: str, target: PublishPlatform | str) -> str:
        """Transpile emphasis/bouten marks to target platform syntax."""
        target_str = target.value if isinstance(target, PublishPlatform) else str(target).lower()

        def _narou_bouten(match: re.Match) -> str:
            content = match.group(1)
            return "".join(f"|{char}《・》" for char in content)

        def _alphapolis_bouten(match: re.Match) -> str:
            content = match.group(1)
            return "".join(f"#{char}(・)#" for char in content)

        def _aozora_bouten(match: re.Match) -> str:
            content = match.group(1)
            return f"［＃傍点］{content}［＃傍点終わり］"

        if target_str == PublishPlatform.KAKUYOMU.value:
            # Kakuyomu natively supports 《《...》》
            return text
        elif target_str == PublishPlatform.NAROU.value:
            return cls.BOUTEN_PATTERN.sub(_narou_bouten, text)
        elif target_str == PublishPlatform.ALPHAPOLIS.value:
            return cls.BOUTEN_PATTERN.sub(_alphapolis_bouten, text)
        elif target_str == PublishPlatform.AOZORA.value:
            return cls.BOUTEN_PATTERN.sub(_aozora_bouten, text)
        else:
            # KDP / Default
            return text

    @classmethod
    def transpile_all(cls, text: str, target: PublishPlatform | str) -> str:
        """Transpile both bouten and ruby for the target platform."""
        # Process bouten first, so 《《...》》 does not collide with ruby patterns
        text_with_bouten = cls.transpile_bouten(text, target)
        return cls.transpile_ruby(text_with_bouten, target)
