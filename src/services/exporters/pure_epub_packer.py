import io
import zipfile


class PureEpubPacker:
    """ebooklib非依存の Pure Python ZIPベース EPUB 3 パッカー (Steps 49, 50)。
    - mimetype は非圧縮 (ZIP_STORED) かつアーカイブの最先頭に配置
    - META-INF/container.xml の標準出力
    """

    def __init__(self):
        self.entries: list[tuple[str, bytes, int]] = []

    def add_file(self, arcname: str, data: bytes, compress: bool = True) -> None:
        c_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
        self.entries.append((arcname, data, c_type))

    def add_text_file(self, arcname: str, text: str, compress: bool = True, encoding: str = "utf-8") -> None:
        self.add_file(arcname, text.encode(encoding), compress=compress)

    def add_container_xml(self, opf_path: str = "item/standard.opf") -> None:
        """META-INF/container.xml を追加 (Step 50)。"""
        container_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="{opf_path}" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
        self.add_text_file("META-INF/container.xml", container_xml, compress=True)

    def build_epub_bytes(self) -> bytes:
        """規格厳格準拠のEPUB 3バイナリを構築する。"""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            # 1. 規格必須: mimetype は無圧縮かつ先頭
            zf.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)

            # 2. その他のファイル群
            for path, data, c_type in self.entries:
                if path == "mimetype":
                    continue
                zf.writestr(path, data, compress_type=c_type)

        res = buf.getvalue()
        # EPUB 3 規格適合性検証 (Step 43)
        with zipfile.ZipFile(io.BytesIO(res), "r") as check_zf:
            infolist = check_zf.infolist()
            if not infolist or infolist[0].filename != "mimetype":
                raise ValueError("EPUB 3 violation: 'mimetype' must be the first file in archive")
            if infolist[0].compress_type != zipfile.ZIP_STORED:
                raise ValueError("EPUB 3 violation: 'mimetype' must be uncompressed (ZIP_STORED)")

        return res
