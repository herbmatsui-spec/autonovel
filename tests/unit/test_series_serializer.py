"""`series_serializer` の単体テスト。"""
from __future__ import annotations

from src.easy_mode.pipeline import EpisodeResult, SeriesResult
from src.easy_mode.spice_guard import SpiceElement
from src.services.series_serializer import episode_summary, series_to_dict


def _make_episode(num: int = 1) -> EpisodeResult:
    content = "本文テスト" * 100
    return EpisodeResult(
        episode_num=num,
        title=f"第{num}話",
        content=content,
        word_count=len(content),
        audit_score=80.0,
        audit_passed=True,
        rewrite_count=0,
        spice_elements=[SpiceElement(type="unique_metaphor", text="", position=0, priority="low")],
        metadata={"foo": "bar"},
    )


def test_episode_summary_snippet():
    ep = _make_episode(1)
    d = episode_summary(ep)
    assert d["episode_num"] == 1
    assert d["title"] == "第1話"
    assert "content_snippet" in d
    assert len(d["content_snippet"]) <= 200
    assert d["audit_passed"] is True


def test_series_to_dict_includes_count():
    s = SeriesResult(
        genre="x",
        title="タイトル",
        concept="コンセプト",
        total_episodes=2,
        episodes=[_make_episode(1), _make_episode(2)],
        bible={"a": 1},
        plot_outline=[],
        metadata={"k": "v"},
    )
    d = series_to_dict(s)
    assert d["title"] == "タイトル"
    assert d["total_episodes"] == 2
    assert len(d["episodes"]) == 2
    assert d["bible"] == {"a": 1}
    assert d["metadata"] == {"k": "v"}
    assert d["status"] == "completed"
