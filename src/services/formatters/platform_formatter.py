"""Platform-specific Novel Formatter and Packager (Steps 49, 52, 53, 54, 55)."""

from __future__ import annotations

import io
import re
import zipfile
from typing import Any

from src.services.formatters.ruby_transpiler import PublishPlatform, RubyTranspiler

# Regex helpers for typography normalization
CONSECUTIVE_BLANKS = re.compile(r"\n{3,}")
DIALOGUE_STARTERS = ("「", "『", "（", "(", "【", "［", "[", "〈", "《", "“", "\"")


class PlatformFormatter:
    """Formats novel text according to publishing platform standards and conventions."""

    @classmethod
    def normalize_typography(cls, text: str, platform: PublishPlatform | str = PublishPlatform.NAROU) -> str:
        """Normalize indentation, empty lines, and punctuation for web novels."""
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        normalized_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                normalized_lines.append("")
                continue

            # Remove leading spaces first to normalize
            content = line.lstrip(" 　")

            # Dialogue lines should not have leading indent
            if content.startswith(DIALOGUE_STARTERS):
                normalized_lines.append(content)
            else:
                # Narrative lines should have exactly one full-width space indent
                normalized_lines.append(f"　{content}")

        result = "\n".join(normalized_lines)

        # Normalize consecutive blank lines to at most 2 blank lines (3 newlines)
        result = CONSECUTIVE_BLANKS.sub("\n\n", result)

        # Normalize odd numbers of ellipsis (… or ...) and em-dashes (― or --) to even pairs
        def _even_ellipses(match: re.Match) -> str:
            count = len(match.group(0))
            if count % 2 != 0:
                count += 1
            return "…" * count

        result = re.sub(r"…+", _even_ellipses, result)

        # Also transpile ruby and bouten
        result = RubyTranspiler.transpile_all(result, platform)
        return result

    @classmethod
    def validate_limits(
        cls,
        title: str,
        synopsis: str,
        platform: PublishPlatform | str,
    ) -> list[str]:
        """Validate title and synopsis lengths according to platform guidelines."""
        target = PublishPlatform(platform) if isinstance(platform, str) else platform
        warnings: list[str] = []

        title_len = len(title)
        synopsis_len = len(synopsis)

        if target == PublishPlatform.NAROU:
            if title_len > 100:
                warnings.append(f"小説家になろうのタイトル上限は100文字です（現在: {title_len}文字）")
            if synopsis_len > 1000:
                warnings.append(f"小説家になろうのあらすじは1000文字以内が推奨されます（現在: {synopsis_len}文字）")
        elif target == PublishPlatform.KAKUYOMU:
            if title_len > 100:
                warnings.append(f"カクヨムのタイトル上限は100文字です（現在: {title_len}文字）")
            if synopsis_len > 10000:
                warnings.append(f"カクヨムのあらすじ上限は10,000文字です（現在: {synopsis_len}文字）")
        elif target == PublishPlatform.ALPHAPOLIS:
            if title_len > 100:
                warnings.append(f"アルファポリスのタイトル上限は100文字です（現在: {title_len}文字）")

        return warnings

    @classmethod
    def format_episode_with_author_notes(
        cls,
        title: str,
        content: str,
        platform: PublishPlatform | str,
        foreword: str = "",
        afterword: str = "",
    ) -> dict[str, str]:
        """Format an episode with optional author foreword and afterword."""
        formatted_content = cls.normalize_typography(content, platform)
        formatted_foreword = cls.normalize_typography(foreword, platform) if foreword else ""
        formatted_afterword = cls.normalize_typography(afterword, platform) if afterword else ""

        full_text_parts = []
        if formatted_foreword:
            full_text_parts.append(f"【前書き】\n{formatted_foreword}\n\n" + "―" * 20 + "\n")
        full_text_parts.append(formatted_content)
        if formatted_afterword:
            full_text_parts.append("\n\n" + "―" * 20 + f"\n【後書き】\n{formatted_afterword}")

        return {
            "title": title,
            "foreword": formatted_foreword,
            "content": formatted_content,
            "afterword": formatted_afterword,
            "full_text": "\n".join(full_text_parts),
        }

    @classmethod
    def package_for_platform(
        cls,
        title: str,
        synopsis: str,
        episodes: list[dict[str, Any]],
        platform: PublishPlatform | str,
    ) -> bytes:
        """Create a platform-formatted zip bundle containing all episodes as text files."""
        zip_buf = io.BytesIO()

        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Synopsis / Overview file
            overview_lines = [
                f"作品名: {title}",
                f"投稿先プラットフォーム: {platform.value if isinstance(platform, PublishPlatform) else platform}",
                "",
                "【あらすじ】",
                synopsis or "（あらすじ未設定）",
                "",
                "【話数一覧】",
            ]
            for idx, ep in enumerate(episodes, start=1):
                ep_title = ep.get("title", f"第{idx}話")
                overview_lines.append(f"第{idx}話: {ep_title}")

            zf.writestr("00_作品情報・あらすじ.txt", "\n".join(overview_lines).encode("utf-8"))

            # Episodes
            for idx, ep in enumerate(episodes, start=1):
                ep_title = ep.get("title", f"第{idx}話")
                ep_content = ep.get("content", "")
                ep_foreword = ep.get("foreword", "")
                ep_afterword = ep.get("afterword", "")

                formatted = cls.format_episode_with_author_notes(
                    title=ep_title,
                    content=ep_content,
                    platform=platform,
                    foreword=ep_foreword,
                    afterword=ep_afterword,
                )

                file_name = f"{idx:03d}_{ep_title}.txt"
                # Sanitize filename
                file_name = re.sub(r'[\\/*?:"<>|]', "_", file_name)
                zf.writestr(f"本文/{file_name}", formatted["full_text"].encode("utf-8"))

        return zip_buf.getvalue()


__all__ = ["PublishPlatform", "RubyTranspiler", "PlatformFormatter"]
