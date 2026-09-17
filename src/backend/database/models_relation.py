"""CharacterRelationModel - キャラクター関係リレーショナルモデル。

Apache AGE のグラフDB Edge を置換する、
単純な (source_char_id, target_char_id, relation_type) テーブル。
"""
from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text

from src.infrastructure.database.models.base_orm import Base


class CharacterRelationModel(Base):
    """キャラクター間の関係性を格納するリレーショナルモデル。

    グラフDBの Edge を (source, target, type) の行で表現する。
    双方向関係は2行（A→B, B→A）で明示的に表す。

    Attributes:
        id: リレーションの一意識別子
        book_id: 所属作品ID
        source_char_id: 関係元キャラクターID
        target_char_id: 関係先キャラクターID
        relation_type: 関係の種類（例: 宿敵, 師弟, 信頼, 片思い）
        description: 関係の補足説明（任意）
    """

    __tablename__ = "character_relations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, nullable=False, index=True)
    source_char_id = Column(Integer, nullable=False)
    target_char_id = Column(Integer, nullable=False)
    relation_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CharacterRelation(id={self.id}, "
            f"source={self.source_char_id}→target={self.target_char_id}, "
            f"type='{self.relation_type}')>"
        )
