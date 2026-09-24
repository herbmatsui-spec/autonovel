"""Writer Agent with hierarchical agent memory (Core/Working/Archival) integration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.memory.compaction import CompactionPolicy
from src.agents.memory.manager import MemoryManager
from src.agents.tools.memory_tools import MEMORY_TOOLS_SCHEMA
from src.agents.tool_handler import ToolHandler
from src.fusion.config import FusionConfig, load_fusion_config
from src.fusion.engine import FusionEngine
from src.pipeline.emotional_residue import EmotionalVector
from src.pipeline.prompt_builder import build_emotional_context_prompt, build_fused_emotional_context_prompt
from src.stores.vector_store import VectorStore


class WriterAgent:
    """自律的な感情メモリ（Core/Working/Archival）を備えた執筆エージェント"""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        fusion_engine: Optional[FusionEngine] = None,
        memory_manager: Optional[MemoryManager] = None,
        config: Optional[FusionConfig] = None,
        fusion_enabled: bool = True,
        save_directory: Optional[str | Path] = None,
    ):
        self.config = config or load_fusion_config()
        self.vector_store = vector_store
        self.fusion_enabled = fusion_enabled
        self.save_directory = Path(save_directory) if save_directory else Path("memory/default/main")

        # 融合エンジン初期化
        self.fusion_engine = fusion_engine
        if self.fusion_engine is None and self.vector_store is not None:
            self.fusion_engine = FusionEngine(self.vector_store, self.config)

        # メモリマネージャー初期化
        self.memory_manager = memory_manager or MemoryManager(vector_store=self.vector_store)
        self.tool_handler = ToolHandler(self.memory_manager)
        self.compaction_policy = CompactionPolicy()
        self.tools = list(MEMORY_TOOLS_SCHEMA)

    def get_emotional_prompt(self, episode: int) -> str:
        """エピソード執筆用の感情コンテキストプロンプトを生成する"""
        if self.fusion_enabled and self.fusion_engine is not None:
            prompt = build_fused_emotional_context_prompt(
                episode_id=episode,
                fusion_engine=self.fusion_engine,
            )
            if prompt:
                return prompt

        if self.vector_store is not None:
            return build_emotional_context_prompt(
                episode_id=episode,
                vector_store=self.vector_store,
            )

        return ""

    def build_system_prompt(self, episode: int, base_prompt: str = "") -> str:
        """CoreMemory の常駐感情状態および検出ルールを含めたシステムプロンプトを構築"""
        parts = []
        if base_prompt:
            parts.append(base_prompt)

        # 1. 感情変化検知ルール
        parts.append(
            "## 執筆指示\n"
            "執筆中にキャラクター間の感情変化を検知した場合は、提供されているツール（update_emotion 等）を自律的に呼び出してください。\n"
            "過去の感情経緯が必要な場合は recall_similar_scene や trace_emotional_cause を使用してください。"
        )

        # 2. 前話からの引き継ぎ感情プロンプト
        emotional_context = self.get_emotional_prompt(episode)
        if emotional_context:
            parts.append(emotional_context)

        # 3. CoreMemory の常駐サマリー
        core_dump = self.memory_manager.core_memory.dump()
        if core_dump.get("character_emotions"):
            parts.append("## CoreMemory 常駐感情:")
            parts.append(json.dumps(core_dump["character_emotions"], ensure_ascii=False, indent=2))

        return "\n\n".join(parts)

    def write_episode(
        self,
        episode: int,
        plot_outline: str,
        simulated_tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """エピソードを執筆し、ツール呼び出しを実行し、エピソード境界で自動圧縮・保存を行う"""
        # 1. 前話の FusedVector があれば初期 CoreMemory にロード
        prev_ep = episode - 1
        if prev_ep >= 1 and self.fusion_engine is not None:
            fused = self.fusion_engine.get_fused(prev_ep) or self.fusion_engine.fuse_all(prev_ep)
            if fused and fused.values:
                self.memory_manager.core_memory.load_fused_vector(fused, episode_label=f"ep{prev_ep}")

        # 2. ツール呼び出し（シミュレーションまたはLLM連携）
        if simulated_tool_calls:
            self.tool_handler.handle_calls(simulated_tool_calls)

        # 3. 本文生成（シミュレートまたはドラフト）
        manuscript = f"=== 第{episode}話 ===\nプロット: {plot_outline}\n執筆完了。"

        # 4. エピソード境界での自動圧縮・保存 (Step 12)
        self.compaction_policy.compact(
            core_memory=self.memory_manager.core_memory,
            current_episode=episode,
            archival_memory=self.memory_manager.archival_memory,
        )

        # 要約を ArchivalMemory に保存
        summary = f"第{episode}話の感情ハイライト: プロット『{plot_outline[:50]}』完了に伴う感情推移"
        self.memory_manager.archival_memory.insert_emotional_summary(
            episode=episode,
            summary=summary,
        )

        # CoreMemory をディスク永続化
        self.memory_manager.save_state(self.save_directory)

        # WorkingMemory クリア
        self.memory_manager.working_memory.clear()

        return manuscript


__all__ = ["WriterAgent"]
