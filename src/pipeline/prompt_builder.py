"""Prompt builder for emotional context injection."""
from __future__ import annotations

from typing import Optional

from jinja2 import Environment, FileSystemLoader

from src.pipeline.emotional_residue import EmotionalVector
from src.stores.vector_store import VectorStore


# Jinja2環境（シングルトン）
_jinja_env: Optional[Environment] = None


def get_jinja_env() -> Environment:
    """Jinja2環境取得（シングルトン）"""
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=False,
        )
    return _jinja_env


def build_emotional_context_prompt(
    episode_id: int,
    vector_store: VectorStore,
    namespace: str = "pipeline",
    top_n: int = 5,
) -> str:
    """前話の感情コンテキストプロンプト生成
    
    Args:
        episode_id: 現在のエピソード番号（前話から取得するため -1 される）
        vector_store: ベクトルストア
        namespace: 取得するネームスペース
        top_n: 表示する主要ペア数
        
    Returns:
        感情コンテキスト文字列
    """
    prev_episode = episode_id - 1
    if prev_episode < 1:
        return ""
    
    # エピソードID形式: "ep{num}"
    ep_key = f"ep{prev_episode}"
    
    # ベクトル取得
    # 全キーから該当エピソードのベクトルを取得
    keys = vector_store.get_namespace_keys(namespace)
    ep_keys = [k for k in keys if k == ep_key or k.startswith(f"{ep_key}:")]
    
    if not ep_keys:
        return ""
    
    # 最新のベクトル取得（単一キーの場合）
    vector = vector_store.get_latest(namespace, ("", ""))  # ペア指定なしで全取得試行
    
    # キー指定で取得を試行
    for key in ep_keys:
        vec = vector_store._get_by_key(namespace, key) if hasattr(vector_store, '_get_by_key') else None
        if vec:
            vector = vec
            break
    else:
        return ""
    
    if not vector or not vector.signals:
        return ""
    
    # テンプレート描画
    template = get_jinja_env().get_template("emotional_context.j2")
    top_pairs = vector.get_top_pairs(top_n)
    
    return template.render(
        top_pairs=top_pairs,
        vector=vector,
    )


EMOTION_JA_MAP = {
    "fear": "恐怖",
    "affection": "好意",
    "tension": "緊張",
    "trust": "信頼",
    "intimacy": "親愛",
    "jealousy": "嫉妬",
    "anger": "怒り",
    "sadness": "悲哀",
    "surprise": "驚き",
    "disgust": "嫌悪",
}


def build_fused_emotional_context_prompt(
    episode_id: int,
    fusion_engine: Optional[Any] = None,
    vector_store: Optional[VectorStore] = None,
    namespaces: Optional[list[str]] = None,
    top_n: int = 5,
) -> str:
    """融合済み感情コンテキストプロンプト生成（Week 4 融合レイヤー版）
    
    Args:
        episode_id: 現在のエピソード番号（前話 episode_id - 1 から引き継ぐ）
        fusion_engine: FusionEngine インスタンス（推奨）
        vector_store: VectorStore（fusion_engine 未指定時に生成用）
        namespaces: 参照ネームスペース一覧
        top_n: 上位表示件数
        
    Returns:
        融合済み感情コンテキスト文字列
    """
    prev_episode = episode_id - 1
    if prev_episode < 1:
        return ""

    if fusion_engine is None and vector_store is not None:
        from src.fusion.engine import FusionEngine
        fusion_engine = FusionEngine(vector_store)

    if fusion_engine is None:
        return ""

    # 前話の融合ベクトル取得または融合実行
    fused_vector = fusion_engine.get_fused(prev_episode)
    if not fused_vector:
        fused_vector = fusion_engine.fuse_all(prev_episode)

    if not fused_vector or (not fused_vector.values and not fused_vector.conflicts):
        return ""

    # 信頼度別にアイテムを分類
    high_confidence = []
    medium_confidence = []
    low_confidence = []

    for (src, tgt, emo), f_val in fused_vector.values.items():
        emo_str = emo.value if hasattr(emo, "value") else str(emo)
        emo_ja = EMOTION_JA_MAP.get(emo_str, emo_str)
        item = {
            "source": src,
            "target": tgt,
            "emotion": emo_str,
            "emotion_ja": emo_ja,
            "value": f_val.value,
            "primary_source": f_val.primary_source,
            "confidence": f_val.confidence,
            "cause": "",
        }
        if f_val.confidence >= 0.8:
            high_confidence.append(item)
        elif f_val.confidence >= 0.4:
            medium_confidence.append(item)
        else:
            low_confidence.append(item)

    # 矛盾リストの整形
    formatted_conflicts = []
    for c in fused_vector.conflicts:
        emo_str = c.emotion.value if hasattr(c.emotion, "value") else str(c.emotion)
        emo_ja = EMOTION_JA_MAP.get(emo_str, emo_str)
        formatted_conflicts.append({
            "pair": c.pair,
            "emotion": emo_str,
            "emotion_ja": emo_ja,
            "sources": c.sources,
        })

    try:
        template = get_jinja_env().get_template("fused_emotional_context.j2")
        rendered = template.render(
            high_confidence=high_confidence,
            medium_confidence=medium_confidence,
            low_confidence=low_confidence,
            conflicts=formatted_conflicts,
        )
        return rendered.strip()
    except Exception:
        return ""


__all__ = ["build_emotional_context_prompt", "build_fused_emotional_context_prompt", "get_jinja_env", "EMOTION_JA_MAP"]