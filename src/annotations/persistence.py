"""Annotation persistence adapter - saves beats to Vector/Graph/Log stores."""
from __future__ import annotations

from typing import Optional

from src.annotations.beat import EmotionalBeat
from src.pipeline.emotional_residue import EmotionalSignal, EmotionalVector
from src.stores.vector_store import VectorStore
from src.stores.graph_store import GraphStore
from src.stores.event_log import EventLogStore


class AnnotationPersistence:
    """感情ビートを各ストアに永続化"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: Optional[GraphStore] = None,
        log_store: Optional[EventLogStore] = None,
    ):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.log_store = log_store

    def persist_beats(self, beats: list[EmotionalBeat], episode: int) -> int:
        """ビートリストを全ストアに保存
        
        Returns:
            保存したビート数
        """
        if not beats:
            return 0
        
        # VectorStore: エピソード単位でベクトル生成・保存
        vector = self._beats_to_vector(beats, episode)
        if self.vector_store:
            key = f"ep{episode}"
            self.vector_store.upsert("annotation", key, vector)
        
        # GraphStore: エッジとして保存
        if self.graph_store:
            for beat in beats:
                self._persist_to_graph(beat, episode)
        
        # EventLogStore: 個別シグナルとして追記
        if self.log_store:
            for beat in beats:
                self.log_store.append(beat.to_signal())
        
        return len(beats)

    def _beats_to_vector(self, beats: list[EmotionalBeat], episode: int) -> EmotionalVector:
        """ビートリストからEmotionalVector生成"""
        vector = EmotionalVector(episode_id=f"ep{episode}")
        for beat in beats:
            # EmotionalBeat.emotion は EmotionType enum
            # 安全のために文字列の場合も対応
            if isinstance(beat.emotion, str):
                from src.pipeline.emotional_residue import EmotionType
                emotion = EmotionType(beat.emotion)
            else:
                emotion = beat.emotion
            
            signal = EmotionalSignal(
                source=beat.source,
                target=beat.target,
                emotion_type=emotion,
                value=beat.delta,
                confidence=beat.confidence,
                evidence_span=f"[beat:{emotion.value}{beat.delta:+.1f} cause=\"{beat.cause}\"]",
                episode_id=f"ep{episode}",
                cause=beat.cause,
                hidden=beat.hidden,
            )
            vector.set_signal(signal)
        return vector

    def _persist_to_graph(self, beat: EmotionalBeat, episode: int) -> None:
        """GraphStoreにエッジ保存"""
        if not self.graph_store:
            return
        
        props = {
            "affection": 0.0,
            "tension": 0.0,
            "fear": 0.0,
            "trust": 0.0,
            "intimacy": 0.0,
            "jealousy": 0.0,
            "anger": 0.0,
            "sadness": 0.0,
            "surprise": 0.0,
            "disgust": 0.0,
        }
        props[beat.emotion.value] = beat.delta
        
        props.update({
            "cause": beat.cause,
            "episode": episode,
            "beat_id": beat.beat_id,
            "confidence": beat.confidence,
            "hidden": beat.hidden,
            "source_type": "annotation",
        })
        
        self.graph_store.upsert_edge(
            source=beat.source,
            target=beat.target,
            props=props,
        )


def persist_annotations(
    beats: list[EmotionalBeat],
    episode: int,
    vector_store: VectorStore,
    graph_store: Optional[GraphStore] = None,
    log_store: Optional[EventLogStore] = None,
) -> int:
    """便利関数: アノテーション永続化"""
    persistence = AnnotationPersistence(vector_store, graph_store, log_store)
    return persistence.persist_beats(beats, episode)


__all__ = ["AnnotationPersistence", "persist_annotations"]