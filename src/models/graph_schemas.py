"""GraphRAG 用 Pydantic スキーマ定義."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Entity(BaseModel):
    """物語から抽出された単一エンティティ (ノード)."""

    name: str = Field(..., description="エンティティの名前 (例: アルス, 聖剣エクスカリバー, 王都ルミナス)")
    type: Literal["Character", "Location", "Item", "Event", "Faction", "Concept"] = Field(
        ..., description="エンティティの種別"
    )
    description: str = Field("", description="この章における簡潔な説明や状態 (例: 負傷中, 宝物庫に保管)")
    properties: dict[str, Any] = Field(default_factory=dict, description="追加の属性情報 (例: is_alive, faction)")


class Relationship(BaseModel):
    """エンティティ間の関係性 (エッジ)."""

    source: str = Field(..., description="関係の起点となるエンティティ名")
    target: str = Field(..., description="関係の対象となるエンティティ名")
    type: str = Field(..., description="関係種別 (例: KNOWS, HATES, ALLY_OF, LOCATED_IN, POSSESSES, ATTACKED)")
    detail: str = Field("", description="関係の詳細・理由 (例: 幼馴染, 以前決闘で敗れた)")


class GraphExtractionResult(BaseModel):
    """LLM による章テキストからのナレッジグラフ抽出結果."""

    entities: list[Entity] = Field(default_factory=list, description="抽出されたエンティティ一覧")
    relationships: list[Relationship] = Field(default_factory=list, description="抽出された関係性一覧")
    plot_summary: str = Field("", description="この章の1行ダイジェスト要約")
