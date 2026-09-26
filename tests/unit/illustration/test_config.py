"""統合イラスト生成エンジンの設定テスト（Step 19）。"""

from __future__ import annotations


import pytest

from config.image_models import (
    DEFAULT_IMAGE_MODEL,
    ENV_MODEL_KEY,
    IMAGE_MODEL_CATALOG,
    estimate_cost_usd,
    get_image_model_id,
    get_image_model_spec,
    normalize_model_key,
    resolve_model_key_from_env,
)
from src.models.illustration import IllustrationType
from src.services.illustration.config import (
    ENV_LEGACY,
    ENV_MOCK,
    UnifiedIllustrationConfig,
)


def test_catalog_has_nanobanana2lite_as_default():
    """【仕様】既定モデルキーは NanoBanana2Lite である。

    これを崩すと全イラストの生成モデル・コスト・品質が変わる。
    """
    assert DEFAULT_IMAGE_MODEL == "nanobanana2lite"
    assert IMAGE_MODEL_CATALOG[DEFAULT_IMAGE_MODEL].model_id == "gemini-3.1-flash-lite-image"


def test_imagen_models_remain_registered_for_swap():
    """【仕様】Imagen 3 tier は切替候補としてカタログに残っている。

    消すとモデル差し替え（運用）の手段が消える。
    """
    for key in ("imagen_fast", "imagen_quality", "imagen_ultra"):
        assert key in IMAGE_MODEL_CATALOG
        assert get_image_model_spec(key).client == "legacy_imagen"


def test_env_model_key_override(monkeypatch):
    """環境変数でモデルを切り替えられる（差し替え容易性の担保）。"""
    monkeypatch.setenv(ENV_MODEL_KEY, "imagen_ultra")
    assert resolve_model_key_from_env() == "imagen_ultra"
    assert get_image_model_id(resolve_model_key_from_env()) == "imagen-4.0-ultra-generate-001"


def test_unknown_env_model_falls_back_to_default(monkeypatch):
    """未知のモデル指定でも既定へ安全に倒す（起動を壊さない）。"""
    monkeypatch.setenv(ENV_MODEL_KEY, "does-not-exist")
    assert resolve_model_key_from_env() == DEFAULT_IMAGE_MODEL


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("auto", "nanobanana2lite"),
        ("fast", "imagen_fast"),
        ("ultra", "imagen_ultra"),
        ("imagen-4.0-generate-001", "imagen_quality"),
        ("gemini-3.1-flash-lite-image", "nanobanana2lite"),
        (None, "nanobanana2lite"),
    ],
)
def test_legacy_alias_normalization(raw, expected):
    """旧 tier 名 / モデルID をカタログキーへ正規化できる。"""
    assert normalize_model_key(raw) == expected


def test_config_reads_mock_and_legacy_env(monkeypatch, tmp_path):
    """mock / ロールバックフラグを環境変数から読む。"""
    monkeypatch.setenv(ENV_MOCK, "1")
    monkeypatch.setenv(ENV_LEGACY, "1")
    config = UnifiedIllustrationConfig(output_root=tmp_path)
    assert config.mock_mode is True
    assert config.use_legacy_client is True


def test_config_env_model_overrides_default(monkeypatch, tmp_path):
    monkeypatch.setenv(ENV_MODEL_KEY, "imagen_quality")
    config = UnifiedIllustrationConfig(output_root=tmp_path)
    assert config.model_key == "imagen_quality"
    assert config.model_id == "imagen-4.0-generate-001"


def test_aspect_ratio_by_type():
    """種別ごとの既定アスペクト比（表紙/24コマは縦長）。"""
    config = UnifiedIllustrationConfig()
    assert config.aspect_ratio_for(IllustrationType.COVER) == "2:3"
    assert config.aspect_ratio_for(IllustrationType.MANGA_24PANEL) == "2:3"
    assert config.aspect_ratio_for(IllustrationType.EPISODE) == "3:4"
    assert config.aspect_ratio_for("unknown-type") == config.default_aspect_ratio


def test_cost_uses_catalog_not_hardcoded():
    """コストはカタログの単価から算出される（ハードコード禁止）。"""
    assert estimate_cost_usd("nanobanana2lite", 1) == pytest.approx(0.034)
    assert estimate_cost_usd("nanobanana2lite", 40) == pytest.approx(1.36)
    assert estimate_cost_usd("imagen_ultra", 1) == pytest.approx(0.20)


def test_thresholds_for_multi_panel():
    """複数コマ種別は multi_panel バケットの閾値を使う。"""
    config = UnifiedIllustrationConfig()
    single = config.thresholds_for(IllustrationType.EPISODE)
    multi = config.thresholds_for(IllustrationType.MANGA_24PANEL, multi_panel=True)
    assert single["min_resolution"] == 256
    assert multi["min_resolution"] == 512
