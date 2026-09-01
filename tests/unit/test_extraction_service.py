"""ナレッジグラフ抽出・名寄せサービスの単体テスト."""
from unittest.mock import MagicMock

from src.models.graph_schemas import Entity, GraphExtractionResult, Relationship
from src.services.extraction_service import ExtractionService


def test_graph_extraction_result_response_format():
    """get_response_format が正しい strict json_schema 形式を返すことを確認."""
    fmt = GraphExtractionResult.get_response_format()
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "graph_extraction_result"
    assert fmt["json_schema"]["strict"] is True
    assert "properties" in fmt["json_schema"]["schema"]


def test_extract_graph_from_text_success():
    """正常系: LLMが正しいJSONを返した際にGraphExtractionResultが正しく構築される."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = """
    {
        "entities": [
            {"name": "アルス", "type": "Character", "description": "勇者", "properties": {"is_alive": true}}
        ],
        "relationships": [
            {"source": "アルス", "target": "エクスカリバー", "type": "POSSESSES", "detail": "伝説の剣を所持"}
        ],
        "plot_summary": "アルスが伝説の剣を手に入れた。"
    }
    """
    service = ExtractionService(llm_adapter=mock_llm)
    result = service.extract_graph_from_text("アルスはエクスカリバーを引き抜いた。")

    assert len(result.entities) == 1
    assert result.entities[0].name == "アルス"
    assert len(result.relationships) == 1
    assert result.relationships[0].type == "POSSESSES"
    assert result.plot_summary == "アルスが伝説の剣を手に入れた。"


def test_extract_graph_self_correction_on_bad_json():
    """異常系: 初回に壊れたJSONが返った場合、自己修正プロンプトで再試行して成功する."""
    mock_llm = MagicMock()
    # 1回目はパースエラー、2回目で正常JSON
    mock_llm.generate.side_effect = [
        "This is not a JSON { broken",
        """
        {
            "entities": [{"name": "ルミナス", "type": "Location", "description": "聖なる都", "properties": {}}],
            "relationships": [],
            "plot_summary": "一行は都を目指す。"
        }
        """,
    ]
    service = ExtractionService(llm_adapter=mock_llm)
    result = service.extract_graph_from_text("ルミナスに向かって歩いた。")

    assert len(result.entities) == 1
    assert result.entities[0].name == "ルミナス"
    assert mock_llm.generate.call_count == 2


def test_resolve_entities():
    """名寄せ: 類似エンティティ名が既存の名称にマージされることを確認."""
    service = ExtractionService()
    extracted = GraphExtractionResult(
        entities=[
            Entity(name="勇者アルス", type="Character", description="強大な勇者", properties={}),
            Entity(name="魔王城", type="Location", description="最終ダンジョン", properties={}),
        ],
        relationships=[
            Relationship(source="勇者アルス", target="魔王城", type="ATTACKED", detail="進軍した"),
        ],
        plot_summary="アルスが魔王城へ向かった。",
    )
    existing_names = ["アルス", "王都ルミナス"]

    resolved = service.resolve_entities(extracted, existing_names)

    # "勇者アルス" が "アルス" に名寄せされていること
    entity_names = [e.name for e in resolved.entities]
    assert "アルス" in entity_names
    assert "勇者アルス" not in entity_names
    # リレーションの source も "アルス" に更新されていること
    assert resolved.relationships[0].source == "アルス"
