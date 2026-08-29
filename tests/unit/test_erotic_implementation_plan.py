"""Plan implementation tests: encoding integrity, consent detection, flag normalization.

These tests guard the improvements made to the NSFW / 官能 agent:
  * No U+FFFD replacement characters remain in the repaired source files.
  * EroticIntegrityChecker.check_mutual_consent requires two distinct utterances.
  * resolve_erotic_config normalizes enable_erotic / nsfw_enabled / erotic_enabled.
"""

from __future__ import annotations

import pathlib

from src.agents.erotic_enhancer import resolve_erotic_config
from src.agents.erotic.filter import EroticIntegrityChecker

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
REPAIRED_FILES = [
    REPO_ROOT / "src" / "agents" / "erotic" / "evaluator.py",
    REPO_ROOT / "src" / "agents" / "erotic" / "vocabulary.py",
    REPO_ROOT / "src" / "agents" / "erotic" / "filter.py",
]


def test_no_replacement_characters_in_repaired_files():
    for f in REPAIRED_FILES:
        text = f.read_text(encoding="utf-8")
        assert "\ufffd" not in text, f"{f.name} still contains corrupted characters"


def test_mutual_consent_requires_two_utterances():
    checker = EroticIntegrityChecker(db_path=":memory:")

    # 片方のみの同意 → 不合格
    ok, issues = checker.check_mutual_consent("彼女は『いいよ』と頷いた。")
    assert ok is False
    assert any("片方" in i for i in issues)

    # 両者からの同意 → 合格
    ok, issues = checker.check_mutual_consent(
        "『いいよ』と彼女は頷いた。「私も欲しい」と彼は答えた。"
    )
    assert ok is True
    assert issues == []


def test_mutual_consent_no_consent_is_rejected():
    checker = EroticIntegrityChecker(db_path=":memory:")
    ok, issues = checker.check_mutual_consent("二人は静かに見つめ合っていた。")
    assert ok is False
    assert any("検出されません" in i for i in issues)


def test_resolve_erotic_config_normalizes_flags():
    # 古い表記 enable_erotic
    intensity, enabled = resolve_erotic_config({"enable_erotic": True, "erotic_intensity": 3})
    assert enabled is True and intensity == 3

    # nsfw_enabled
    intensity, enabled = resolve_erotic_config({"nsfw_enabled": True})
    assert enabled is True

    # 新表記 erotic_enabled
    intensity, enabled = resolve_erotic_config({"erotic_enabled": True, "erotic_intensity": 4})
    assert enabled is True and intensity == 4

    # intensity のみでも有効
    intensity, enabled = resolve_erotic_config({"erotic_intensity": 2})
    assert enabled is True and intensity == 2

    # すべて無効
    intensity, enabled = resolve_erotic_config({})
    assert enabled is False and intensity == 0
