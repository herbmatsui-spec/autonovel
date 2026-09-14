from src.services.exporters.text_sanitizer import escape_xhtml_text
from dataclasses import dataclass
from typing import Literal

def detect_image_media_type(filename: str = "", data: bytes | None = None) -> str:
    """拡張子およびマジックバイトから画像メディアタイプを自動判定 (Step 44)。"""
    if data:
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return "image/gif"
        if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"
        if b"<svg" in data[:100].lower():
            return "image/svg+xml"

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "webp":
        return "image/webp"
    if ext == "gif":
        return "image/gif"
    if ext == "svg":
        return "image/svg+xml"
    return "image/jpeg"


@dataclass
class EpubIllustrationItem:
    image_id: str
    image_bytes: bytes
    file_name: str
    media_type: str = "image/jpeg"
    position: Literal["frontmatter", "chapter_start", "chapter_end"] = "chapter_start"
    chapter_index: int | None = None
    caption: str = ""

    def __post_init__(self):
        if not self.media_type or self.media_type == "image/jpeg":
            self.media_type = detect_image_media_type(self.file_name, self.image_bytes)


class EpubManifestBuilder:
    """EPUB 3 ナビゲーション文書 (nav.xhtml), NCX目次 (toc.ncx), OPF (standard.opf) 生成器 (Steps 43, 44, 45, 52)。"""

    @staticmethod
    def build_nav_xhtml(
        title: str,
        chapters: list[dict[str, str]],
        css_rel_path: str = "style/vertical.css",
        exclude_hrefs: set[str] | None = None,
    ) -> str:
        """EPUB 3 ナビゲーション文書 (nav.xhtml) の自動生成 (Step 43)。"""
        nav_items = []
        for i, chap in enumerate(chapters):
            href = chap.get("href", f"xhtml/p-{i+1:03d}.xhtml")
            if exclude_hrefs and href in exclude_hrefs:
                continue
            chap_title = escape_xhtml_text(chap.get("title", f"第{i+1}話"))
            nav_items.append(f'<li><a href="{href}">{chap_title}</a></li>')

        items_html = "\n".join(nav_items)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">
