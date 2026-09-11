import uuid
from src.services.exporters.text_sanitizer import escape_xhtml_text


class EpubManifestBuilder:
    """EPUB 3 ナビゲーション文書 (nav.xhtml), NCX目次 (toc.ncx), OPF (standard.opf) 生成器 (Steps 43, 44, 45, 52)。"""

    @staticmethod
    def build_nav_xhtml(
        title: str,
        chapters: list[dict[str, str]],
        css_rel_path: str = "style/vertical.css",
    ) -> str:
        """EPUB 3 ナビゲーション文書 (nav.xhtml) の自動生成 (Step 43)。"""
        nav_items = []
        for i, chap in enumerate(chapters):
            href = chap.get("href", f"xhtml/p-{i+1:03d}.xhtml")
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
    ) -> str:
        """旧規格・Kindle互換用 NCX 目次 (toc.ncx) の二重生成 (Step 44)。"""
        nav_points = []
        for i, chap in enumerate(chapters):
            href = chap.get("href", f"xhtml/p-{i+1:03d}.xhtml")
            chap_title = escape_xhtml_text(chap.get("title", f"第{i+1}話"))
            order = i + 1
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
    ) -> str:
        """OPF マニフェスト・スパインの生成（Kindle縦書き・右開き page-progression-direction="rtl" 準拠）(Step 52)。"""
        items = manifest_items or []
        item_tags = []
        for it in items:
            props = f' properties="{it["properties"]}"' if "properties" in it else ""
            item_tags.append(f'<item id="{it["id"]}" href="{it["href"]}" media-type="{it["media-type"]}"{props} />')

        spines = spine_items or []
        spine_tags = [f'<itemref idref="{ref}" />' for ref in spines]

        manifest_xml = "\n    ".join(item_tags)
        spine_xml = "\n    ".join(spine_tags)

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
