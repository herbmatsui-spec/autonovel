from src.easy_mode.phase3.media_mix import MediaFormat, Panel

def test_media_format_enum_values():
    assert MediaFormat.MANGA == "manga"
    assert MediaFormat.AUDIO_DRAMA == "audio_drama"
    assert MediaFormat.VIDEO == "video"

def test_panel_creation():
    panel = Panel(
        number=1,
        description="主人公が立ち尽くす",
        dialogue=["「信じられない……」"],
        camera_angle="wide",
        sfx=["ゴゴゴ…"]
    )
    assert panel.number == 1
    assert len(panel.dialogue) == 1
    assert panel.camera_angle == "wide"
