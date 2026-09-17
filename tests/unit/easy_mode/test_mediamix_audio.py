from src.easy_mode.phase3.media_mix import MediaMixExporter

def test_export_audio_drama_script():
    exporter = MediaMixExporter(genre="fantasy", preset={})
    text = "雨音が静かに窓を叩く。ボブ「今夜は冷えるな」"
    script = exporter.convert_to_audio_drama(text)
    assert script is not None
    assert "雨音" in str(script) or "ボブ" in str(script)
