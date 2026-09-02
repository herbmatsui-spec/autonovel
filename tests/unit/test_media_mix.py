"""src.easy_mode.phase3.media_mix の単体テスト。"""
from __future__ import annotations

import json

from src.easy_mode.phase3.media_mix import (
    AudioCue,
    AudioDramaScriptGenerator,
    MediaFormat,
    Panel,
    VoiceLine,
    create_media_mix_exporter,
)
from src.easy_mode.pipeline import EpisodeResult, SeriesResult
from src.easy_mode.spice_guard import SpiceElement


def _make_episode(num: int = 1) -> EpisodeResult:
    content = (
        "第1話: テスト\n"
        "\n"
        "主人公は森の奥へと足を踏み入れた。\n"
        "\n"
        "「誰かいるのか」\n"
        "\n"
        "返事はない。ただ木々のざわめきだけが響く。\n"
    )
    return EpisodeResult(
        episode_num=num,
        title="テスト話",
        content=content,
        word_count=len(content),
        audit_score=88.0,
        audit_passed=True,
        rewrite_count=0,
        spice_elements=[SpiceElement(type="unique_metaphor", text="", position=0, priority="low")],
        metadata={},
    )


def _make_series(eps: list[EpisodeResult] | None = None) -> SeriesResult:
    eps = eps or [_make_episode(1)]
    return SeriesResult(
        genre="ハイファンタジー (R15)",
        title="テストシリーズ",
        concept="テスト",
        total_episodes=len(eps),
        episodes=eps,
        bible={},
        plot_outline=[],
        metadata={"prologue": "始まりの物語"},
    )


def test_panel_to_dict():
    panel = Panel(
        number=1,
        description="森のシーン",
        dialogue=["「誰かいるのか」"],
        narration="静寂が支配する",
        sfx=["ドドド"],
        camera_angle="wide",
        characters=["主人公"],
        background="深い森",
        mood="mysterious",
    )
    d = panel.to_dict()
    assert d["number"] == 1
    assert d["dialogue"] == ["「誰かいるのか」"]
    assert d["mood"] == "mysterious"


def test_audio_cue_to_dict():
    cue = AudioCue(
        type="bgm", name="tension", description="不穏な BGM", duration=10.0, volume=0.8
    )
    d = cue.to_dict()
    assert d["type"] == "bgm"
    assert d["duration"] == 10.0


def test_voice_line_to_dict():
    line = VoiceLine(
        character="主人公",
        text="行くぞ",
        emotion="determined",
        direction="低く",
    )
    d = line.to_dict()
    assert d["character"] == "主人公"
    assert d["emotion"] == "determined"


def test_audio_drama_generator_produces_script():
    gen = AudioDramaScriptGenerator("ハイファンタジー (R15)", {"characters": {"archetypes": {}}, "erotic": {}})
    episode = _make_episode(1)
    series = _make_series([episode])
    script = gen.generate(episode, series)
    assert script.format == MediaFormat.AUDIO_DRAMA
    assert script.episode_num == 1
    assert isinstance(script.voice_lines, list)
    assert len(script.voice_lines) > 0
    # JSON 化できる
    json.loads(script.to_json())


def test_create_media_mix_exporter_runs():
    exporter = create_media_mix_exporter(
        "ハイファンタジー (R15)", {"characters": {"archetypes": {}}, "erotic": {}}
    )
    series = _make_series([_make_episode(1)])
    scripts = exporter.export_all(series.episodes[0], series, [MediaFormat.MANGA])
    assert MediaFormat.MANGA in scripts
    assert scripts[MediaFormat.MANGA].format == MediaFormat.MANGA
