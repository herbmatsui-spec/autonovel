"""Tests for annotations API endpoints - unit tests with proper mocking."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Test the router logic directly without full FastAPI client
# This avoids database/auth middleware issues


class TestAnnotationsRouterLogic:
    """アノテーションルーターのロジックテスト"""

    def test_beat_dto_validation(self):
        """BeatDTOのバリデーションテスト"""
        from src.backend.routers.annotations import BeatDTO
        from pydantic import ValidationError
        
        # 正常なデータ
        dto = BeatDTO(
            episode=14,
            scene=3,
            source="A",
            target="B",
            emotion="fear",
            delta=0.8,
            cause="ep14 betrayal",
        )
        assert dto.delta == 0.8
        assert dto.emotion == "fear"
        
        # delta範囲外エラー
        with pytest.raises(ValidationError):
            BeatDTO(episode=14, scene=3, source="A", target="B", emotion="fear", delta=1.5, cause="test")
        
        with pytest.raises(ValidationError):
            BeatDTO(episode=14, scene=3, source="A", target="B", emotion="fear", delta=-1.5, cause="test")

    def test_persist_request_validation(self):
        """PersistRequestのバリデーションテスト"""
        from src.backend.routers.annotations import PersistRequest, BeatDTO
        from pydantic import ValidationError
        
        # 正常
        req = PersistRequest(
            book_id=1,
            episode=14,
            beats=[
                BeatDTO(episode=14, scene=3, source="A", target="B", emotion="fear", delta=0.8, cause="test")
            ]
        )
        assert req.book_id == 1
        assert len(req.beats) == 1
        
        # 空beatsも許可される（Pydanticデフォルト）
        req_empty = PersistRequest(book_id=1, episode=14, beats=[])
        assert req_empty.beats == []

    def test_rollback_request_validation(self):
        """RollbackRequestのバリデーションテスト"""
        from src.backend.routers.annotations import RollbackRequest
        from pydantic import ValidationError
        
        req = RollbackRequest(book_id=1, episode=14, beat_id="beat123")
        assert req.beat_id == "beat123"
        
        # 必須フィールド欠落
        with pytest.raises(ValidationError):
            RollbackRequest(book_id=1, episode=14)

    def test_beats_to_domain_conversion(self):
        """DTO→ドメイン変換テスト"""
        from src.backend.routers.annotations import _beats_to_domain, BeatDTO
        from src.pipeline.emotional_residue import EmotionType
        
        beats_dto = [
            BeatDTO(episode=14, scene=3, source="A", target="B", emotion="fear", delta=0.8, cause="test"),
            BeatDTO(episode=14, scene=3, source="B", target="A", emotion="sadness", delta=0.6, cause="test2"),
        ]
        
        domain_beats = _beats_to_domain(beats_dto, 14)
        
        assert len(domain_beats) == 2
        assert domain_beats[0].source == "A"
        assert domain_beats[0].target == "B"
        assert domain_beats[0].emotion == EmotionType.FEAR
        assert domain_beats[0].delta == 0.8
        assert domain_beats[1].emotion == EmotionType.SADNESS

    def test_beats_to_domain_unknown_emotion(self):
        """未知の感情タイプはAFFECTIONにフォールバック"""
        from src.backend.routers.annotations import _beats_to_domain, BeatDTO
        from src.pipeline.emotional_residue import EmotionType
        
        beats_dto = [
            BeatDTO(episode=14, scene=3, source="A", target="B", emotion="unknown_emotion", delta=0.5, cause="test"),
        ]
        
        domain_beats = _beats_to_domain(beats_dto, 14)
        assert domain_beats[0].emotion == EmotionType.AFFECTION

    @pytest.mark.asyncio
    async def test_persist_annotations_logic(self):
        """persist_annotationsのロジックテスト（モック使用）"""
        from src.backend.routers.annotations import persist_annotations
        from src.backend.routers.annotations import PersistRequest, BeatDTO, PersistResponse
        from src.pipeline.emotional_residue import EmotionType
        
        req = PersistRequest(
            book_id=1,
            episode=14,
            beats=[
                BeatDTO(episode=14, scene=3, source="A", target="B", emotion="fear", delta=0.8, cause="test"),
            ]
        )
        
        # モックセットアップ
        with patch("src.backend.routers.annotations.verify_book_ownership", new_callable=AsyncMock) as mock_verify:
            with patch("src.backend.routers.annotations.load_character_dict", return_value={"A", "B"}) as mock_load_dict:
                with patch("src.backend.routers.annotations.BeatValidator") as mock_validator_cls:
                    with patch("src.backend.routers.annotations._get_stores") as mock_get_stores:
                        with patch("src.backend.routers.annotations.AnnotationPersistence") as mock_persistence_cls:
                            # モック設定
                            mock_validator = MagicMock()
                            mock_validator.validate.return_value = MagicMock(is_valid=True, errors=[], warnings=[])
                            mock_validator_cls.return_value = mock_validator
                            
                            mock_vector_store = MagicMock()
                            mock_graph_store = MagicMock()
                            mock_log_store = MagicMock()
                            mock_get_stores.return_value = (mock_vector_store, mock_graph_store, mock_log_store)
                            
                            mock_persistence = MagicMock()
                            mock_persistence.persist_beats.return_value = 1
                            mock_persistence_cls.return_value = mock_persistence
                            
                            # モックユーザー
                            mock_user = MagicMock()
                            mock_user.id = 1
                            
                            # 実行
                            result = await persist_annotations(req, mock_user)
                            
                            # 検証
                            assert isinstance(result, PersistResponse)
                            assert result.persisted == 1
                            assert result.errors == []
                            
                            # 呼び出し確認
                            mock_verify.assert_called_once()
                            mock_load_dict.assert_called_once()
                            mock_validator.validate.assert_called_once()
                            mock_persistence.persist_beats.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_annotations_validation_failure(self):
        """バリデーションエラー時の挙動"""
        from src.backend.routers.annotations import persist_annotations, PersistRequest, BeatDTO
        
        req = PersistRequest(
            book_id=1,
            episode=14,
            beats=[
                BeatDTO(episode=14, scene=3, source="X", target="B", emotion="fear", delta=0.8, cause="test"),
            ]
        )
        
        with patch("src.backend.routers.annotations.verify_book_ownership", new_callable=AsyncMock):
            with patch("src.backend.routers.annotations.load_character_dict", return_value={"A", "B"}):
                with patch("src.backend.routers.annotations.BeatValidator") as mock_validator_cls:
                    mock_validator = MagicMock()
                    mock_validator.validate.return_value = MagicMock(is_valid=False, errors=["Unknown character 'X'"], warnings=[])
                    mock_validator_cls.return_value = mock_validator
                    
                    with patch("src.backend.routers.annotations._get_stores"):
                        mock_user = MagicMock()
                        result = await persist_annotations(req, mock_user)
                        
                        assert result.persisted == 0
                        assert "Unknown character" in result.errors[0]

    def test_get_stores_returns_correct_types(self):
        """_get_storesが正しい型を返すこと"""
        from src.backend.routers.annotations import _get_stores
        from src.stores.vector_store import RedisVectorStore
        from src.stores.graph_store import InMemoryGraphStore
        from src.stores.event_log import EventLogStore
        
        vector_store, graph_store, log_store = _get_stores()
        
        assert isinstance(vector_store, RedisVectorStore)
        assert isinstance(graph_store, InMemoryGraphStore)
        assert isinstance(log_store, EventLogStore)

    @pytest.mark.asyncio
    async def test_get_annotation_history_logic(self):
        """履歴取得ロジックのテスト"""
        from src.backend.routers.annotations import get_annotation_history
        from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
        
        with patch("src.backend.routers.annotations.verify_book_ownership", new_callable=AsyncMock):
            with patch("src.backend.routers.annotations._get_stores") as mock_get_stores:
                mock_vector_store = MagicMock()
                mock_log_store = MagicMock()
                mock_get_stores.return_value = (mock_vector_store, MagicMock(), mock_log_store)
                
                # モックベクトル
                vec = EmotionalVector(episode_id="ep14")
                vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 0.9, "...", "ep14", "ep14 betrayal"))
                
                mock_vector_store.get_namespace_keys.return_value = ["ep14:A->B"]
                mock_vector_store._get_by_key.return_value = vec
                
                mock_user = MagicMock()
                result = await get_annotation_history(book_id=1, episode=14, source="A", target="B", current_user=mock_user)
                
                assert "history" in result
                assert len(result["history"]) == 1
                assert result["history"][0]["emotion"] == "fear"
                assert result["history"][0]["value"] == 0.8

    @pytest.mark.asyncio
    async def test_rollback_annotation_logic(self):
        """ロールバックロジックのテスト"""
        from src.backend.routers.annotations import rollback_annotation, RollbackRequest
        
        with patch("src.backend.routers.annotations.verify_book_ownership", new_callable=AsyncMock):
            with patch("src.backend.routers.annotations._get_stores") as mock_get_stores:
                mock_vector_store = MagicMock()
                mock_graph_store = MagicMock()
                mock_log_store = MagicMock()
                mock_get_stores.return_value = (mock_vector_store, mock_graph_store, mock_log_store)
                
                mock_log_store.delete_by_beat_id.return_value = 1
                mock_vector_store.delete.return_value = True
                mock_graph_store._edges = {("A", "B"): [{"beat_id": "beat123", "cause": "test"}]}
                
                mock_user = MagicMock()
                req = RollbackRequest(book_id=1, episode=14, beat_id="beat123")
                
                result = await rollback_annotation(req, mock_user)
                
                assert result["deleted"] == 1
                assert result["recalculation_triggered"] is True
                mock_log_store.delete_by_beat_id.assert_called_once_with(14, "beat123")
                mock_vector_store.delete.assert_called_once_with("annotation", "ep14:beat123")

    @pytest.mark.asyncio
    async def test_rollback_not_found(self):
        """ロールバック: 見つからない場合"""
        from src.backend.routers.annotations import rollback_annotation, RollbackRequest
        from fastapi import HTTPException
        
        with patch("src.backend.routers.annotations.verify_book_ownership", new_callable=AsyncMock):
            with patch("src.backend.routers.annotations._get_stores") as mock_get_stores:
                mock_log_store = MagicMock()
                mock_vector_store = MagicMock()
                mock_get_stores.return_value = (mock_vector_store, MagicMock(), mock_log_store)
                
                mock_log_store.delete_by_beat_id.return_value = 0
                
                mock_user = MagicMock()
                req = RollbackRequest(book_id=1, episode=14, beat_id="nonexistent")
                
                with pytest.raises(HTTPException) as exc_info:
                    await rollback_annotation(req, mock_user)
                
                assert exc_info.value.status_code == 404
                assert "見つかりません" in str(exc_info.value.detail)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])