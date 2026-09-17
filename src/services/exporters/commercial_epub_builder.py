"""商用縦書きEPUB 3純Python組版ビルダー (v5.0 Step 17).

calibre等の外部CLIツールやC言語拡張不要。
標準ライブラリ（zipfile, io, uuid）のみで、Kindle Direct Publishing (KDP) および
楽天Koboの仕様（EPUB 3.0 / vertical-rl / 右開き）に完全準拠した電子書籍バイナリを出力する。
"""
from __future__ import annotations

import io
import uuid
import zipfile
from typing import Any, Dict, List, Optional

from src.services.exporters.epub_ruby_processor import EpubRubyProcessor
from src.services.exporters.epub_vertical_styler import COMMERCIAL_VERTICAL_CSS


class PureCommercialEpubBuilder:
    """純Python/標準ライブラリによる商用縦書きEPUB 3ビルダー。"""

    def build_epub(
        self,
        title: str,
        author: str,
        chapters: List[Dict[str, str]],
        cover_image_bytes: Optional[bytes] = None,
    ) -> bytes:
        """KDP / 楽天Kobo互換のEPUB 3ファイルを生成しバイトデータを返す。

        Args:
            title: 書籍タイトル
            author: 著者名
            chapters: 各章の辞書リスト [{"title": "第1話", "body": "..."}]
            cover_image_bytes: 表紙画像PNG/JPEGバイナリ（任意）

        Returns:
            EPUB 3規格準拠のzipアーカイブバイト列
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. mimetype (仕様により先頭・無圧縮ZIP_STORED)
            zf.writestr(
                "mimetype",
                "application/epub+zip",
                compress_type=zipfile.ZIP_STORED,
            )

            # 2. META-INF/container.xml
            container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
            zf.writestr("META-INF/container.xml", container_xml)

            # 3. OEBPS/styles/vertical.css
            zf.writestr("OEBPS/styles/vertical.css", COMMERCIAL_VERTICAL_CSS)

            manifest_items = [
                '<item id="css" href="styles/vertical.css" media-type="text/css"/>'
            ]
            spine_items = []

            # 4. 表紙 (cover)
            if cover_image_bytes:
                zf.writestr("OEBPS/images/cover.png", cover_image_bytes)
                manifest_items.append(
                    '<item id="cover-image" href="images/cover.png" media-type="image/png" properties="cover-image"/>'
                )
                cover_html = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">
<head>
    <meta charset="utf-8"/>
    <title>Cover</title>
    <style>body { margin: 0; padding: 0; text-align: center; } img { max-width: 100%; height: auto; }</style>
</head>
<body>
    <div id="cover-wrapper">
        <img src="images/cover.png" alt="Cover"/>
    </div>
</body>
</html>"""
                zf.writestr("OEBPS/cover.xhtml", cover_html)
                manifest_items.append(
                    '<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>'
                )
                spine_items.append('<itemref idref="cover"/>')

            # 5. 各章のXHTML生成
            for idx, ch in enumerate(chapters, start=1):
                ch_id = f"chapter_{idx}"
                ch_title = ch.get("title", f"第{idx}話")
                body_html = EpubRubyProcessor.to_xhtml_paragraphs(ch.get("body", ""))
                xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">
<head>
    <meta charset="utf-8"/>
    <title>{ch_title}</title>
    <link rel="stylesheet" type="text/css" href="styles/vertical.css"/>
</head>
<body class="vertical-text">
    <h2>{ch_title}</h2>
    {body_html}
</body>
</html>"""
                zf.writestr(f"OEBPS/{ch_id}.xhtml", xhtml)
                manifest_items.append(
                    f'<item id="{ch_id}" href="{ch_id}.xhtml" media-type="application/xhtml+xml"/>'
                )
                spine_items.append(f'<itemref idref="{ch_id}"/>')

            # 6. OEBPS/content.opf (縦書き・右開き指定: page-progression-direction="rtl")
            unique_id = str(uuid.uuid4())
            opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="pub-id">urn:uuid:{unique_id}</dc:identifier>
        <dc:title>{title}</dc:title>
        <dc:creator>{author}</dc:creator>
        <dc:language>ja</dc:language>
        <meta property="dcterms:modified">2026-09-17T00:00:00Z</meta>
    </metadata>
    <manifest>
        {"".join(manifest_items)}
    </manifest>
    <spine page-progression-direction="rtl">
        {"".join(spine_items)}
    </spine>
</package>"""
            zf.writestr("OEBPS/content.opf", opf)

        return buf.getvalue()
