from src.easy_mode.phase3.asset_pack import export_asset_pack

def test_export_asset_pack_manifest(tmp_path):
    # 最小構成でマニフェスト生成
    meta = export_asset_pack(
        work_dir=tmp_path,
        episodes=["第1話", "第2話"],
        title="テスト作品"
    )
    assert meta["title"] == "テスト作品"
    assert len(meta["episodes"]) == 2
