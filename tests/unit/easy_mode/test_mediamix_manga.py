import pytest
from src.easy_mode.phase3.media_mix import MediaMixExporter, MediaFormat

def test_export_manga_script():
    exporter = MediaMixExporter(genre="fantasy", preset={})
    text = "激しい雷鳴が響いた。アリスは剣を抜いた。「覚悟しなさい！」"
    script = exporter.convert_to_manga(text)
    assert script is not None
    assert len(script.panels) >= 1