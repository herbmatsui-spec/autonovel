"""RDBMSベース相関図APIの単体テスト (v5.0 Relational Memory)

GET /api/graph で book_id を指定し、PostgreSQL/SQLite 環境でも
実際の作品伏線・キャラデータから動的グラフが返却されることを検証する。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.backend.server import app
from src.backend.routers.graph import router
from src.backend import database
from src.domain.schemas.foreshadowing import GraphNodeSchema, GraphEdgeSchema, ForeshadowingGraphResponse


client = TestClient(app)


@pytest.fixture
def mock_async_session():
    """モック AsyncSession を作成"""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def override_async_db(mock_async_session):
    """非同期DB依存をオーバーライド"""
    app.dependency_overrides[database.get_async_db] = lambda: mock_async_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_foreshadowings():
    """モック伏線データを作成"""
    from src.backend.database.models_foreshadowing import ForeshadowingModel
    
    f1 = MagicMock(spec=ForeshadowingModel)
    f1.id = 1
    f1.title = "謎の剣"
    f1.description = "主人公が見つけた謎の剣"
    f1.planted_episode = 1
    f1.target_episode = 5
    f1.resolved_episode = None
    f1.status = "planted"
    
    f2 = MagicMock(spec=ForeshadowingModel)
    f2.id = 2
    f2.title = "消えた手紙"
    f2.description = "第3話で消えた重要な手紙"
    f2.planted_episode = 3
    f2.target_episode = 10
    f2.resolved_episode = 8
    f2.status = "resolved"
    
    return [f1, f2]


@pytest.fixture
def mock_characters():
    """モックキャラクターデータを作成"""
    from src.backend.database.models import Character as CharacterModel
    
    c1 = MagicMock(spec=CharacterModel)
    c1.id = 1
    c1.name = "アルス"
    c1.role = "主人公"
    c1.personality = "勇敢で正義感が強い"
    c1.ability = "古代魔導剣術"
    
    c2 = MagicMock(spec=CharacterModel)
    c2.id = 2
    c2.name = "セリア"
    c2.role = "ヒロイン"
    c2.personality = "聡明で優しい"
    c2.ability = "精霊魔法"
    
    return [c1, c2]


@pytest.fixture
def mock_character_relations():
    """モックキャラ関係データを作成"""
    from src.backend.database.models_relation import CharacterRelationModel
    
    r1 = MagicMock(spec=CharacterRelationModel)
    r1.source_char_id = 1
    r1.target_char_id = 2
    r1.relation_type = "信頼"
    r1.description = "幼馴染として深い信頼関係"
    
    return [r1]


class TestGraphRelationalAPI:
    """RDBMSベース相関図APIのテストスイート"""

    @pytest.mark.asyncio
    async def test_get_graph_data_with_valid_book_id(
        self, mock_async_session, override_async_db, mock_foreshadowings, mock_characters, mock_character_relations
    ):
        """有効な book_id でグラフデータが正しく返却されることを検証"""
        from sqlalchemy import select
        from src.backend.database.models import Character as CharacterModel
        from src.backend.database.models_relation import CharacterRelationModel
        from src.backend.database.models_foreshadowing import ForeshadowingModel
        
        # セッションの execute をモック
        async def mock_execute(query):
            result = MagicMock()
            # ForeshadowingModel のクエリ
            if "foreshadowings" in str(query).lower() or "ForeshadowingModel" in str(query):
                result.scalars.return_value.all.return_value = mock_foreshadowings
            # CharacterModel のクエリ
            elif "characters" in str(query).lower() or "CharacterModel" in str(query) or "Character" in str(query):
                result.scalars.return_value.all.return_value = mock_characters
            # CharacterRelationModel のクエリ
            elif "character_relations" in str(query).lower() or "CharacterRelationModel" in str(query):
                result.scalars.return_value.all.return_value = mock_character_relations
            else:
                result.scalars.return_value.all.return_value = []
            return result
        
        mock_async_session.execute.side_effect = mock_execute
        
        response = client.get("/api/graph?book_id=1")
        
        assert response.status_code == 200
        data = response.json()
        
        # レスポンス構造の検証
        assert "graph_name" in data
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
        
        # 伏線ノードが含まれることを確認
        foreshadowing_nodes = [n for n in data["nodes"] if n.get("label") == "Foreshadowing"]
        assert len(foreshadowing_nodes) >= 2  # 2つの伏線
        
        # キャラクターノードが含まれることを確認
        character_nodes = [n for n in data["nodes"] if n.get("label") == "Character"]
        assert len(character_nodes) >= 2  # 2人のキャラ
        
        # エピソードノードが含まれることを確認
        episode_nodes = [n for n in data["nodes"] if n.get("label") == "Episode"]
        assert len(episode_nodes) >= 3  # planted_episode 1, 3, resolved_episode 8, target_episode 5, 10
        
        # エッジの検証
        assert len(data["edges"]) > 0
        
        # PLANTED_IN エッジの存在確認
        planted_edges = [e for e in data["edges"] if e.get("type") == "PLANTED_IN"]
        assert len(planted_edges) >= 2
        
        # RESOLVED_BY エッジの存在確認
        resolved_edges = [e for e in data["edges"] if e.get("type") == "RESOLVED_BY"]
        assert len(resolved_edges) >= 1  # f2 は resolved_episode=8
        
        # キャラクター関係エッジの存在確認
        char_rel_edges = [e for e in data["edges"] if e.get("type") == "信頼"]
        assert len(char_rel_edges) >= 1

    @pytest.mark.asyncio
    async def test_get_graph_data_with_invalid_book_id(self, mock_async_session, override_async_db):
        """存在しない book_id で空のグラフが返却されることを検証"""
        from sqlalchemy import select
        
        async def mock_execute(query):
            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            return result
        
        mock_async_session.execute.side_effect = mock_execute
        
        response = client.get("/api/graph?book_id=9999")
        
        assert response.status_code == 200
        data = response.json()
        
        # 空のグラフが返却されること
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 0
        assert len(data["edges"]) == 0

    @pytest.mark.asyncio
    async def test_get_graph_data_without_book_id(self, mock_async_session, override_async_db):
        """book_id なしでリクエストした場合 422 エラーが返ることを検証"""
        response = client.get("/api/graph")
        
        # book_id は必須パラメータなので 422 (Unprocessable Entity) が返る
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_graph_response_schema_validation(
        self, mock_async_session, override_async_db, mock_foreshadowings, mock_characters, mock_character_relations
    ):
        """レスポンスが ForeshadowingGraphResponse スキーマに準拠することを検証"""
        from sqlalchemy import select
        from src.backend.database.models import Character as CharacterModel
        from src.backend.database.models_relation import CharacterRelationModel
        from src.backend.database.models_foreshadowing import ForeshadowingModel
        
        async def mock_execute(query):
            result = MagicMock()
            if "foreshadowings" in str(query).lower() or "ForeshadowingModel" in str(query):
                result.scalars.return_value.all.return_value = mock_foreshadowings
            elif "characters" in str(query).lower() or "CharacterModel" in str(query):
                result.scalars.return_value.all.return_value = mock_characters
            elif "character_relations" in str(query).lower() or "CharacterRelationModel" in str(query):
                result.scalars.return_value.all.return_value = mock_character_relations
            else:
                result.scalars.return_value.all.return_value = []
            return result
        
        mock_async_session.execute.side_effect = mock_execute
        
        response = client.get("/api/graph?book_id=1")
        
        assert response.status_code == 200
        data = response.json()
        
        # スキーマバリデーション
        graph_response = ForeshadowingGraphResponse(**data)
        
        assert isinstance(graph_response.graph_name, str)
        assert isinstance(graph_response.nodes, list)
        assert isinstance(graph_response.edges, list)
        
        # 各ノードが GraphNodeSchema に準拠
        for node in graph_response.nodes:
            assert isinstance(node.id, str)
            assert isinstance(node.label, str)
            assert isinstance(node.properties, dict)
        
        # 各エッジが GraphEdgeSchema に準拠
        for edge in graph_response.edges:
            assert isinstance(edge.source, str)
            assert isinstance(edge.target, str)
            assert isinstance(edge.type, str)
            assert isinstance(edge.properties, dict)

    @pytest.mark.asyncio
    async def test_graph_data_empty_foreshadowings(self, mock_async_session, override_async_db):
        """伏線データが空でもキャラのみのグラフが返ることを検証"""
        mock_characters = [
            {"id": 1, "name": "テスト主人公", "role": "主人公", "personality": "", "ability": ""},
        ]
        mock_relations = []
        
        async def mock_execute(query):
            result = MagicMock()
            if "foreshadowings" in str(query).lower():
                result.scalars.return_value.all.return_value = []
            elif "characters" in str(query).lower():
                # Return dict-like objects
                mock_chars = []
                for c in mock_characters:
                    mock_char = MagicMock()
                    mock_char.id = c["id"]
                    mock_char.name = c["name"]
                    mock_char.role = c["role"]
                    mock_char.personality = c["personality"]
                    mock_char.ability = c["ability"]
                    mock_chars.append(mock_char)
                result.scalars.return_value.all.return_value = mock_chars
            elif "character_relations" in str(query).lower():
                result.scalars.return_value.all.return_value = mock_relations
            else:
                result.scalars.return_value.all.return_value = []
            return result
        
        mock_async_session.execute.side_effect = mock_execute
        
        response = client.get("/api/graph?book_id=1")
        
        assert response.status_code == 200
        data = response.json()
        
        # キャラクターノードのみ存在
        character_nodes = [n for n in data["nodes"] if n.get("label") == "Character"]
        assert len(character_nodes) == 1
        
        # 伏線ノードなし
        foreshadowing_nodes = [n for n in data["nodes"] if n.get("label") == "Foreshadowing"]
        assert len(foreshadowing_nodes) == 0


class TestGraphRegression:
    """既存グラフAPI機能のリグレッションテスト"""

    def test_graph_endpoint_exists(self):
        """GET /api/graph エンドポイントが存在することを確認"""
        # ルーターにエンドポイントが登録されていること
        routes = [r for r in router.routes if r.path == "/api/graph" or r.path == ""]
        assert len(routes) >= 1

    def test_chunks_endpoint_exists(self):
        """GET /api/graph/chunks エンドポイントが存在することを確認"""
        routes = [r for r in router.routes if "/chunks" in r.path]
        assert len(routes) >= 1