import zipfile
from src.easy_mode.phase3.asset_pack import pack_to_zip

def test_pack_to_zip(tmp_path):
    target_dir = tmp_path / "assets"
    target_dir.mkdir()
    (target_dir / "story.txt").write_text("本文テキスト", encoding="utf-8")

    zip_path = tmp_path / "bundle.zip"
    pack_to_zip(str(target_dir), str(zip_path))

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert "story.txt" in zf.namelist()
