"""scripts/ingest_kakuyomu.py

Opt-in CLI to fetch the top-N entries of a public Kakuyomu ranking and
write their public metadata (title, synopsis, tag list, episode titles)
to ``data/kakuyomu_corpus/``.

This script **does not** fetch individual episode bodies – those URLs
are disallowed by ``robots.txt`` and the scraper enforces that. The
collected metadata is intended to be used as a light-weight style
reference by :func:`src.services.style_learning.learn_from_corpus`.

Usage
-----
    # Dry-run (prints what would be done, performs no HTTP requests)
    python -m scripts.ingest_kakuyomu --genre fantasy --period weekly --dry-run

    # Real run (requires kakuyomu_ingest_enabled = true in settings.toml)
    python -m scripts.ingest_kakuyomu --genre fantasy --limit 5

    # Then, for a given book workspace, refresh STYLE_LEARNED.md from the corpus
    python -m scripts.ingest_kakuyomu --apply-style --book-id 1
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on sys.path when run as ``python scripts/ingest_kakuyomu.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from config.settings import ConfigManager  # noqa: E402
from src.services.kakuyomu_scraper import (  # noqa: E402
    DEFAULT_RANKING,
    OptInDisabled,
    WorkMeta,
    build_scraper_from_settings,
)

DEFAULT_CORPUS_DIR = _REPO_ROOT / "data" / "kakuyomu_corpus"


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--genre", default="all")
    p.add_argument("--period", default="weekly",
                   choices=["daily", "weekly", "monthly", "yearly", "entire"])
    p.add_argument("--variation", default="long",
                   choices=["all", "long", "short"])
    p.add_argument("--limit", type=int, default=None,
                   help="Override settings.kakuyomu_ingest_limit")
    p.add_argument("--corpus-dir", default=str(DEFAULT_CORPUS_DIR))
    p.add_argument("--dry-run", action="store_true",
                   help="Print plan, perform no HTTP I/O.")
    p.add_argument("--apply-style", action="store_true",
                   help="After ingesting, run style_learning.learn_from_corpus() "
                        "on --book-id.")
    p.add_argument("--book-id", type=int, default=1)
    p.add_argument("--branch-id", type=int, default=1)
    p.add_argument("--ranking-url", default=DEFAULT_RANKING,
                   help="Display-only: the ranking URL that will be used.")
    return p.parse_args(argv)


def _write_work(corpus_root: Path, meta: WorkMeta) -> None:
    work_dir = corpus_root / meta.work_id
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "meta.json").write_text(
        json.dumps(meta.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (work_dir / "synopsis.txt").write_text(
        meta.synopsis + "\n", encoding="utf-8"
    )
    (work_dir / "episode_titles.txt").write_text(
        "\n".join(meta.episode_titles) + "\n", encoding="utf-8"
    )
    (work_dir / "tags.txt").write_text(
        "\n".join(meta.tags) + "\n", encoding="utf-8"
    )


def _write_manifest(
    corpus_root: Path,
    works: list,
    genre: str,
    period: str,
    variation: str,
) -> None:
    manifest = {
        "ranking": f"/rankings/{genre}/{period}?work_variation={variation}",
        "source": "kakuyomu.jp (public metadata only)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(works),
        "works": [w.work_id for w in works],
    }
    (corpus_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main(argv=None) -> int:
    args = _parse_args(argv)
    # ConfigManager.get_config() reads settings.toml via ConfigValidator,
    # ensuring kakuyomu_ingest_enabled reflects the current file state.
    settings = ConfigManager.get_config()

    if not bool(getattr(settings, "kakuyomu_ingest_enabled", False)) and not args.dry_run:
        print(
            "ERROR: kakuyomu_ingest_enabled is false.\n"
            "       This feature is opt-in. Set it to true in "
            "config/settings.toml\n"
            "       (or pass --dry-run to preview the plan).",
            file=sys.stderr,
        )
        return 2

    limit = args.limit or int(
        getattr(settings, "kakuyomu_ingest_limit", 10)
    )
    corpus_root = Path(args.corpus_dir)
    corpus_root.mkdir(parents=True, exist_ok=True)

    print(
        f"[kakuyomu] ranking={args.ranking_url}  "
        f"genre={args.genre} period={args.period} variation={args.variation} "
        f"limit={limit}"
    )
    if args.dry_run:
        print("[kakuyomu] dry-run: no HTTP requests will be made.")
        return 0

    scraper = build_scraper_from_settings(
        settings_obj=settings,
        cache_dir=corpus_root / "_cache",
    )
    # honour the explicit --limit override
    scraper.max_works = max(1, int(limit))

    try:
        works = scraper.fetch_ranking(
            genre=args.genre,
            period=args.period,
            variation=args.variation,
        )
    except OptInDisabled as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not works:
        print("[kakuyomu] no works collected (empty ranking?).")
        return 1

    for meta in works:
        _write_work(corpus_root, meta)
    _write_manifest(
        corpus_root, works, args.genre, args.period, args.variation
    )
    print(f"[kakuyomu] wrote {len(works)} work(s) to {corpus_root}")

    if args.apply_style:
        from src.services.style_learning import learn_from_corpus
        out = learn_from_corpus(
            corpus_dir=corpus_root,
            book_id=args.book_id,
            branch_id=args.branch_id,
        )
        if out is None:
            print(
                "[kakuyomu] learn_from_corpus() was a no-op "
                "(opt-in off or empty corpus).",
                file=sys.stderr,
            )
            return 3
        print(f"[kakuyomu] updated style profile at {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
