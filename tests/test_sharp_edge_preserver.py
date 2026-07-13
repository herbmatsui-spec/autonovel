"""
tests/test_sharp_edge_preserver.py
src/backend/sharp_edge_preserver.py の単体テスト。
"""
import pytest

from src.backend.sharp_edge_preserver import check_edges_preserved
from src.models.sharp_edge import SharpEdgeSpec


class TestCheckEdgesPreserved:
    def test_no_edges_returns_empty(self):
        result = check_edges_preserved("before", "after", [])
        assert result == []

    def test_all_edges_preserved_returns_empty(self):
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方"),
            SharpEdgeSpec(edge_type="protagonist_flaw", description="優柔不断な点"),
        ]
        after = "before after 余韻のある終わり方 優柔不断な点"
        result = check_edges_preserved("before", after, edges)
        assert result == []

    def test_single_edge_removed_returns_it(self):
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方"),
        ]
        after = "before after 優柔不断な点"
        result = check_edges_preserved("before", after, edges)
        assert len(result) == 1
        assert result[0].edge_type == "ending_pullback"

    def test_case_insensitive(self):
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方"),
        ]
        after = "BEFORE AFTER 余韻のある終わり方"
        result = check_edges_preserved("before", after, edges)
        assert result == []

    def test_whitespace_normalization(self):
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="  余韻のある終わり方  "),
        ]
        after = "before after 余韻のある終わり方"
        result = check_edges_preserved("before", after, edges)
        assert result == []


class TestCheckEdgesPreservedWithKeyPhrase:
    """key_phrase フィールドを使用したテスト"""

    def test_key_phrase_preserved(self):
        """key_phrase が after_content に含まれる場合は保持されたと判定"""
        edges = [
            SharpEdgeSpec(edge_type="protagonist_flaw", description="長い説明文", key_phrase="深淵で得た力")
        ]
        after = "深淵で得た力 が彼を新たな存在として蘇らせた。"
        result = check_edges_preserved("before", after, edges)
        assert result == []  # 保持された

    def test_key_phrase_removed(self):
        """key_phrase が after_content に含まれない場合は削除されたと判定"""
        edges = [
            SharpEdgeSpec(edge_type="protagonist_flaw", description="長い説明文", key_phrase="深淵で得た力")
        ]
        after = "彼は新たな力を得た。"  # key_phrase なし
        result = check_edges_preserved("before", after, edges)
        assert len(result) == 1
        assert result[0].edge_type == "protagonist_flaw"

    def test_key_phrase_falls_back_to_description(self):
        """key_phrase が空の場合、description[:20] にフォールバック"""
        edges = [
            SharpEdgeSpec(edge_type="abnormal_dialogue", description="『退屈だね』", key_phrase="")
        ]
        after = "before after 『退屈だね』 异常なセリフ"
        result = check_edges_preserved("before", after, edges)
        assert result == []  # description[:20] = "『退屈だね』" で一致

    def test_key_phrase_priority_over_description(self):
        """key_phrase がある場合、description[:20] の一致は無視される"""
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="結末は唐突に終わった", key_phrase="突然の幕切れ")
        ]
        after = "突然の幕切れで物語が終わった"
        # key_phrase = "突然の幕切れ" は含まれる
        # description[:20] = "結末は唐突に終わった" は含まれない
        result = check_edges_preserved("before", after, edges)
        assert result == []  # key_phrase で一致

    def test_key_phrase_case_insensitive(self):
        """key_phrase の一致判定は大文字小文字を区別しない（ASCII）"""
        edges = [
            SharpEdgeSpec(edge_type="protagonist_flaw", description="説明", key_phrase="Deep Hidden Power")
        ]
        after = "THE DEEP HIDDEN POWER GRANTED HIM NEW LIFE"
        result = check_edges_preserved("before", after, edges)
        # 大文字小文字は区別しないので保持される
        assert result == []

    def test_key_phrase_with_whitespace(self):
        """key_phrase はtrimされてから一致判定される"""
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="説明", key_phrase=" 余韻のある終わり方 ")
        ]
        after = "before after 余韻のある終わり方"
        result = check_edges_preserved("before", after, edges)
        assert result == []  # トリムされて一致


