"""tests/services/test_kakuyomu_scraper.py

Unit tests for the opt-in Kakuyomu scraper. These tests are pure
unit tests – no real network access is performed. Instead, we
construct the scraper with a stub ``_http_get_raw`` and assert the
filtering, parsing, and opt-in behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.services import kakuyomu_scraper as ks  # noqa: E402
from src.services.kakuyomu_scraper import (  # noqa: E402
    KakuyomuScraper,
    OptInDisabled,
    RobotsDisallowed,
    build_scraper_from_settings,
)


RANKING_HTML = """
<html><body>
  <a href="/works/16816927863019427894">work 1</a>
  <a href="/works/16816927863019427894">dup</a>
  <a href="/works/16817139558294412594">work 2</a>
  <a href="/works/999/episodes/1">bad link ignored</a>
</body></html>
"""

WORK_HTML = """
<html><head>
  <meta property="og:title" content="テスト作品 - カクヨム" />
  <meta property="og:description" content="あらすじです。&lt;b&gt;強調&lt;/b&gt;も含む。" />
  <meta name="description" content="fallback" />
</head><body>
  <a class="tag" href="/tags/xyz">タグA</a>
  <a class="tag" href="/tags/abc">タグB</a>
  <a href="/works/16816927863019427894/episodes/1">第一話 旅立ち</a>
  <a href="/works/16816927863019427894/episodes/2">第二話 再会</a>
  <a href="/works/16816927863019427894/episodes/2">第二話 再会</a>
</body></html>
"""


class _StubScraper(KakuyomuScraper):
    """Scraper variant that returns canned HTML instead of HTTP."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.requests: list[str] = []

    def _http_get_raw(self, url: str) -> str:  # type: ignore[override]
        # Always go through the parent's allow-check so the production
        # robots.txt code path is exercised.
        if not self._is_allowed(url):
            from src.services.kakuyomu_scraper import RobotsDisallowed
            raise RobotsDisallowed(f"Refused by robots.txt: {url}")
        self.requests.append(url)
        if url.endswith("/robots.txt"):
            return (
                "User-agent: *\n"
                "Disallow: /works/*/episodes/*/read$\n"
                "Disallow: /login?\n"
            )
        if "/rankings/" in url:
            return RANKING_HTML
        if "/works/" in url:
            return WORK_HTML
        raise AssertionError(f"Unexpected URL: {url}")


def _settings_stub(**overrides):
    base = dict(
        kakuyomu_ingest_enabled=True,
        kakuyomu_request_interval=0.0,
        kakuyomu_user_agent="test-bot",
        kakuyomu_ingest_limit=5,
    )
    base.update(overrides)

    class _S:
        pass

    s = _S()
    for k, v in base.items():
        setattr(s, k, v)
    return s


def test_opt_in_disabled_raises():
    s = _StubScraper(enabled=False, request_interval=0.0)
    assert s.is_enabled() is False
    with pytest.raises(OptInDisabled):
        s.fetch_ranking()
    with pytest.raises(OptInDisabled):
        s.fetch_work_meta("123")


def test_robots_disallowed_for_episode_read_url():
    s = KakuyomuScraper(enabled=True, request_interval=0.0)
    # Pre-seed the disallow list (the production fetcher would obtain
    # this from robots.txt; here we avoid that round-trip).
    s._disallow_prefixes = [
        "/works/*/episodes/*/read$",
        "/login?",
    ]
    s._robots_loaded = True
    assert not s._is_allowed(
        "https://kakuyomu.jp/works/1/episodes/2/read"
    )
    # Work overview pages remain allowed.
    assert s._is_allowed("https://kakuyomu.jp/works/16816927863019427894")


def test_robots_allows_public_pages():
    s = _StubScraper(enabled=True, request_interval=0.0)
    assert s._is_allowed("https://kakuyomu.jp/rankings/all/weekly?work_variation=long")
    assert s._is_allowed("https://kakuyomu.jp/works/16816927863019427894")
    # login? is disallowed
    assert not s._is_allowed("https://kakuyomu.jp/login?x=1")


def test_fetch_ranking_parses_and_dedupes():
    s = _StubScraper(enabled=True, request_interval=0.0, max_works=10)
    works = s.fetch_ranking()
    assert [w.work_id for w in works] == [
        "16816927863019427894",
        "16817139558294412594",
    ]
    # The only HTTP calls should be robots.txt + ranking + 2x work pages.
    assert any(u.endswith("/robots.txt") for u in s.requests)
    assert any("/rankings/" in u for u in s.requests)
    assert any(u.endswith("/works/16816927863019427894") for u in s.requests)
    # No episode read URLs are ever hit.
    assert not any("/episodes/" in u and u.endswith("/read") for u in s.requests)


def test_fetch_work_meta_parses_og_and_tags():
    s = _StubScraper(enabled=True, request_interval=0.0)
    meta = s.fetch_work_meta("16816927863019427894")
    assert meta.title == "テスト作品"
    assert "あらすじ" in meta.synopsis
    assert "<b>" in meta.synopsis  # entity unescaped
    assert meta.tags == ["タグA", "タグB"]
    assert meta.episode_titles == ["第一話 旅立ち", "第二話 再会"]
    assert meta.source_url == "https://kakuyomu.jp/works/16816927863019427894"


def test_invalid_inputs():
    s = _StubScraper(enabled=True, request_interval=0.0)
    with pytest.raises(ValueError):
        s.fetch_ranking(genre="not-a-genre")
    with pytest.raises(ValueError):
        s.fetch_ranking(period="hourly")
    with pytest.raises(ValueError):
        s.fetch_ranking(variation="medium")
    with pytest.raises(ValueError):
        s.fetch_work_meta("../etc/passwd")


def test_throttle_enforces_interval(monkeypatch):
    sleeps = []
    monkeypatch.setattr(ks.time, "sleep", lambda x: sleeps.append(x))
    s = KakuyomuScraper(
        enabled=True, request_interval=1.5, user_agent="x", max_works=2
    )
    # Drive the throttle directly – we only want to verify pacing.
    s._throttle()
    s._throttle()
    assert sleeps, "throttle should have slept at least once"
    assert all(x >= 0 for x in sleeps)


def test_build_scraper_from_settings():
    s = build_scraper_from_settings(_settings_stub())
    assert s.enabled is True
    assert s.user_agent == "test-bot"
    assert s.max_works == 5
    assert s.request_interval == 0.0


def test_build_scraper_defaults_to_disabled():
    class _S:
        pass

    s = build_scraper_from_settings(_S())
    assert s.enabled is False
    assert s.max_works == 10
