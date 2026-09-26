"""GiNZA/NLP pipeline initialization (singleton)."""
from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spacy.language import Language

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def get_nlp(model_name: str = "ja_ginza") -> Language:
    """NLPパイプラインを取得（シングルトン・キャッシュ付き）

    Args:
        model_name: 使用するspaCyモデル名 ("ja_ginza" または "ja_core_news_lg")

    Returns:
        読み込み済みのspaCy Languageオブジェクト

    Raises:
        OSError: モデルが見つからない場合
    """
    import spacy

    try:
        nlp = spacy.load(model_name)
        logger.info(f"Loaded NLP model: {model_name}")
        return nlp
    except OSError as e:
        logger.error(f"Failed to load model '{model_name}': {e}")
        logger.error("Please install the model: pip install ja-ginza")
        raise


def init_nlp(model_name: str = "ja_ginza") -> Language:
    """明示的な初期化（キャッシュクリア後に呼び出し可能）"""
    get_nlp.cache_clear()
    return get_nlp(model_name)


def get_nlp_for_testing() -> Language:
    """テスト用の軽量NLPパイプライン（モデル未インストール時のフォールバック）"""
    import spacy

    # 空白トークナイザーのみの最小パイプライン
    nlp = spacy.blank("ja")
    # 依存構造解析などが必要な場合はモデル必須
    return nlp


__all__ = ["get_nlp", "init_nlp", "get_nlp_for_testing"]
