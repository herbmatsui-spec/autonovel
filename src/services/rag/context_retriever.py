from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class ForeshadowingStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


@dataclass
class ForeshadowingEntity:
    foreshadow_id: str
    description: str
    introduced_in_ep: int
    target_resolution_ep: Optional[int] = None
    status: ForeshadowingStatus = ForeshadowingStatus.OPEN
    related_characters: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        description: str,
        introduced_in_ep: int,
        target_resolution_ep: Optional[int] = None,
        related_characters: list[str] = None,
        keywords: list[str] = None,
        metadata: dict[str, Any] = None,
    ) -> "ForeshadowingEntity":
        return cls(
            foreshadow_id=str(uuid.uuid4())[:8],
            description=description,
            introduced_in_ep=introduced_in_ep,
            target_resolution_ep=target_resolution_ep,
            related_characters=related_characters or [],
            keywords=keywords or [],
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "foreshadow_id": self.foreshadow_id,
            "description": self.description,
            "introduced_in_ep": self.introduced_in_ep,
            "target_resolution_ep": self.target_resolution_ep,
            "status": self.status.value,
            "related_characters": self.related_characters,
            "keywords": self.keywords,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForeshadowingEntity":
        return cls(
            foreshadow_id=data["foreshadow_id"],
            description=data["description"],
            introduced_in_ep=data["introduced_in_ep"],
            target_resolution_ep=data.get("target_resolution_ep"),
            status=ForeshadowingStatus(data.get("status", "open")),
            related_characters=data.get("related_characters", []),
            keywords=data.get("keywords", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SettingEntity:
    setting_id: str
    name: str
    description: str
    category: str
    related_episodes: list[int] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CharacterState:
    character_id: str
    name: str
    current_episode: int
    emotional_state: str
    relationships: dict[str, str] = field(default_factory=dict)
    knowledge: list[str] = field(default_factory=list)
    inventory: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class LongFormContextRetriever:
    """統合リトリーバー: ChromaDBベクトル検索 + NetworkX知識グラフ探索"""

    def __init__(
        self,
        chroma_client: Any = None,
        graph_store: Any = None,
        embedding_function: Any = None,
    ):
        self.chroma_client = chroma_client
        self.graph_store = graph_store
        self.embedding_function = embedding_function
        self._collections: dict[int, Any] = {}

    def _get_or_create_collection(self, book_id: int) -> Any:
        """ChromaDBコレクションを取得または作成"""
        if book_id in self._collections:
            return self._collections[book_id]

        if self.chroma_client is None:
            # モック/テスト用のインメモリ実装
            from src.services.vector_store.in_memory import InMemoryVectorStore
            self.chroma_client = InMemoryVectorStore()

        collection_name = f"novel_foreshadowings_book_{book_id}"
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except Exception:
            collection = self.chroma_client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"book_id": book_id, "type": "foreshadowing"},
            )
        self._collections[book_id] = collection
        return collection

    def upsert_foreshadowing(self, book_id: int, entity: ForeshadowingEntity) -> None:
        """伏線エンティティをベクトルDBに保存・更新"""
        collection = self._get_or_create_collection(book_id)
        
        # 埋め込み用テキストを構築
        embedding_text = f"{entity.description} {' '.join(entity.keywords)} {' '.join(entity.related_characters)}"
        
        collection.upsert(
            ids=[entity.foreshadow_id],
            documents=[embedding_text],
            metadatas=[entity.to_dict()],
        )

    def get_pending_foreshadowings(self, book_id: int, current_ep: int) -> list[ForeshadowingEntity]:
        """未回収かつ回収目標が近い伏線を優先抽出"""
        collection = self._get_or_create_collection(book_id)
        
        # 全件取得してフィルタリング（本番ではwhere句で効率化）
        results = collection.get()
        
        entities = []
        for metadata in results.get("metadatas", []):
            entity = ForeshadowingEntity.from_dict(metadata)
            if entity.status == ForeshadowingStatus.OPEN:
                # 回収目標が現在エピソード以降、または目標未設定
                if entity.target_resolution_ep is None or entity.target_resolution_ep >= current_ep:
                    entities.append(entity)
        
        # 回収目標が近い順でソート
        entities.sort(key=lambda e: e.target_resolution_ep or float('inf'))
        return entities

    def search_relevant_context(
        self,
        book_id: int,
        plot_summary: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """プロット概要と意味的類似度が高い伏線をベクトル検索"""
        collection = self._get_or_create_collection(book_id)
        
        results = collection.query(
            query_texts=[plot_summary],
            n_results=top_k,
            where={"status": {"$ne": "resolved"}},
        )
        
        relevant = []
        for i, metadata in enumerate(results.get("metadatas", [[]])[0]):
            distance = results.get("distances", [[]])[0][i] if results.get("distances") else 0
            relevant.append({
                "entity": ForeshadowingEntity.from_dict(metadata),
                "similarity": 1.0 - distance,
                "metadata": metadata,
            })
        
        return relevant

    def extract_subgraph(self, character_names: list[str]) -> list[dict[str, Any]]:
        """知識グラフからキャラクター関連のサブグラフを抽出"""
        if self.graph_store is None:
            return []
        
        return self.graph_store.extract_character_subgraph(character_names)

    def retrieve_writing_context(
        self,
        book_id: int,
        current_ep: int,
        plot_outline: str,
        character_names: list[str] = None,
    ) -> dict[str, Any]:
        """執筆に必要な背景知識をワンストップで提供"""
        character_names = character_names or []
        
        # 1. 未回収伏線の取得
        pending_foreshadowings = self.get_pending_foreshadowings(book_id, current_ep)
        
        # 2. プロット類似度ベースの関連伏線検索
        relevant_foreshadowings = self.search_relevant_context(book_id, plot_outline)
        
        # 3. 知識グラフから関連サブグラフ抽出
        subgraph = self.extract_subgraph(character_names) if character_names else []
        
        # 4. キャラクター状態取得（将来拡張用）
        character_states = self._get_character_states(book_id, current_ep, character_names)
        
        return {
            "pending_foreshadowings": pending_foreshadowings,
            "relevant_foreshadowings": [r["entity"] for r in relevant_foreshadowings],
            "subgraph_edges": subgraph,
            "character_states": character_states,
            "current_episode": current_ep,
        }

    def _get_character_states(
        self,
        book_id: int,
        current_ep: int,
        character_names: list[str],
    ) -> list[CharacterState]:
        """キャラクター状態を取得（プレースホルダー）"""
        return [
            CharacterState(
                character_id=name,
                name=name,
                current_episode=current_ep,
                emotional_state="neutral",
            )
            for name in character_names
        ]

    def format_context_for_prompt(self, context_dict: dict[str, Any]) -> str:
        """取得した知識をプロンプト用Markdownに整形"""
        lines = ["## 本話で意識・回収すべき伏線・設定"]
        
        # 未回収伏線
        pending = context_dict.get("pending_foreshadowings", [])
        if pending:
            lines.append("### 回収必須の伏線")
            for fs in pending:
                target = fs.target_resolution_ep or "未定"
                lines.append(
                    f"- **{fs.foreshadow_id}** (第{fs.introduced_in_ep}話提示 → 第{target}話回収予定): "
                    f"{fs.description} [キャラ: {', '.join(fs.related_characters) or 'なし'}]"
                )
        
        # 関連伏線
        relevant = context_dict.get("relevant_foreshadowings", [])
        if relevant:
            lines.append("### 今回のプロットに関連する伏線・設定")
            for fs in relevant:
                lines.append(f"- {fs.description} [キーワード: {', '.join(fs.keywords)}]")
        
        # サブグラフ
        subgraph = context_dict.get("subgraph_edges", [])
        if subgraph:
            lines.append("### キャラクター関係性・因縁")
            for edge in subgraph:
                lines.append(f"- {edge.get('source', '')} --{edge.get('relation', '')}--> {edge.get('target', '')}")
        
        # キャラクター状態
        states = context_dict.get("character_states", [])
        if states:
            lines.append("### キャラクター状態")
            for st in states:
                lines.append(f"- {st.name}: 感情={st.emotional_state}, 知識={', '.join(st.knowledge) or 'なし'}")
        
        if not any([pending, relevant, subgraph, states]):
            lines.append("(参照すべき背景情報はありません)")
        
        return "\n".join(lines)

    def resolve_foreshadowing(
        self,
        book_id: int,
        foreshadow_id: str,
        resolved_ep: int,
    ) -> bool:
        """伏線回収ステータスを更新"""
        collection = self._get_or_create_collection(book_id)
        
        # 既存データ取得
        results = collection.get(ids=[foreshadow_id])
        if not results.get("metadatas"):
            return False
        
        metadata = results["metadatas"][0]
        metadata["status"] = ForeshadowingStatus.RESOLVED.value
        metadata["updated_at"] = datetime.now().isoformat()
        metadata["target_resolution_ep"] = resolved_ep
        
        collection.update(
            ids=[foreshadow_id],
            metadatas=[metadata],
        )
        return True