"""GraphRAG 検索・Reranking サービスの単体テスト."""
from unittest.mock import MagicMock, patch

from src.services.rag_service import GraphRAGService


def test_rerank_graph_neighbors():
    """Reranking: ユーザープロンプトに最も意味的に近いグラフノードが上位に再評価される."""
    service = GraphRAGService()
    neighbors = [
        {"name": "宿屋の主人", "relation_type": "KNOWS", "properties": {"description": "平凡な宿屋"}},
        {"name": "魔王軍幹部", "relation_type": "ENEMY_OF", "properties": {"description": "闇の魔法の使い手"}},
        {"name": "聖剣の鞘", "relation_type": "ITEM", "properties": {"description": "光の加護を持つ"}},
    ]

    with patch("src.services.rag_service.embedding_service") as mock_emb:
        # プロンプト「魔王軍との戦い」に対して、魔王軍幹部が一番類似度高くなるようにベクトルをモック
        def fake_embedding(text: str):
            if "魔王" in text:
                return [1.0, 0.0, 0.0]
            elif "聖剣" in text:
                return [0.0, 1.0, 0.0]
            else:
                return [0.0, 0.0, 1.0]

        mock_emb.get_embedding.side_effect = fake_embedding

        ranked = service.rerank_graph_neighbors(
            neighbors=neighbors,
            current_prompt="魔王軍の幹部と戦闘を開始するシーン",
            top_k=2,
        )

        assert len(ranked) == 2
        # 最上位が「魔王軍幹部」になっていること
        assert ranked[0]["name"] == "魔王軍幹部"


def test_cosine_similarity():
    """コサイン類似度の計算精度テスト."""
    service = GraphRAGService()
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]

    assert abs(service._cosine_similarity(vec_a, vec_b) - 1.0) < 1e-5
    assert abs(service._cosine_similarity(vec_a, vec_c) - 0.0) < 1e-5
    assert service._cosine_similarity([], []) == 0.0
