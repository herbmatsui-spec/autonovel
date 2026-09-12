"""商用縦書きEPUBの挿絵・口絵統合単体テスト (Part 3: Step 35, 36)。"""

import io
import zipfile
import pytest

from src.services.exporters.epub_commercial_builder import CommercialEpubBuilder
from src.services.exporters.epub_manifest_builder import EpubIllustrationItem


# 1x1 ダミーJPEGバイナリ
DUMMY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00"
    b"\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19"
    b"\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9"
    b"=@0821\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00"
    b"\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04"
    b"\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)


def test_commercial_epub_with_illustrations():
    """口絵および章間挿絵を含む商用EPUBの生成と整合性検証。"""
    builder = CommercialEpubBuilder()

    chapters = [
        {"title": "第1話 始まりの朝", "content": "「起きろ！」と母が叫んだ。\n朝日が眩しい。"},
        {"title": "第2話 旅立ちの森", "content": "深い森の奥で、タロウは奇妙な光を見た。"},
    ]

    images = [
        # 口絵（カラー巻頭イラスト）
        {
            "image_id": "front_color",
            "image_bytes": DUMMY_JPEG,
            "file_name": "frontmatter_color.jpg",
            "position": "frontmatter",
            "caption": "カラー口絵: 冒険の始まり",
        },
        # 第2章の直前挿絵
        EpubIllustrationItem(
            image_id="forest_beast",
            image_bytes=DUMMY_JPEG,
            file_name="forest_beast.jpg",
            position="chapter_start",
            chapter_index=2,
            caption="森の奥に潜む巨影",
        ),
    ]

    epub_bytes = builder.build_commercial_epub(
        novel_meta={"title": "テスト冒険譚", "author": "テスト作家"},
        chapters=chapters,
        images=images,
    )

    assert len(epub_bytes) > 0

    # ZIP 構造の検証
    with zipfile.ZipFile(io.BytesIO(epub_bytes), "r") as zf:
        namelist = zf.namelist()

        # 1. 規格必須ファイル
        assert "mimetype" in namelist
        assert "META-INF/container.xml" in namelist
        assert "item/standard.opf" in namelist
        assert "item/nav.xhtml" in namelist

        # 2. 画像ファイルが格納されていること
        assert "item/images/frontmatter_color.jpg" in namelist
        assert "item/images/forest_beast.jpg" in namelist

        # 3. 挿絵XHTMLページが格納されていること
        assert "item/xhtml/ill-front_color.xhtml" in namelist
        assert "item/xhtml/ill-forest_beast.xhtml" in namelist

        # 4. standard.opf の内容検証
        opf_text = zf.read("item/standard.opf").decode("utf-8")
        assert 'id="img-front_color"' in opf_text
        assert 'id="img-forest_beast"' in opf_text
        assert 'id="p-ill-front_color"' in opf_text
        assert 'id="p-ill-forest_beast"' in opf_text

        # Spine に挿絵ページが入っていること
        assert '<itemref idref="p-ill-front_color"' in opf_text
        assert '<itemref idref="p-ill-forest_beast"' in opf_text

        # 口絵が第1章の前、第2章挿絵が第2章の前に配置されている順序検証
        pos_ill_front = opf_text.find('idref="p-ill-front_color"')
        pos_p001 = opf_text.find('idref="p-001"')
        pos_ill_beast = opf_text.find('idref="p-ill-forest_beast"')
        pos_p002 = opf_text.find('idref="p-002"')

        assert pos_ill_front < pos_p001, "口絵は第1話の前に配置されるべき"
        assert pos_p001 < pos_ill_beast, "第2話挿絵は第1話の後に配置されるべき"
        assert pos_ill_beast < pos_p002, "第2話挿絵は第2話の前に配置されるべき"

        # 5. nav.xhtml 目次に挿絵ページが含まれていないこと (Step 29)
        nav_text = zf.read("item/nav.xhtml").decode("utf-8")
        assert "ill-" not in nav_text
        assert "第1話 始まりの朝" in nav_text
        assert "第2話 旅立ちの森" in nav_text

        # 6. 挿絵 XHTML のマークアップ検証 (Step 26, 38)
        ill_front_xhtml = zf.read("item/xhtml/ill-front_color.xhtml").decode("utf-8")
        assert 'class="p-illustration"' in ill_front_xhtml
        assert 'class="illustration-wrap"' in ill_front_xhtml
        assert 'class="illustration-caption"' in ill_front_xhtml
        assert "カラー口絵: 冒険の始まり" in ill_front_xhtml


def test_commercial_epub_without_images():
    """画像なしの通常エクスポートが破綻しないことを検証。"""
    builder = CommercialEpubBuilder()
    chapters = [{"title": "第1話", "content": "本文"}]
    epub_bytes = builder.build_commercial_epub(
        novel_meta={"title": "テキストのみの本"},
        chapters=chapters,
        images=None,
    )
    assert len(epub_bytes) > 0
    with zipfile.ZipFile(io.BytesIO(epub_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "item/xhtml/p-001.xhtml" in namelist
        assert not any(name.startswith("item/images/") for name in namelist)