<head>
<meta charset="UTF-8" />
<title>目次</title>
<link rel="stylesheet" type="text/css" href="{css_rel_path}" />
</head>
<body>
<nav epub:type="toc" id="toc">
<h1>目次</h1>
<ol>
{items_html}
</ol>
</nav>
</body>
</html>"""

    @staticmethod
    def build_toc_ncx(
        book_uuid: str,
        title: str,
        chapters: list[dict[str, str]],
        exclude_hrefs: set[str] | None = None,
    ) -> str:
        """旧規格・Kindle互換用 NCX 目次 (toc.ncx) の二重生成 (Step 44)。"""
        nav_points = []
        order = 0
        for i, chap in enumerate(chapters):
            href = chap.get("href", f"xhtml/p-{i+1:03d}.xhtml")
            if exclude_hrefs and href in exclude_hrefs:
                continue
            chap_title = escape_xhtml_text(chap.get("title", f"第{i+1}話"))
            order += 1
            nav_points.append(f"""  <navPoint id="navPoint-{order}" playOrder="{order}">
    <navLabel><text>{chap_title}</text></navLabel>
    <content src="{href}"/>
  </navPoint>""")

        points_xml = "\n".join(nav_points)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head>
  <meta name="dtb:uid" content="urn:uuid:{book_uuid}"/>
  <meta name="dtb:depth" content="1"/>
  <meta name="dtb:totalPageCount" content="0"/>
  <meta name="dtb:maxPageNumber" content="0"/>
</head>
<docTitle><text>{escape_xhtml_text(title)}</text></docTitle>
<navMap>
{points_xml}
</navMap>
</ncx>"""

    @staticmethod
    def build_cover_xhtml(
        image_href: str = "images/cover.jpg",
        css_rel_path: str = "style/vertical.css",
    ) -> str:
        """表紙ページ (cover.xhtml) の自動生成 (Step 45)。"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">
<head>
<meta charset="UTF-8" />
<title>表紙</title>
<link rel="stylesheet" type="text/css" href="{css_rel_path}" />
</head>
<body class="p-cover" style="margin:0;padding:0;text-align:center;">
<div class="main" style="height:100%;text-align:center;">
  <img src="{image_href}" alt="表紙" style="max-height:100%;max-width:100%;object-fit:contain;" />
</div>
</body>
</html>"""

    @staticmethod
    def build_standard_opf(
        book_uuid: str,
        title: str,
        author: str = "AI Novelist",
        publisher: str = "AutoNovel",
        manifest_items: list[dict[str, str]] | None = None,
        spine_items: list[str] | None = None,
        has_cover: bool = False,
        illustrations: list[EpubIllustrationItem] | None = None,
    ) -> str:
        """OPF マニフェスト・スパインの生成（Kindle縦書き・右開き page-progression-direction="rtl" 準拠）(Step 52)。"""
        items = manifest_items or []
        item_tags = []
        for it in items:
            props = f' properties="{it["properties"]}"' if "properties" in it else ""
            item_tags.append(f'<item id="{it["id"]}" href="{it["href"]}" media-type="{it["media-type"]}"{props} />')

        # Process illustrations: add image binary and XHTML page to manifest and prepare spine insertion
        illustration_manifest_items = []
        illustration_spine_entries = []  # list of (position_type, chapter_index, xhtml_page_id)
        if illustrations:
            for ill in illustrations:
                img_id = f"img-{ill.image_id}"
                page_id = f"p-ill-{ill.image_id}"
                illustration_manifest_items.append({
                    "id": img_id,
                    "href": f"images/{ill.file_name}",
                    "media-type": ill.media_type,
                })
                # Determine spine insertion point using XHTML page_id
                if ill.position == "frontmatter":
                    illustration_spine_entries.append(("frontmatter", 0, page_id))
                elif ill.position == "chapter_start":
                    illustration_spine_entries.append(("chapter_start", ill.chapter_index, page_id))
                elif ill.position == "chapter_end":
                    illustration_spine_entries.append(("chapter_end", ill.chapter_index, page_id))

        # Build manifest items including illustrations (avoid duplicates with manifest_items)
        existing_ids = {it["id"] for it in items}
        all_items = list(items)
        for it in illustration_manifest_items:
            if it["id"] not in existing_ids:
                all_items.append(it)
                existing_ids.add(it["id"])

        item_tags = []
        for it in all_items:
            props = f' properties="{it["properties"]}"' if "properties" in it else ""
            item_tags.append(f'<item id="{it["id"]}" href="{it["href"]}" media-type="{it["media-type"]}"{props} />')

        manifest_xml = "\n    ".join(item_tags)

        # Build spine with illustration insertion
        spines = spine_items or []
        new_spine = []
        frontmatter_ills = [page_id for pos, idx, page_id in illustration_spine_entries if pos == "frontmatter"]
        chapter_start_ills = {}  # chapter_index -> list of page_ids
        chapter_end_ills = {}
        for pos, idx, page_id in illustration_spine_entries:
            if pos == "chapter_start":
                chapter_start_ills.setdefault(idx, []).append(page_id)
            elif pos == "chapter_end":
                chapter_end_ills.setdefault(idx, []).append(page_id)

        # Iterate through original spine items and insert illustrations
        for ref in spines:
            # Check if this ref is a chapter (pattern p-XXX)
            if ref.startswith("p-") and ref[2:].isdigit():
                chap_idx = int(ref[2:])
                # Insert chapter_start illustrations before this chapter
                if chap_idx in chapter_start_ills:
                    for p_id in chapter_start_ills[chap_idx]:
                        new_spine.append(f'<itemref idref="{p_id}" />')
                new_spine.append(f'<itemref idref="{ref}" />')
                # Insert chapter_end illustrations after this chapter
                if chap_idx in chapter_end_ills:
                    for p_id in chapter_end_ills[chap_idx]:
                        new_spine.append(f'<itemref idref="{p_id}" />')
            else:
                new_spine.append(f'<itemref idref="{ref}" />')

        # Prepend frontmatter illustrations (after cover if cover is first)
        frontmatter_ill_refs = [f'<itemref idref="{p_id}" />' for p_id in frontmatter_ills]
        if new_spine and new_spine[0].startswith('<itemref idref="p-cover"'):
            final_spine = [new_spine[0]] + frontmatter_ill_refs + new_spine[1:]
        else:
            final_spine = frontmatter_ill_refs + new_spine

        spine_xml = "\n    ".join(final_spine)

        cover_meta = '<meta name="cover" content="cover-image" />' if has_cover else ""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" xml:lang="ja" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:uuid:{book_uuid}</dc:identifier>
    <dc:title>{escape_xhtml_text(title)}</dc:title>
    <dc:creator>{escape_xhtml_text(author)}</dc:creator>
    <dc:publisher>{escape_xhtml_text(publisher)}</dc:publisher>
    <dc:language>ja</dc:language>
    <meta property="dcterms:modified">2026-09-11T00:00:00Z</meta>
    {cover_meta}
  </metadata>
  <manifest>
    {manifest_xml}
  </manifest>
  <spine page-progression-direction="rtl" toc="ncx">
    {spine_xml}
  </spine>
</package>"""
