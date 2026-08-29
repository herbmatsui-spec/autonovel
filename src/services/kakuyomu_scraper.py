"""src/services/kakuyomu_scraper.py

Opt-in scraper for the public Kakuyomu (カクヨム) ranking pages.

Design constraints
------------------
* **Opt-in only.** Entry points no-op unless
  ``settings.kakuyomu_ingest_enabled`` is True.
* **robots.txt compliance.** The scraper downloads and parses
  https://kakuyomu.jp/robots.txt at startup and refuses to fetch any
  URL that matches a ``Disallow`` rule. The ``/works/*/episodes/*/read$``
  pattern is therefore **never** hit by this module – we only fetch the
  public ranking pages and the public work overview page (no individual
  episode bodies).
* **Politeness.** A configurable interval (``kakuyomu_request_interval``,
  default 2.0s) is enforced between HTTP requests.
* **Identification.** A descriptive ``User-Agent`` is required (operators
  must override ``kakuyomu_user_agent`` to provide real contact info).
* **No login / no personal data.** We never authenticate, and we only
  collect publicly visible metadata (title, author handle, synopsis,
  tag list, episode titles). Author display name is *not* persisted.
"""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

BASE_URL = "https://kakuyomu.jp"
ROBOTS_URL = f"{BASE_URL}/robots.txt"

# Ranking URL template: /rankings/<genre>/<period>?work_variation=<variation>
DEFAULT_RANKING = "/rankings/all/weekly?work_variation=long"
VALID_PERIODS = {"daily", "weekly", "monthly", "yearly", "entire"}
VALID_VARIATIONS = {"all", "long", "short"}
VALID_GENRES = {
    "all",
    "action",
    "criticism",
    "drama",
    "fantasy",
    "history",
    "horror",
    "love_story",
    "mystery",
    "nonfiction",
    "others",
    "romance",
    "sf",
}

WORK_ID_RE = re.compile(r"^/works/(\d+)$")
WORK_HREF_RE = re.compile(r'href="(/works/\d+)"')
OG_TITLE_RE = re.compile(
    r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"'
)
OG_DESC_RE = re.compile(
    r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"'
)
META_DESC_RE = re.compile(
    r'<meta[^>]+name="description"[^>]+content="([^"]+)"'
)
EPISODE_HREF_RE = re.compile(
    r'href="(/works/\d+/episodes/\d+)"'
)
TAG_RE = re.compile(
    r'<a[^>]+class="[^"]*tag[^"]*"[^>]*>([^<]+)</a>'
)


@dataclass
class WorkMeta:
    """Public metadata for one Kakuyomu work.

    Note: we deliberately do **not** store the author's display name.
    Only the work id and the public handle slug (which is part of the
    work URL) are kept.
    """

    work_id: str
    title: str
    synopsis: str
    tags: List[str] = field(default_factory=list)
    episode_titles: List[str] = field(default_factory=list)
    source_url: str = ""

    def to_dict(self) -> dict:
        return {
            "work_id": self.work_id,
            "title": self.title,
            "synopsis": self.synopsis,
            "tags": list(self.tags),
            "episode_titles": list(self.episode_titles),
            "source_url": self.source_url,
        }


class OptInDisabled(RuntimeError):
    """Raised when the opt-in flag is off and a fetch is requested."""


class RobotsDisallowed(RuntimeError):
    """Raised when a URL is disallowed by robots.txt."""


