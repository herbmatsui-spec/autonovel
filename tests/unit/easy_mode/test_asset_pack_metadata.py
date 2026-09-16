from src.easy_mode.phase3.asset_pack import AssetPackMetadata

def test_asset_pack_metadata_summary():
    meta = AssetPackMetadata(
        pack_id="pack-001",
        title="覇権物語パック",
        genre="ファンタジー",
        episode_count=5,
        total_words=25000
    )
    assert meta.pack_id == "pack-001"
    assert meta.total_words == 25000
