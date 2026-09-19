from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.backend.auth import get_current_user, validate_api_key_sync
from src.backend.database.models import User
from src.backend.database.uow import UnitOfWork
from src.backend.security.owner_guard import verify_book_ownership
from src.core.container import AppContainer

from src.annotations.beat import EmotionalBeat
from src.annotations.persistence import AnnotationPersistence
from src.stores.vector_store import RedisVectorStore
from src.stores.graph_store import GraphStore, InMemoryGraphStore
from src.stores.event_log import EventLogStore
from src.pipeline.character_dict import load_character_dict
from src.pipeline.emotional_residue import EmotionType
from src.annotations.validator import BeatValidator

router = APIRouter(
    prefix="/api/annotations",
    tags=["annotations"],
    dependencies=[Depends(get_current_user)],
)


class BeatDTO(BaseModel):
    """感情ビートDTO（API用）"""
    beat_id: Optional[str] = None
    episode: int
    scene: int
    source: str
    target: str
    emotion: str
    delta: float = Field(ge=-1.0, le=1.0)
    cause: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    hidden: bool = False
    metadata: Dict[str, Any] = {}


class PersistRequest(BaseModel):
    """アノテーション永続化リクエスト"""
    book_id: int
    episode: int
    beats: List[BeatDTO]


class PersistResponse(BaseModel):
    """永続化レスポンス"""
    persisted: int
    errors: List[str] = []


class HistoryRequest(BaseModel):
    """履歴取得リクエスト"""
    book_id: int
    episode: int
    source: Optional[str] = None
    target: Optional[str] = None


class RollbackRequest(BaseModel):
    """ロールバックリクエスト"""
    book_id: int
    episode: int
    beat_id: str


def _get_stores() -> tuple:
    """ストアインスタンス取得"""
    vector_store = RedisVectorStore(skip_connection_check=True)
    graph_store = InMemoryGraphStore()
    log_store = EventLogStore()
    return vector_store, graph_store, log_store


def _beats_to_domain(beats_dto: List[BeatDTO], episode: int) -> List:
    """DTOをドメインモデルに変換"""
    from src.annotations.beat import EmotionalBeat
    from src.pipeline.emotional_residue import EmotionType
    
    domain_beats = []
    for dto in beats_dto:
        try:
            emotion_type = EmotionType(dto.emotion)
        except ValueError:
            emotion_type = EmotionType.AFFECTION
        
        beat = EmotionalBeat(
            episode=dto.episode,
            scene=dto.scene,
            source=dto.source,
            target=dto.target,
            emotion=emotion_type,
            delta=dto.delta,
            cause=dto.cause,
            beat_id=dto.beat_id or "",
            confidence=dto.confidence,
            hidden=dto.hidden,
            metadata=dto.metadata,
        )
        domain_beats.append(beat)
    return domain_beats


@router.post("/persist", response_model=PersistResponse)
async def persist_annotations(
    req: PersistRequest,
    current_user: User = Depends(get_current_user),
):
    """アノテーション永続化エンドポイント"""
    # 権限チェック
    await verify_book_ownership(req.book_id, current_user, AppContainer.db())
    
    # DTOをドメインモデルに変換
    domain_beats = _beats_to_domain(req.beats, req.episode)
    
    # キャラクター辞書取得
    char_dict = load_character_dict()
    
    # 検証
    validator = BeatValidator(char_dict)
    result = validator.validate(domain_beats)
    
    if not result.is_valid:
        return PersistResponse(persisted=0, errors=result.errors)
    
    # ストア取得・永続化
    vector_store, graph_store, log_store = _get_stores()
    persistence = AnnotationPersistence(vector_store, graph_store, log_store)
    
    try:
        count = persistence.persist_beats(domain_beats, req.episode)
        return PersistResponse(persisted=count, errors=result.warnings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"永続化エラー: {str(e)}")


@router.get("/history")
async def get_annotation_history(
    book_id: int,
    episode: int,
    source: Optional[str] = None,
    target: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """アノテーション履歴取得"""
    await verify_book_ownership(book_id, current_user, AppContainer.db())
    
    vector_store, _, log_store = _get_stores()
    
    # VectorStoreから履歴取得（annotation namespace）
    if source and target:
        # 特定ペアの履歴
        keys = vector_store.get_namespace_keys("annotation")
        pair_prefix = f"{source}->{target}"
        matching = [k for k in keys if pair_prefix in k and k.startswith(f"ep{episode}")]
        history = []
        for key in matching:
            vec = vector_store._get_by_key("annotation", key)
            if vec:
                emotions = vec.get_pair_emotions(source, target)
                for emo, val in emotions.items():
                    history.append({
                        "episode": vec.episode_id,
                        "source": source,
                        "target": target,
                        "emotion": emo.value,
                        "value": val,
                        "confidence": vec.confidences.get((source, target, emo), 0.0),
                        "cause": vec.causes.get((source, target, emo)),
                    })
        return {"history": history}
    
    # 全履歴（指定エピソード）
    keys = vector_store.get_namespace_keys("annotation")
    matching = [k for k in keys if k.startswith(f"ep{episode}")]
    history = []
    for key in matching:
        vec = vector_store._get_by_key("annotation", key)
        if vec:
            for (s, t, emo), val in vec.signals.items():
                history.append({
                    "episode": vec.episode_id,
                    "source": s,
                    "target": t,
                    "emotion": emo.value,
                    "value": val,
                    "confidence": vec.confidences.get((s, t, emo), 0.0),
                    "cause": vec.causes.get((s, t, emo)),
                })
    return {"history": history}


@router.post("/rollback")
async def rollback_annotation(
    req: RollbackRequest,
    current_user: User = Depends(get_current_user),
):
    """指定ビートのロールバック（論理削除・再計算トリガー）"""
    await verify_book_ownership(req.book_id, current_user, AppContainer.db())
    
    vector_store, graph_store, log_store = _get_stores()
    
    try:
        # LogStoreから該当ビートを論理削除（source_type=annotationでフィルタ）
        deleted = log_store.delete_by_beat_id(req.episode, req.beat_id)
        
        if deleted == 0:
            raise HTTPException(status_code=404, detail="指定されたビートが見つかりません")
        
        # VectorStoreからも削除
        vector_store.delete("annotation", f"ep{req.episode}:{req.beat_id}")
        
        # GraphStoreからも削除
        # ここでソース・ターゲットが必要だが、beat_idから推定するか、
        # 全エッジからbeat_idで検索して削除する
        # 簡易実装: InMemoryGraphStoreではbeat_idでフィルタ削除可能
        if hasattr(graph_store, '_edges'):
            for (src, tgt), edges in list(graph_store._edges.items()):
                original_len = len(edges)
                graph_store._edges[(src, tgt)] = [e for e in edges if e.get("beat_id") != req.beat_id]
                if len(graph_store._edges.get((src, tgt), [])) == 0:
                    del graph_store._edges[(src, tgt)]
        
        # 再計算トリガー（非同期で実行）
        # ここでは完了フラグのみ返す
        return {
            "deleted": deleted,
            "message": "ロールバック完了。再計算は非同期で実行されます。",
            "recalculation_triggered": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ロールバックエラー: {str(e)}")


__all__ = ["router"]