"""tests/services/test_learn_from_corpus.py

Tests for ``src.services.style_learning.learn_from_corpus``.

These tests use a temporary directory as the corpus root and a
fake ``get_settings`` that returns an enabled-flagged object. We
also stub :func:`src.filesystem_memory.paths.get_workspace_path` so
the test does not need a real workspace tree on disk.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def enabled_settings(monkeypatch):
    """Patch ConfigManager.get_config to return an opt-in object."""
    from config import settings as settings_mod

    class _S:
        kakuyomu_ingest_enabled = True
        kakuyomu_ingest_limit = 5
        kakuyomu_request_interval = 0.0
        kakuyomu_user_agent = "test"

    monkeypatch.setattr(settings_mod.ConfigManager, "get_config", lambda: _S())
    return _S()


@pytest.fixture
def disabled_settings(monkeypatch):
    from config import settings as settings_mod

    class _S:
        kakuyomu_ingest_enabled = False

    monkeypatch.setattr(settings_mod.ConfigManager, "get_config", lambda: _S())
    return _S()


@pytest.fixture
def fake_workspace(monkeypatch, tmp_path: Path):
    """Route get_workspace_path into tmp_path for the test."""
    from src.filesystem_memory import paths as paths_mod

    base = tmp_path / "workspaces" / "1" / "1"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        paths_mod, "get_workspace_path", lambda book_id, branch_id=1: base
    )
    return base


def _make_corpus(root: Path, works: list) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for wid, synopsis, titles, tags in works:
        wd = root / str(wid)
        wd.mkdir()
        (wd / "synopsis.txt").write_text(synopsis + "\n", encoding="utf-8")
        (wd / "episode_titles.txt").write_text(
            "\n".join(titles) + "\n", encoding="utf-8"
        )
        (wd / "tags.txt").write_text("\n".join(tags) + "\n", encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "ranking": "/rankings/all/weekly?work_variation=long",
                "count": len(works),
                "generated_at": "2026-01-01T00:00:00Z",
                "works": [str(w[0]) for w in works],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return root


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def test_disabled_settings_is_noop(
    disabled_settings, fake_workspace, tmp_path
):
    from src.services.style_learning import learn_from_corpus

    corpus = _make_corpus(
        tmp_path / "corpus",
        [("1", "あらすじ", ["第一話"], ["タグ"])],
    )
    out = learn_from_corpus(corpus, book_id=1, branch_id=1)
    assert out is None
    assert not (fake_workspace / "STYLE_LEARNED.md").exists()


def test_missing_corpus_is_noop(enabled_settings, fake_workspace, tmp_path):
    from src.services.style_learning import learn_from_corpus

    out = learn_from_corpus(tmp_path / "no-such-dir", book_id=1, branch_id=1)
    assert out is None
    assert not (fake_workspace / "STYLE_LEARNED.md").exists()


def test_empty_corpus_is_noop(enabled_settings, fake_workspace, tmp_path):
    from src.services.style_learning import learn_from_corpus

    empty = tmp_path / "empty"
    empty.mkdir()
    out = learn_from_corpus(empty, book_id=1, branch_id=1)
    assert out is None
    assert not (fake_workspace / "STYLE_LEARNED.md").exists()


def test_writes_external_corpus_section(
    enabled_settings, fake_workspace, tmp_path
):
    from src.services.style_learning import learn_from_corpus

    corpus = _make_corpus(
        tmp_path / "corpus",
        [
            (
                "1",
                "魔法学園の物語。主人公は召喚術を学ぶ。",
                ["第一章 出会い", "第二章 試練"],
                ["異世界", "魔法"],
            ),
            (
                "2",
                "都会で繰り広げられる恋愛と成長のドラマ。",
                ["プロローグ", "第一章"],
                ["現代", "恋愛"],
            ),
        ],
    )

    out = learn_from_corpus(corpus, book_id=1, branch_id=1)
    assert out is not None
    text = (fake_workspace / "STYLE_LEARNED.md").read_text(encoding="utf-8")
    assert "## 外部コーパス - 出典" in text
    assert "/rankings/all/weekly" in text
    assert "作品数=2" in text
    # The section aggregates text from all works, so we expect a mix.
    assert "## 外部コーパス - 頻出語（上位N）" in text
    assert "## 外部コーパス - 平均文長" in text
    assert "## 外部コーパス - 助詞傾向" in text


def test_appends_without_overwriting_local_sections(
    enabled_settings, fake_workspace, tmp_path
):
    from src.services.style_learning import learn_from_corpus

    # Simulate a prior local learning step having populated the file.
    style_path = fake_workspace / "STYLE_LEARNED.md"
    style_path.write_text(
        "## 頻出語（上位N）\n\nLOCAL_TOP_WORDS\n",
        encoding="utf-8",
    )

    corpus = _make_corpus(
        tmp_path / "corpus",
        [("9", "テスト", ["話"], ["タグ"])],
    )
    learn_from_corpus(corpus, book_id=1, branch_id=1)

    text = style_path.read_text(encoding="utf-8")
    assert "LOCAL_TOP_WORDS" in text
    assert "## 外部コーパス - 出典" in text