class KakuyomuScraper:
    """Minimal, opt-in scraper for public Kakuyomu ranking metadata.

    Parameters
    ----------
    enabled:
        Whether scraping is allowed. When ``False`` every public method
        raises :class:`OptInDisabled` *except* :meth:`is_enabled`.
    request_interval:
        Seconds to sleep between HTTP requests.
    user_agent:
        The ``User-Agent`` string to send. Operators are expected to
        override the default with real contact information.
    cache_dir:
        Where to cache the ``robots.txt`` and ranking HTML. ``None``
        disables on-disk caching.
    """

    def __init__(
        self,
        enabled: bool,
        request_interval: float = 2.0,
        user_agent: str = "autonovel-bot/0.1",
        cache_dir: Optional[Path] = None,
        max_works: int = 10,
    ) -> None:
        self.enabled = enabled
        self.request_interval = max(0.0, float(request_interval))
        self.user_agent = user_agent
        self.max_works = max(1, int(max_works))
        self._cache_dir = cache_dir
        self._last_request_at = 0.0
        self._disallow_prefixes: List[str] = []
        self._robots_loaded = False

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def is_enabled(self) -> bool:
        return bool(self.enabled)

    def fetch_ranking(
        self,
        genre: str = "all",
        period: str = "weekly",
        variation: str = "long",
    ) -> List[WorkMeta]:
        """Fetch the work-id list of one ranking page.

        Only the *first* ranking page is consulted (top-~30 entries),
        then we cap to ``max_works`` after metadata enrichment.
        """
        if not self.enabled:
            raise OptInDisabled(
                "Kakuyomu ingestion is disabled. Set "
                "settings.kakuyomu_ingest_enabled = true to enable."
            )
        if genre not in VALID_GENRES:
            raise ValueError(f"Unknown genre: {genre!r}")
        if period not in VALID_PERIODS:
            raise ValueError(f"Unknown period: {period!r}")
        if variation not in VALID_VARIATIONS:
            raise ValueError(f"Unknown variation: {variation!r}")

        url = f"{BASE_URL}/rankings/{genre}/{period}?work_variation={variation}"
        html = self._get(url)
        work_ids = self._extract_work_ids(html)
        # Deduplicate while preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for wid in work_ids:
            if wid in seen:
                continue
            seen.add(wid)
            ordered.append(wid)

        results: List[WorkMeta] = []
        for wid in ordered[: self.max_works]:
            try:
                meta = self.fetch_work_meta(wid)
            except RobotsDisallowed:
                # Defensive: should not happen for /works/<id>
                continue
            results.append(meta)
        return results

    def fetch_work_meta(self, work_id: str) -> WorkMeta:
        """Fetch the public overview page for a single work.

        The individual episode body (``/episodes/<id>/read``) is
        explicitly *not* fetched, as it is disallowed by robots.txt.
        """
        if not self.enabled:
            raise OptInDisabled(
                "Kakuyomu ingestion is disabled. Set "
                "settings.kakuyomu_ingest_enabled = true to enable."
            )
        if not WORK_ID_RE.match(f"/works/{work_id}"):
            raise ValueError(f"Invalid work id: {work_id!r}")
        url = f"{BASE_URL}/works/{work_id}"
        html = self._get(url)
        return self._parse_work_html(work_id, url, html)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_robots(self) -> None:
        if self._robots_loaded:
            return
        self._robots_loaded = True
        try:
            html = self._http_get_raw(ROBOTS_URL)
        except Exception:
            # Fail closed: if robots.txt cannot be fetched, disallow everything.
            self._disallow_prefixes = ["/"]
            return
        prefixes: List[str] = []
        for line in html.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            if key.strip().lower() == "disallow" and value.strip():
                prefixes.append(value.strip())
        self._disallow_prefixes = prefixes

    def _is_allowed(self, url: str) -> bool:
        self._ensure_robots()
        parts = urllib.parse.urlsplit(url)
        path = parts.path or "/"
        # Some robots.txt rules target the raw URL (path + "?" + query).
        # We compare against both the bare path and the path+query form.
        candidates = [path]
        if parts.query:
            candidates.append(f"{path}?{parts.query}")
        for prefix in self._disallow_prefixes:
            if prefix == "/":
                return False
            # robots.txt uses simple prefix matching. ``*`` is treated
            # as "any characters" (RFC 9309 §2.2.2) – we approximate
            # by allowing any non-empty run of path characters.
            if prefix.endswith("$"):
                anchored = prefix[:-1]
                # Translate ``*`` -> ``[^/]*`` for end-anchored patterns.
                regex = "^" + re.escape(anchored).replace(r"\*", r"[^/]+") + "$"
                if any(re.match(regex, c) for c in candidates):
                    return False
            else:
                # Translate ``*`` to "any chars" in the prefix matcher.
                regex_pat = "^" + re.escape(prefix).replace(r"\*", r".*")
                if any(re.match(regex_pat, c) for c in candidates):
                    return False
        return True

    def _throttle(self) -> None:
        if self.request_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _http_get_raw(self, url: str) -> str:
        if not self._is_allowed(url):
            raise RobotsDisallowed(f"Refused by robots.txt: {url}")
        self._throttle()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ja,en;q=0.5",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 - we trust the BASE_URL host
            raw = resp.read()
        return raw.decode("utf-8", errors="replace")

    def _cache_key(self, url: str) -> Optional[Path]:
        if self._cache_dir is None:
            return None
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        # Use a flat filename – only public URLs are cached.
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", url)
        return self._cache_dir / safe

    def _get(self, url: str) -> str:
        cache = self._cache_key(url)
        if cache is not None and cache.exists():
            try:
                return cache.read_text(encoding="utf-8")
            except OSError:
                pass
        body = self._http_get_raw(url)
        if cache is not None:
            try:
                cache.write_text(body, encoding="utf-8")
            except OSError:
                pass
        return body

    @staticmethod
    def _extract_work_ids(html: str) -> List[str]:
        ids: list[str] = []
        for match in WORK_HREF_RE.finditer(html):
            href = match.group(1)
            m = WORK_ID_RE.match(href)
            if m:
                ids.append(m.group(1))
        return list(ids)

    @staticmethod
    def _parse_work_html(work_id: str, url: str, html: str) -> WorkMeta:
        # og:title is preferred; fall back to <title> minus the trailing
        # " - カクヨム" branding.
        title_match = OG_TITLE_RE.search(html)
        if title_match:
            raw_title = title_match.group(1)
            title = raw_title.split(" - カクヨム")[0].strip()
        else:
            title = work_id

        synopsis = ""
        desc_match = OG_DESC_RE.search(html) or META_DESC_RE.search(html)
        if desc_match:
            synopsis = _html_unescape(desc_match.group(1)).strip()

        tags = [t.strip() for t in TAG_RE.findall(html) if t.strip()]
        # de-dup
        tags = list(dict.fromkeys(tags))

        episode_titles: List[str] = []
        for m in EPISODE_HREF_RE.finditer(html):
            pass  # titles are not embedded as text in the href;
                  # they appear in the surrounding <a>…</a> chunk.
        # Pull episode titles from anchor text directly.
        for m in re.finditer(
            r'<a[^>]+href="(/works/\d+/episodes/\d+)"[^>]*>([^<]+)</a>',
            html,
        ):
            text = _html_unescape(m.group(2)).strip()
            if text and text not in episode_titles:
                episode_titles.append(text)

        return WorkMeta(
            work_id=work_id,
            title=title,
            synopsis=synopsis,
            tags=tags,
            episode_titles=episode_titles,
            source_url=url,
        )


def _html_unescape(text: str) -> str:
    """Tiny HTML-entity unescaper (avoids an html import)."""
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )


# ----------------------------------------------------------------------
# Factory helper
# ----------------------------------------------------------------------


def build_scraper_from_settings(
    settings_obj,
    cache_dir: Optional[Path] = None,
) -> KakuyomuScraper:
    """Build a :class:`KakuyomuScraper` from a settings object.

    The settings object is duck-typed: it just needs the four attributes
    ``kakuyomu_ingest_enabled``, ``kakuyomu_request_interval``,
    ``kakuyomu_user_agent`` and ``kakuyomu_ingest_limit``.
    """
    return KakuyomuScraper(
        enabled=bool(getattr(settings_obj, "kakuyomu_ingest_enabled", False)),
        request_interval=float(
            getattr(settings_obj, "kakuyomu_request_interval", 2.0)
        ),
        user_agent=str(
            getattr(
                settings_obj,
                "kakuyomu_user_agent",
                "autonovel-bot/0.1",
            )
        ),
        max_works=int(getattr(settings_obj, "kakuyomu_ingest_limit", 10)),
        cache_dir=cache_dir,
    )
