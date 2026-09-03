"""GraphRAG 関連 Pydantic スキーマの契約テスト.

スキーマの破壊的変更を検知するためのテスト。
"""
import pytest
from pydantic import ValidationError

from src.models.graph_schemas import GraphExtractionResult, Entity, Relationship


def test_graph_extraction_result_schema():
    """GraphExtractionResult のスキーマが破壊的変更されないことを確認"""
    result = GraphExtractionResult(
        entities=[
            Entity(name="テスト", type="Character", description="説明", properties={})
        ],
        relationships=[
            Relationship(source="A", target="B", type="KNOWS", detail="詳細")
        ],
        plot_summary="要約"
    )

    # 必須フィールド存在確認
    assert hasattr(result, "entities")
    assert hasattr(result, "relationships")
    assert hasattr(result, "plot_summary")

    # JSON シリアライズ可能
    json_str = result.model_dump_json()
    assert "テスト" in json_str
    assert "KNOWS" in json_str


def test_entity_type_literal():
    """Entity.type が許可された Literal のみ受け付ける"""
    valid_types = ["Character", "Location", "Item", "Event", "Faction", "Concept"]

    for valid_type in valid_types:
        entity = Entity(name="テスト", type=valid_type, description="", properties={})
        assert entity.type == valid_type

    # 無効なタイプは拒否される
    with pytest.raises(ValidationError):
        Entity(name="テスト", type="InvalidType", description="", properties={})


def test_entity_properties_default_factory():
    """Entity.properties がデフォルトで空 dict になる"""
    entity = Entity(name="テスト", type="Character", description="")
    assert entity.properties == {}
    assert isinstance(entity.properties, dict)


def test_relationship_fields():
    """Relationship の全フィールドが正しく設定される"""
    rel = Relationship(
        source="アルス",
        target="聖剣",
        type="POSSESSES",
        detail="所持している"
    )
    assert rel.source == "アルス"
    assert rel.target == "聖剣"
    assert rel.type == "POSSESSES"
    assert rel.detail == "所持している"


def test_graph_extraction_result_response_format():
    """GraphExtractionResult.get_response_format() が正しい JSON Schema を返す"""
    fmt = GraphExtractionResult.get_response_format()

    assert fmt["type"] == "json_schema"
    assert "json_schema" in fmt
    assert fmt["json_schema"]["name"] == "graph_extraction_result"
    assert fmt["json_schema"]["strict"] is True
    assert "schema" in fmt["json_schema"]


def test_entity_immutability_after_creation():
    """Entity 作成後のフィールドが変更可能（Pydantic v2 デフォルト）"""
    entity = Entity(name="テスト", type="Character", description="")
    entity.description = "変更後"
    assert entity.description == "変更後"


def test_relationship_optional_detail():
    """Relationship.detail が省略可能（デフォルト空文字）"""
    rel = Relationship(source="A", target="B", type="KNOWS")
    assert rel.detail == ""