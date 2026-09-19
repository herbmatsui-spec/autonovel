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


def build_fused_emotional_context_prompt(
    episode_id: int,
    vector_store: VectorStore,
    namespaces: list[str] = None,
    top_n: int = 5,
) -> str:
    """融合済み感情コンテキストプロンプト生成（Week 4以降用）
    
    複数ネームスペースから優先順位でベクトル取得・融合
    """
    if namespaces is None:
        namespaces = ["annotation", "rule_engine", "pipeline"]
    
    prev_episode = episode_id - 1
    if prev_episode < 1:
        return ""
    
    # 簡易実装: 最初に見つかったネームスペースを使用
    for ns in namespaces:
        keys = vector_store.get_namespace_keys(ns)
        ep_keys = [k for k in keys if k == f"ep{prev_episode}" or k.startswith(f"ep{prev_episode}:")]
        if ep_keys:
            for key in ep_keys:
                if hasattr(vector_store, '_get_by_key'):
                    vec = vector_store._get_by_key(ns, key)
                    if vec:
                        template = get_jinja_env().get_template("emotional_context.j2")
                        top_pairs = vec.get_top_pairs(top_n)
                        return template.render(top_pairs=top_pairs, vector=vec)
    
    return ""


__all__ = ["build_emotional_context_prompt", "build_fused_emotional_context_prompt", "get_jinja_env"]