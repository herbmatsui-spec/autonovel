from src.easy_mode.phase3.asset_pack import AssetPackGenerator

def test_asset_pack_generator_init():
    gen = AssetPackGenerator(genre="ファンタジー", preset={})
    assert gen.genre == "ファンタジー"
    assert gen.preset == {}
    assert gen.if_generator is None
    assert gen.media_exporter is None
    assert gen.ebook_exporter is None
