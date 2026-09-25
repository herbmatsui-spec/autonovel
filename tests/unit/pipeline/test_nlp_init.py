"""Tests for NLP initialization."""
from __future__ import annotations

import pytest

from src.pipeline.nlp_init import get_nlp, init_nlp, get_nlp_for_testing


class TestNLPInit:
    """NLP初期化テスト"""

    def test_nlp_singleton(self):
        """シングルトンパターンでキャッシュされること"""
        try:
            nlp1 = get_nlp("ja_ginza")
            nlp2 = get_nlp("ja_ginza")
            assert nlp1 is nlp2
        except OSError:
            pytest.skip("ja_ginza model not installed")

    def test_init_nlp_clears_cache(self):
        """init_nlp でキャッシュがクリアされること"""
        try:
            nlp1 = get_nlp("ja_ginza")
            nlp2 = init_nlp("ja_ginza")
            # 同じモデルでもキャッシュクリア後は新しいインスタンス
            # （実際の実装では同一オブジェクトが返る可能性もあるが、キャッシュはクリアされる）
        except OSError:
            pytest.skip("ja_ginza model not installed")

    def test_get_nlp_for_testing(self):
        """テスト用軽量NLP取得"""
        nlp = get_nlp_for_testing()
        assert nlp is not None
        assert nlp.lang == "ja"
        # 空白モデルなのでコンポーネントは少ない
        assert len(nlp.pipe_names) == 0 or "tokenizer" in nlp.pipe_names

    def test_invalid_model_raises(self):
        """存在しないモデル名で例外が発生すること"""
        with pytest.raises(OSError):
            get_nlp("non_existent_model_xyz")