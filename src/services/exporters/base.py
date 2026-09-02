"""
services/exporters/base.py - 出版フォーマット自動整形エクスポーター基底

各プラットフォーム（なろう/カクヨム/Nocturne）の投稿用テキスト整形を提供する。
自動投稿ではなく、人間がコピペ・貼り付けする用の整形済みテキストを出力する。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Iterable, List, Optional


def normalize_newlines(text: str) -> str:
    """改行をLF統一に正規化し、連続する改行を最大2つに制限。"""
    if not text:
        return ""
    # CRLFとCRをLFに変換
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 連続する改行を最大2つに制限（段落間の空行は1つまで）
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def escape_ruby_markup(text: str) -> str:
    """ルビ記法 |文字《ルビ》| を保護（現在は変換しないが、将来の拡張のために保持）。"""
    # ルビ記法はそのまま保持（各プラットフォームで適切に変換する）
    return text


def process_image_placeholders(text: str, platform: str) -> str:
    """画像プレースホルダ ![alt](url) をプラットフォーム別形式に変換"""
    if not text:
        return text

    # 画像プレースホルダをマッチ: ![alt](url) または ![alt](url "title")
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)(?:\s+"[^"]*")?\)'

    def replace_image(match):
        alt_text = match.group(1)
        url = match.group(2)

        if platform == "narou":
            # なろうでは画像はサポートされていないため、代替テキストを表示
            return f"[画像: {alt_text}]" if alt_text else "[画像]"
        elif platform == "kakuyomu":
            # カクヨムではMarkdown形式のまま保持
            return match.group(0)  # 元のまま
        elif platform == "nocturn":
            # Nocturneでは画像はサポートされていないため、代替テキストを表示
            return f"[画像: {alt_text}]" if alt_text else "[画像]"
        elif platform == "markdown":
            # Markdownではそのまま保持
            return match.group(0)
        else:  # txt
            # プレーンテキストでは代替テキストのみ
            return f"[画像: {alt_text}]" if alt_text else "[画像]"

    return re.sub(image_pattern, replace_image, text)


def process_ruby_markup(text: str, platform: str) -> str:
    """ルビ記法 |文字《ルビ》| をプラットフォーム別形式に変換"""
    if not text:
        return text

    # ルビ記法をマッチ: |文字《ルビ》|
    ruby_pattern = r"\|([^|]+)《([^》]+)》\|"

    def replace_ruby(match):
        base_text = match.group(1)
        ruby_text = match.group(2)

        if platform == "narou":
            # なろうでは |漢字《かんじ》| 形式を使用
            return f"|{base_text}《{ruby_text}》|"
        elif platform == "kakuyomu":
            # カクヨムでは同じ形式を使用（サポートしているため）
            return f"|{base_text}《{ruby_text}》|"
        elif platform == "nocturn":
            # Nocturneでも同様の形式を使用可能
            return f"|{base_text}《{ruby_text}》|"
        elif platform == "markdown":
            # MarkdownではHTMLのルビタグに変換（サポートしているものとする）
            return f"<ruby>{base_text}<rt>{ruby_text}</rt></ruby>"
        else:  # txt
            # プレーンテキストでは基底テキストのみ
            return base_text

    return re.sub(ruby_pattern, replace_ruby, text)


def process_footnotes(text: str, platform: str) -> str:
    """脚注・傍注 ^[注釈] をプラットフォーム別形式に変換"""
    if not text:
        return text

    # 脚注をマッチ: ^[注釈]
    footnote_pattern = r"\$$\^([^$$]+)\$\$"

    def replace_footnote(match):
        footnote_text = match.group(1)

        if platform == "narou":
            # なろうでは脚注はサポートされていないため、括弧で囲んで表示
            return f"（{footnote_text}）"
        elif platform == "kakuyomu":
            # カクヨムでは脚注記法を使用: [^1] 形式（連番のため簡易実装）
            # 実際の実装では脚注に連番を付ける必要がある
            return f"[^{footnote_text}]"
        elif platform == "nocturn":
            # Nocturneでも同様に括弧で囲んで表示
            return f"（{footnote_text}）"
        elif platform == "markdown":
            # Markdownでは脚注記法を使用
            return f"[^{footnote_text}]"
        else:  # txt
            # プレーンテキストでは括弧で囲んで表示
            return f"（{footnote_text}）"

    return re.sub(footnote_pattern, replace_footnote, text)


def detect_unsupported_elements(text: str, platform: str) -> List[str]:
    """サポートされていない要素を検出して警告リストを返す"""
    warnings = []

    if not text:
        return warnings

    # 画像プレースホルダをチェック
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)(?:\s+"[^"]*")?\)'
    image_matches = re.findall(image_pattern, text)
    if image_matches and platform in ["narou", "nocturn", "txt"]:
        warnings.append(
            f"画像プレースホルダが検出されました ({len(image_matches)}個)。{platform} では代替テキストに変換されます。"
        )

    # 脚注をチェック
    footnote_pattern = r"\$$\^([^$$]+)\$\$"
    footnote_matches = re.findall(footnote_pattern, text)
    if footnote_matches and platform in ["narou", "nocturn", "txt"]:
        warnings.append(
            f"脚注が検出されました ({len(footnote_matches)}個)。{platform} では括弧表記に変換されます。"
        )

    # HTMLタグなど、明確にサポートされていないものをチェック（簡易的に）
    html_tag_pattern = r"<[^>]+>"
    html_matches = re.findall(html_tag_pattern, text)
    if html_matches and platform not in ["markdown"]:
        warnings.append(
            f"HTMLタグが検出されました ({len(html_matches)}個)。{platform} では削除または変換される可能性があります。"
        )

    return warnings


def sanitize_for_narou(text: str) -> str:
    """なろう向けにテキストをサニタイズ。"""
    text, _ = process_content_for_platform(text, "narou")
    return text


def sanitize_for_kakuyomu(text: str) -> str:
    """カクヨム向けにテキストをサニタイズ。"""
    text, _ = process_content_for_platform(text, "kakuyomu")
    return text


def sanitize_for_nocturne(text: str) -> str:
    """Nocturne向けにテキストをサニタイズ。"""
    text, _ = process_content_for_platform(text, "nocturn")
    return text


def sanitize_for_markdown(text: str) -> str:
    """Markdown向けにテキストをサニタイズ。"""
    text, _ = process_content_for_platform(text, "markdown")
    return text


def sanitize_for_plain_text(text: str) -> str:
    """プレーンテキスト向けにテキストをサニタイズ（UTF-8 BOMなし、LF改行）。"""
    text, _ = process_content_for_platform(text, "txt")
    # BOMがあれば削除（UTF-8 BOM: EF BB BF）
    if text.startswith("\ufeff"):
        text = text[1:]
    return text


def process_content_for_platform(text: str, platform: str) -> tuple[str, List[str]]:
    """プラットフォーム別コンテンツ処理を行い、処理済みテキストと警告を返す"""
    warnings = []

    # 画像プレースホルダを処理し、警告を収集
    original_text = text
    text = process_image_placeholders(text, platform)
    if text != original_text:
        # 画像が実際に変換された場合は警告を追加
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)(?:\s+"[^"]*")?\)'
        if re.search(image_pattern, original_text):
            if platform in ["narou", "nocturn", "txt"]:
                warnings.append(
                    f"画像プレースホルダが検出されました。{platform} では代替テキストに変換されます。"
                )

    # ルビ記法を処理
    text = process_ruby_markup(text, platform)

    # 脚注を処理し、警告を収集
    original_text = text
    text = process_footnotes(text, platform)
    if text != original_text:
        # 脚注が実際に変換された場合は警告を追加
        footnote_pattern = r"\$$\^([^$$]+)\$\$"
        if re.search(footnote_pattern, original_text):
            if platform in ["narou", "nocturn", "txt"]:
                warnings.append(f"脚注が検出されました。{platform} では括弧表記に変換されます。")

    # サポートされていない要素をチェック
    unsupported_warnings = detect_unsupported_elements(text, platform)
    warnings.extend(unsupported_warnings)

    # プラットフォーム共通のサニタイズ
    text = normalize_newlines(text)
    if platform == "txt" and text.startswith("\ufeff"):
        text = text[1:]

    return text, warnings


def escape_md(text: str) -> str:
    """Markdownエスケープ（基本的なもの）"""
    if not text:
        return ""
    # バックティック、アスタリスク、アンダースコア、波括弧、ブラケット、ハッシュ、プラス、マイナス、ドット、エクスクラメーションをエスケープ
    escapes = {
        "\\": "\\\\",
        "`": "\\`",
        "*": "\\*",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "[": "\\[",
        "]": "\\]",
        "(": "\\(",
        ")": "\\)",
        "#": "\\#",
        "+": "\\+",
        "-": "\\-",
        ".": "\\.",
        "!": "\\!",
    }
    # 簡易実装：順番に置換
    result = text
    for char, escape in escapes.items():
        result = result.replace(char, escape)
    return result


def ruby_filter(text: str) -> str:
    """ルビフィルタ - |文字《ルビ》| 形式を処理"""
    # 実際の実装では、プラットフォームに応じて変換
    # なろう: |漢字《かんじ》| → 漢字《かんじ》
    # カクヨム: |漢字《かんじ》| → 漢字《かんじ》
    # 現在はそのまま返すが、プラットフォーム固有の実装でオーバーライド可能
    # ここでプラットフォーム情報がないため、元のテキストを返す
    # 実際の処理は各 sanitize_for_* 関数で行われる
    return text


def pagebreak_filter(platform: str) -> str:
    """ページブレークフィルタ - プラットフォームに応じた区切りを返す"""
    if platform == "narou":
        return "\n=====\n"
    elif platform == "kakuyomu":
        return "---\n"
    elif platform == "nocturn":
        return "\n---\n"
    elif platform == "markdown":
        return "---\n"
    else:  # txt
        return "\n" + "-" * 20 + "\n"


def wordcount_filter(text: str) -> int:
    """ワードカウントフィルタ - テキストの文字数を返す（日本語では文字数）"""
    return len(text) if text else 0


class BaseExporter(ABC):
    """エクスポータの基底クラス。"""

    platform: str = "base"
    description: str = ""

    @abstractmethod
    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        """小説全体をプラットフォーム用テキストに整形して返す。"""

    @abstractmethod
    def export_stream(
        self, novel: Dict[str, Any], chapters: Iterable[Dict[str, Any]]
    ) -> Generator[str, None, None]:
        """小説を章ごとにストリーミングで整形してyieldする。"""

    def _header(self, novel: Dict[str, Any]) -> str:
        return f"# {novel.get('title', '無題')}\n\n{novel.get('synopsis', '')}\n"

    def _footer(self, novel: Dict[str, Any]) -> str:
        return ""

    def _format_chapter(self, ch: Dict[str, Any]) -> str:
        title = ch.get("title") or f"第{ch.get('ep_num')}話"
        body = ch.get("content") or ""
        return f"## {title}\n\n{body}\n"

    def apply_template_filters(
        self,
        text: str,
        platform: str,
        novel: Dict[str, Any],
        chapter: Optional[Dict[str, Any]] = None,
    ) -> str:
        """テンプレートフィルタを適用"""
        # 簡易的なフィルタ適用（実際の実装ではJinja2などを使用）
        # {{variable|filter}} 形式をサポート

        # 変数置換
        replacements = {
            "title": novel.get("title", ""),
            "synopsis": novel.get("synopsis", ""),
            "is_adult": str(novel.get("is_adult", False)).lower(),
        }

        if chapter:
            replacements.update(
                {
                    "chapter.title": chapter.get("title", ""),
                    "chapter.content": chapter.get("content", ""),
                    "chapter.number": str(chapter.get("ep_num", "")),
                }
            )

        # 簡易的な変数置換（実際の実装では正規表現などを使用）
        result = text
        for key, value in replacements.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))

        # フィルタ適用の簡易実装
        # {{variable|filter}} 形式
        import re

        filter_pattern = r"\{\{([^|}]+)\|([^}]+)\}\}"

        def replace_filter(match):
            var_name = match.group(1).strip()
            filter_name = match.group(2).strip()

            # 変数値を取得
            if var_name in replacements:
                value = replacements[var_name]
            elif "." in var_name and chapter:  # chapter.title など
                parts = var_name.split(".")
                if len(parts) == 2 and parts[0] == "chapter":
                    value = chapter.get(parts[1], "") if chapter else ""
                else:
                    value = ""
            else:
                value = ""

            # フィルタを適用
            if filter_name == "escape_md":
                return escape_md(str(value))
            elif filter_name == "ruby":
                return ruby_filter(str(value))
            elif filter_name == "wordcount":
                return str(wordcount_filter(str(value)))
            elif filter_name == "pagebreak":
                return pagebreak_filter(platform)
            else:
                # 不明なフィルタはそのまま返す
                return str(value)

        result = re.sub(filter_pattern, replace_filter, result)

        return result


class NarouExporter(BaseExporter):
    platform = "narou"
    description = "小説家になろう（改行・ルビ・話区切りを標準整形）"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        # ストリーミング版を呼び出して結果を結合
        return "".join(self.export_stream(novel, chapters))

    def export_stream(
        self, novel: Dict[str, Any], chapters: Iterable[Dict[str, Any]]
    ) -> Generator[str, None, None]:
        # ヘッダー
        header = self._header(novel)
        yield self.apply_template_filters(header, self.platform, novel)

        for i, ch in enumerate(chapters):
            # 本文をなろう向けに整形
            body_raw = ch.get("content") or ""
            body, warnings = process_content_for_platform(body_raw, self.platform)
            # 警告がある場合はログに出力するか、特別な方法で処理
            # ここでは簡易的に最初のチャンクに警告を付加する（実際の実装では別の方法を検討）
            if i == 0 and warnings:
                warning_text = "\\n".join([f"<!-- WARNING: {w} -->" for w in warnings])
                yield warning_text + "\\n"

            # ルビ記法 |文字《ルビ》| を保持（なろうではこの形式を使用）
            title = ch.get("title") or f"第{ch.get('ep_num')}話"

            # チャプターフォーマット
            chapter_text = f"## {title}\n\n{body}\n"
            yield self.apply_template_filters(chapter_text, self.platform, novel, ch)

            # 話区切り（最後の章以外に「=====」を挿入）
            if i < len(chapters) - 1:
                yield "\n=====\n"

        # フッターがある場合は最後に出す
        footer = self._footer(novel)
        if footer:
            yield self.apply_template_filters(footer, self.platform, novel)


class KakuyomuExporter(BaseExporter):
    platform = "kakuyomu"
    description = "カクヨム（Markdown系・R18タグ付与）"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        return "".join(self.export_stream(novel, chapters))

    def export_stream(
        self, novel: Dict[str, Any], chapters: Iterable[Dict[str, Any]]
    ) -> Generator[str, None, None]:
        yield f"# {novel.get('title', '無題')}\n\n"
        yield novel.get("synopsis", "") + "\n\n"
        for i, ch in enumerate(chapters):
            # 本文をカクヨム向けに整形（Markdown見出しレベル統一）
            body_raw = ch.get("content") or ""
            body, warnings = process_content_for_platform(body_raw, self.platform)
            # 警告がある場合はログに出力するか、特別な方法で処理
            if i == 0 and warnings:
                warning_text = "\\n".join([f"<!-- WARNING: {w} -->" for w in warnings])
                yield warning_text + "\\n"

            # カクヨムでは見出しレベルを調整（小説の場合は見出しレベル3から開始）
            title = ch.get("title") or f"第{ch.get('ep_num')}話"
            if i > 0:
                yield "---\n"  # 章間に水平線
            yield f"### {title}\n\n{body}\n"
        # R18タグの位置（本文の最後に配置）
        if novel.get("is_adult"):
            yield "\n[R18]\n"


class NocturneExporter(BaseExporter):
    platform = "nocturn"
    description = "Nocturn Novel（官能タグ・年齢確認文言）"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        return "".join(self.export_stream(novel, chapters))

    def export_stream(
        self, novel: Dict[str, Any], chapters: Iterable[Dict[str, Any]]
    ) -> Generator[str, None, None]:
        yield f"# {novel.get('title', '無題')}\n\n"
        yield "[R18] 成年向けコンテンツを含みます。\n\n"
        for i, ch in enumerate(chapters):
            # 本文をNocturne向けに整形（官能タグ等対応）
            body_raw = ch.get("content") or ""
            body, warnings = process_content_for_platform(body_raw, self.platform)
            # 警告がある場合はログに出力するか、特別な方法で処理
            if i == 0 and warnings:
                warning_text = "\\n".join([f"<!-- WARNING: {w} -->" for w in warnings])
                yield warning_text + "\\n"

            # Nocturneでは独自のタグ形式を使用可能
            title = ch.get("title") or f"第{ch.get('ep_num')}話"
            if i > 0:
                yield "\n---\n"  # 章間区切り
            yield f"## {title}\n\n{body}\n"
        # 年齢確認文言（必須）
        yield "\n[年齢確認: 18歳以上であることを確認しました]\n"
        # 官能タグの例（実際のコンテンツに応じて追加）
        if novel.get("is_adult"):
            yield "[官能]\n"


class PlainTextExporter(BaseExporter):
    platform = "txt"
    description = "プレーンテキスト（シンプルな原稿テキスト）"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        return "".join(self.export_stream(novel, chapters))

    def export_stream(
        self, novel: Dict[str, Any], chapters: Iterable[Dict[str, Any]]
    ) -> Generator[str, None, None]:
        yield (
            f"『{novel.get('title', '無題')}』\n\nあらすじ：\n{novel.get('synopsis', '')}\n\n"
            + "=" * 30
            + "\n"
        )
        for i, ch in enumerate(chapters):
            # 本文をプレーンテキスト向けに整形（UTF-8 BOMなし、LF改行統一）
            body_raw = ch.get("content") or ""
            body, warnings = process_content_for_platform(body_raw, self.platform)
            # 警告がある場合はログに出力するか、特別な方法で処理
            if i == 0 and warnings:
                warning_text = "\\n".join([f"<!-- WARNING: {w} -->" for w in warnings])
                yield warning_text + "\\n"

            title = ch.get("title") or f"第{ch.get('ep_num')}話"
            if i > 0:
                yield "\n" + "-" * 20 + "\n"  # 章間区切り
            yield f"◆ {title} ◆\n\n{body}\n\n"


class MarkdownExporter(BaseExporter):
    platform = "markdown"
    description = "標準 Markdown（汎用エディタ・Obsidian等向け）"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        return "".join(self.export_stream(novel, chapters))

    def export_stream(
        self, novel: Dict[str, Any], chapters: Iterable[Dict[str, Any]]
    ) -> Generator[str, None, None]:
        # フロントマター (YAML) オプション対応
        front_matter = []
        if novel.get("title"):
            front_matter.append(f'title: "{novel["title"]}"')
        if novel.get("synopsis"):
            # エスケープ処理（簡易的）
            synopsis = novel["synopsis"].replace('"', '\\"').replace("\n", " ")
            front_matter.append(f'description: "{synopsis}"')
        # 作成日などがあれば追加（ここでは省略）
        # タグ情報があれば追加
        if novel.get("tags"):
            tags = ", ".join(novel["tags"]) if isinstance(novel["tags"], list) else novel["tags"]
            front_matter.append(f"tags: [{tags}]")

        if front_matter:
            yield "---\n"
            yield "\n".join(front_matter) + "\n"
            yield "---\n\n"

        yield f"# {novel.get('title', '無題')}\n"
        if novel.get("synopsis"):
            yield f"> {novel.get('synopsis')}\n\n"

        for i, ch in enumerate(chapters):
            # 本文をマークダウン向けに整形
            body_raw = ch.get("content") or ""
            body, warnings = process_content_for_platform(body_raw, self.platform)
            # 警告がある場合はログに出力するか、特別な方法で処理
            if i == 0 and warnings:
                warning_text = "\\n".join([f"<!-- WARNING: {w} -->" for w in warnings])
                yield warning_text + "\\n"

            title = ch.get("title") or f"第{ch.get('ep_num')}話"
            if i > 0:
                yield "---\n"  # 章間区切り
            yield f"## {title}\n\n{body}\n"


# ==========================================
# EPUB/PDF Exporters (Step 7)
# ==========================================


class EpubExporter(BaseExporter):
    platform = "epub"
    description = "EPUB電子書籍形式"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        # ストリーミング版を呼び出して結果を結合
        return "".join(self.export_stream(novel, chapters))

    def export_stream(
        self, novel: Dict[str, Any], chapters: Iterable[Dict[str, Any]]
    ) -> Generator[str, None, None]:
        # フロントマター (YAML) オプション対応
        front_matter = []
        if novel.get("title"):
            front_matter.append(f'title: "{novel["title"]}"')
        if novel.get("synopsis"):
            # エスケープ処理（簡易的）
            synopsis = novel["synopsis"].replace('"', '\\"').replace("\n", " ")
            front_matter.append(f'description: "{synopsis}"')
        # 作成日などがあれば追加（ここでは省略）
        # タグ情報があれば追加
        if novel.get("tags"):
            tags = ", ".join(novel["tags"]) if isinstance(novel["tags"], list) else novel["tags"]
            front_matter.append(f"tags: [{tags}]")

        if front_matter:
            yield "---\n"
            yield "\n".join(front_matter) + "\n"
            yield "---\n\n"

        yield f"# {novel.get('title', '無題')}\n"
        if novel.get("synopsis"):
            yield f"> {novel.get('synopsis')}\n\n"

        for i, ch in enumerate(chapters):
            # 本文をEPUB向けに整形
            body_raw = ch.get("content") or ""
            body, warnings = process_content_for_platform(body_raw, self.platform)
            # 警告がある場合はログに出力するか、特別な方法で処理
            if i == 0 and warnings:
                warning_text = "\\n".join([f"<!-- WARNING: {w} -->" for w in warnings])
                yield warning_text + "\\n"

            title = ch.get("title") or f"第{ch.get('ep_num')}話"
            if i > 0:
                yield "---\n"  # 章間区切り
            yield f"## {title}\n\n{body}\n"


class PdfExporter(BaseExporter):
    platform = "pdf"
    description = "PDFドキュメント形式"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        # ストリーミング版を呼び出して結果を結合
        return "".join(self.export_stream(novel, chapters))

    def export_stream(
        self, novel: Dict[str, Any], chapters: Iterable[Dict[str, Any]]
    ) -> Generator[str, None, None]:
        # フロントマター (YAML) オプション対応
        front_matter = []
        if novel.get("title"):
            front_matter.append(f'title: "{novel["title"]}"')
        if novel.get("synopsis"):
            # エスケープ処理（簡易的）
            synopsis = novel["synopsis"].replace('"', '\\"').replace("\n", " ")
            front_matter.append(f'description: "{synopsis}"')
        # 作成日などがあれば追加（ここでは省略）
        # タグ情報があれば追加
        if novel.get("tags"):
            tags = ", ".join(novel["tags"]) if isinstance(novel["tags"], list) else novel["tags"]
            front_matter.append(f"tags: [{tags}]")

        if front_matter:
            yield "---\n"
            yield "\n".join(front_matter) + "\n"
            yield "---\n\n"

        yield f"# {novel.get('title', '無題')}\n"
        if novel.get("synopsis"):
            yield f"> {novel.get('synopsis')}\n\n"

        for i, ch in enumerate(chapters):
            # 本文をPDF向けに整形
            body_raw = ch.get("content") or ""
            body, warnings = process_content_for_platform(body_raw, self.platform)
            # 警告がある場合はログに出力するか、特別な方法で処理
            if i == 0 and warnings:
                warning_text = "\\n".join([f"<!-- WARNING: {w} -->" for w in warnings])
                yield warning_text + "\\n"

            title = ch.get("title") or f"第{ch.get('ep_num')}話"
            if i > 0:
                yield "---\n"  # 章間区切り
            yield f"## {title}\n\n{body}\n"


# ==========================================
# Exporter Registry
# ==========================================


_EXPORTERS = {
    NarouExporter.platform: NarouExporter,
    KakuyomuExporter.platform: KakuyomuExporter,
    NocturneExporter.platform: NocturneExporter,
    PlainTextExporter.platform: PlainTextExporter,
    MarkdownExporter.platform: MarkdownExporter,
    EpubExporter.platform: EpubExporter,
    PdfExporter.platform: PdfExporter,
}


def get_exporter(platform: str) -> BaseExporter:
    """プラットフォーム名からエクスポータを取得する。未知の場合はなろうを既定とする。"""
    cls = _EXPORTERS.get(platform, NarouExporter)
    return cls()


def list_platforms() -> List[Dict[str, str]]:
    """対応プラットフォーム一覧を返す。"""
    return [{"platform": e.platform, "description": e.description} for e in _EXPORTERS.values()]


def sanitize_for_platform(text: str) -> str:
    """プラットフォーム共通の軽いサニタイズ（制御文字除去）。"""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text or "")