class TestNgramSimilarity:
    """N-gram 類似度フォールバックの単体テスト (plan Step 37-38)"""

    def test_identical_text_returns_one(self):
        from src.backend.engine_utils import compute_ngram_similarity
        assert compute_ngram_similarity("深淵で得た力", "深淵で得た力") == 1.0

    def test_empty_input_returns_zero(self):
        from src.backend.engine_utils import compute_ngram_similarity
        assert compute_ngram_similarity("", "何か") == 0.0
        assert compute_ngram_similarity("何か", "") == 0.0

    def test_unrelated_text_low_score(self):
        from src.backend.engine_utils import compute_ngram_similarity
        score = compute_ngram_similarity("りんごが好き", "電車は速い")
        assert 0.0 <= score <= 0.2

    def test_partial_overlap_mid_score(self):
        from src.backend.engine_utils import compute_ngram_similarity
        score = compute_ngram_similarity("深淵で得た力が彼を蘇らせた", "深淵で得た力が新たな存在に")
        assert 0.3 <= score <= 1.0


class TestSemanticEdgePreserver:
    """SemanticEdgePreserver の動作テスト (plan Step 26-27, 39-40)"""

    @pytest.mark.asyncio
    async def test_string_only_mode_returns_lost_list(self):
        from src.backend.sharp_edge_preserver import SemanticEdgePreserver
        preserver = SemanticEdgePreserver(semantic_cache=None, use_semantic=False)
        edges = [
            SharpEdgeSpec(edge_type="protagonist_flaw", description="説明", key_phrase="深淵で得た力")
        ]
        after = "深淵で得た力 が彼を新たな存在として蘇らせた。"
        semantic_lost, string_lost = await preserver.check_edges_preserved("before", after, edges)
        # 保持されているので両方空
        assert semantic_lost == []
        assert string_lost == []

    @pytest.mark.asyncio
    async def test_use_semantic_no_cache_falls_back_to_ngram(self):
        from src.backend.sharp_edge_preserver import SemanticEdgePreserver

        # semantic_cache なしだが use_ngram_fallback=True の場合
        preserver = SemanticEdgePreserver(semantic_cache=None, use_semantic=True, use_ngram_fallback=True)
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="説明", key_phrase="余韻のある終わり方")
        ]
        # key_phrase を含む本文 → N-gram 類似度が高く、保持と判定
        after = "この物語は余韻のある終わり方で読者の心に残る。"
        semantic_lost, string_lost = await preserver.check_edges_preserved("before", after, edges)
        assert semantic_lost == []
        # string_lost には入る（字面一致しないが key_phrase は含まれるので実際は空）
        assert string_lost == []

    @pytest.mark.asyncio
    async def test_semantic_recovery_via_mock(self):
        from src.backend.sharp_edge_preserver import SemanticEdgePreserver

        class FakeCache:
            async def compute_similarity(self, text1, text2):
                # 字面は一致しないが、意味的には保持されていると判定
                return 0.9

        preserver = SemanticEdgePreserver(semantic_cache=FakeCache(), use_semantic=True, similarity_threshold=0.75)
        edges = [
            SharpEdgeSpec(edge_type="protagonist_flaw", description="説明", key_phrase="深淵で得た力")
        ]
        # 本文には key_phrase を含まない（字面不一致）が意味的には保持
        after = "彼は深海から得た力によって再生した。"
        semantic_lost, string_lost = await preserver.check_edges_preserved("before", after, edges)
        # semantic で保持と判定されるので semantic_lost は空
        assert semantic_lost == []
        # 字面では失われているので string_lost には含まれる
        assert len(string_lost) == 1

    @pytest.mark.asyncio
    async def test_semantic_detects_real_loss_via_mock(self):
        from src.backend.sharp_edge_preserver import SemanticEdgePreserver

        class FakeCache:
            async def compute_similarity(self, text1, text2):
                # 意味的にも失われている
                return 0.1

        preserver = SemanticEdgePreserver(semantic_cache=FakeCache(), use_semantic=True, similarity_threshold=0.75)
        edges = [
            SharpEdgeSpec(edge_type="protagonist_flaw", description="説明", key_phrase="深淵で得た力")
        ]
        after = "彼は平凡な毎日を送っていた。"
        semantic_lost, string_lost = await preserver.check_edges_preserved("before", after, edges)
        # 両方で失われたと判定
        assert len(semantic_lost) == 1
        assert len(string_lost) == 1

