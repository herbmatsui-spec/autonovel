import uuid
from typing import Any
from src.services.exporters.epub_content_builder import EpubContentBuilder
from src.services.exporters.epub_manifest_builder import EpubManifestBuilder
from src.services.exporters.pure_epub_packer import PureEpubPacker
from src.services.exporters.vertical_css_templates import VERTICAL_EPUB_CSS


class CommercialEpubBuilder:
    """商用EPUB 3 統合ビルダー (Step 51)。
    書籍情報・チャプター配列・挿絵を受け取り、規格準拠の縦書きEPUBバイナリを出力する。
    """

    def build_commercial_epub(
        self,
        novel_meta: dict[str, Any],
        chapters: list[dict[str, Any]],
        images: list[dict[str, Any]] | None = None,
    ) -> bytes:
        packer = PureEpubPacker()
        packer.add_container_xml("item/standard.opf")

        # 1. スタイルシート
        packer.add_text_file("item/style/vertical.css", VERTICAL_EPUB_CSS)

        book_uuid = str(novel_meta.get("uuid") or uuid.uuid4())
        title = str(novel_meta.get("title") or "無題")
        author = str(novel_meta.get("author") or "AI Novelist")
        publisher = str(novel_meta.get("publisher") or "AutoNovel")

        manifest_items: list[dict[str, str]] = [
            {"id": "style", "href": "style/vertical.css", "media-type": "text/css"},
            {"id": "nav", "href": "nav.xhtml", "media-type": "application/xhtml+xml", "properties": "nav"},
            {"id": "ncx", "href": "toc.ncx", "media-type": "application/x-dtbncx+xml"},
        ]
        spine_items: list[str] = []

        # 2. 表紙 (存在する場合)
        cover_image_bytes = novel_meta.get("cover_image_bytes")
        has_cover = bool(cover_image_bytes)
        if has_cover:
            packer.add_file("item/images/cover.jpg", cover_image_bytes)
            manifest_items.append({
                "id": "cover-image",
                "href": "images/cover.jpg",
                "media-type": "image/jpeg",
                "properties": "cover-image",
            })
            cover_xhtml = EpubManifestBuilder.build_cover_xhtml(
                image_href="images/cover.jpg",
                css_rel_path="style/vertical.css",
            )
            packer.add_text_file("item/xhtml/cover.xhtml", cover_xhtml)
            manifest_items.append({
                "id": "p-cover",
                "href": "xhtml/cover.xhtml",
                "media-type": "application/xhtml+xml",
            })
            spine_items.append("p-cover")

        # 3. 本文チャプター
        chapter_manifest_meta = []
        for i, chap in enumerate(chapters):
            idx = i + 1
            chap_title = str(chap.get("title") or f"第{idx}話")
            chap_content = str(chap.get("content") or "")
            chap_file = f"xhtml/p-{idx:03d}.xhtml"
            chap_id = f"p-{idx:03d}"

            xhtml_str = EpubContentBuilder.build_chapter_xhtml(
                chapter_title=chap_title,
                content=chap_content,
                chapter_index=idx,
                css_rel_path="../style/vertical.css",
            )
            packer.add_text_file(f"item/{chap_file}", xhtml_str)

            manifest_items.append({
                "id": chap_id,
                "href": chap_file,
                "media-type": "application/xhtml+xml",
            })
            spine_items.append(chap_id)
            chapter_manifest_meta.append({"title": chap_title, "href": chap_file})

        # 4. ナビゲーション文書 (nav.xhtml) & NCX (toc.ncx)
        nav_xhtml = EpubManifestBuilder.build_nav_xhtml(
            title=title,
            chapters=chapter_manifest_meta,
            css_rel_path="style/vertical.css",
        )
        packer.add_text_file("item/nav.xhtml", nav_xhtml)

        toc_ncx = EpubManifestBuilder.build_toc_ncx(
            book_uuid=book_uuid,
            title=title,
            chapters=chapter_manifest_meta,
        )
        packer.add_text_file("item/toc.ncx", toc_ncx)

        # 5. OPF パッケージ
        standard_opf = EpubManifestBuilder.build_standard_opf(
            book_uuid=book_uuid,
            title=title,
            author=author,
            publisher=publisher,
            manifest_items=manifest_items,
            spine_items=spine_items,
            has_cover=has_cover,
        )
        packer.add_text_file("item/standard.opf", standard_opf)

        return packer.build_epub_bytes()
