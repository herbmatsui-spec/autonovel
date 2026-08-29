"""Utility for validating the commercial score against real Kakuyomu ranking data.

This module provides:
- ``fetch_top_works``: using Playwright to scrape the Kakuyomu
  ranking page (order=popular) and extract a limited number of works.
- ``compute_correlation``: run ``score_commercial_node`` on each work
  and calculate the Pearson correlation between the number of bookmarks
  (as a proxy for popularity) and the ``commercial_score`` produced by
  the LLM.
- ``run_validation``: CLI entry‑point that prints the correlation.

The implementation is deliberately defensive: the Playwright import is
optional, and clear error messages are raised if the environment lacks the
required browsers. Adjust the CSS selectors in ``fetch_top_works`` if the
Kakuyomu page layout changes.
"""

import asyncio
import logging
import math
from typing import Dict, List

logger = logging.getLogger(__name__)

PLAYWRIGHT_TIMEOUT_MS: int = 30000
BROWSER_LAUNCH_TIMEOUT_MS: int = 60000

# ---------------------------------------------------------------------------
# Playwright based scraper – optional import to avoid hard runtime dependency
# ---------------------------------------------------------------------------
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover – Playwright may be missing in CI
    sync_playwright = None
    logger.warning("playwright not installed – fetch_top_works will be unavailable")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_top_works(limit: int = 20) -> List[Dict]:
    """Scrape Kakuyomu ranking page and return a list of works.

    Each entry contains the following keys:
    - ``work_id``   : Kakuyomu internal identifier (string)
    - ``title``     : Work title
    - ``bookmark``  : Number of bookmarks (int, 0 if parsing fails)
    - ``excerpt``   : First up‑to‑3000 characters of the work's content.

    The function relies on CSS selectors that were observed on the site at
    the time of writing. If the layout changes, adjust the selectors
    accordingly.
    """
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright is not installed. Install with 'pip install playwright' "
            "and run 'python -m playwright install chromium' before using "
            "fetch_top_works()."
        )

    works: List[Dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, timeout=BROWSER_LAUNCH_TIMEOUT_MS)
        page = browser.new_page()
        page.goto("https://kakuyomu.jp/works?order=popular", timeout=PLAYWRIGHT_TIMEOUT_MS)
        page.wait_for_load_state("networkidle", timeout=PLAYWRIGHT_TIMEOUT_MS)

        # Work cards have a data-work-id attribute (observed on the site).
        items = page.query_selector_all("[data-work-id]")
        for item in items[:limit]:
            work_id = item.get_attribute("data-work-id") or ""
            # Title – usually inside an element with class "c-workItem__title"
            title_el = item.query_selector(".c-workItem__title")
            title = title_el.inner_text().strip() if title_el else ""
            # Bookmark count – class may be "c-workItem__bookmark"
            bookmark_el = item.query_selector(".c-workItem__bookmark")
            bookmark_text = bookmark_el.inner_text().strip() if bookmark_el else "0"
            # Keep only digits (the text often contains the Japanese word "ブックマーク")
            bookmark = int("".join(filter(str.isdigit, bookmark_text))) if bookmark_text else 0

            # Open the work page to fetch a short excerpt (first chapter preview)
            page.goto(f"https://kakuyomu.jp/works/{work_id}", timeout=PLAYWRIGHT_TIMEOUT_MS)
            page.wait_for_load_state("networkidle", timeout=PLAYWRIGHT_TIMEOUT_MS)
            # Content preview – observed selector ".c-episode__content"
            content_el = page.query_selector(".c-episode__content")
            excerpt = content_el.inner_text() if content_el else ""
            excerpt = excerpt[:3000]

            works.append({
                "work_id": work_id,
                "title": title,
                "bookmark": bookmark,
                "excerpt": excerpt,
            })
        browser.close()
    return works

# ---------------------------------------------------------------------------
# Correlation calculation – async because the scoring node is async
# ---------------------------------------------------------------------------

async def compute_correlation(works: List[Dict], llm_provider=None) -> float:
    """Run ``score_commercial_node`` for each work and return Pearson r.

    * ``works`` – list produced by ``fetch_top_works`` (or a mock list).
    * ``llm_provider`` – optional LLM provider; if ``None`` the node falls back
      to a deterministic dummy score.
    """
    if not works:
        return 0.0

    from src.backend.workflows.nodes.review_nodes import score_commercial_node

    scores: List[tuple[int, float]] = []
    for work in works:
        state = {
            "ep_num": work.get("work_id", "0"),
            "source_content": work.get("excerpt") or work.get("title", ""),
        }
        result = await score_commercial_node(state, llm_provider=llm_provider)
        scores.append((work.get("bookmark", 0), float(result.get("commercial_score", 0.0))))

    # Pearson correlation
    xs, ys = zip(*scores)
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    var_x = sum((x - mx) ** 2 for x in xs)
    var_y = sum((y - my) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / math.sqrt(var_x * var_y)

async def run_validation(limit: int = 20, llm_provider=None) -> float:
    """非同期コンテキストから呼び出す検証関数"""
    works = await asyncio.to_thread(fetch_top_works, limit)
    return await compute_correlation(works, llm_provider=llm_provider)


def run_validation_sync(limit: int = 20, llm_provider=None) -> None:
    """同期互換性用ラッパー"""
    works = fetch_top_works(limit)
    corr = asyncio.run(run_validation(limit, llm_provider=llm_provider))
    logger.info(
        f"Correlation between bookmark count and commercial_score (n={len(works)}): {corr:.3f}"
    )

if __name__ == "__main__":  # pragma: no cover
    async def _main():
        corr = await run_validation()
        print(f"Correlation: {corr:.3f}")
    asyncio.run(_main())
