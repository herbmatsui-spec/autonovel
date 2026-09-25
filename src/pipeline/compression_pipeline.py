"""圧縮パイプライン (Week 2 Steps 15-16)。

Week 1 の自動抽出ベクトル (pipeline ネームスペース) と Week 2 の
ルールエンジンベースラインベクトル (rule_engine ネームスペース) を併存させる。
融合は読み取り側 (Week 4) で実施する。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.pipeline.emotional_residue import EmotionalResidueExtractor, EmotionalVector
from src.rules.engine import RULE_ENGINE_NAMESPACE, RuleEngine
from src.rules.plot_events import PlotEvent
from src.rules.state_machine import EmotionalStateMachine

logger = logging.getLogger(__name__)

# ネームスペース定義 (Week 1-3 で分離)
NAMESPACE_PIPELINE = "pipeline"        # Week 1 の自動抽出
NAMESPACE_RULE_ENGINE = RULE_ENGINE_NAMESPACE  # Week 2 のベースライン ("rule_engine")
NAMESPACE_ANNOTATION = "annotation"    # Week 3 の人間上書き


class CompressionPipeline:
    """エピソード処理パイプライン。

    エピソード開始前にルールエンジンでベースラインベクトルを生成し、
    脚本抽出ベクトルと併存保存する。

    Args:
        extractor: Week 1 の感情残基抽出器
        vector_store: ベクトルストア (upsert/get_latest/get_all を提供)
        rule_engine: ルールエンジン (省略可。指定時はベースライン生成を実行)
    """

    def __init__(
        self,
        extractor: Optional[EmotionalResidueExtractor] = None,
        vector_store: Any = None,
        rule_engine: Optional[RuleEngine] = None,
        graph_store: Any = None,
        log_store: Any = None,
    ) -> None:
        self.extractor = extractor
        self.vector_store = vector_store
        self.rule_engine = rule_engine
        self.graph_store = graph_store
        self.log_store = log_store
        # エピソード間で状態を引き継ぐためのスナップショット
        self._last_rule_snapshot: Optional[Dict[str, Dict[str, float]]] = None
        self._last_rule_episode: Optional[int] = None

    def run(self, episode_id: str, script: str, episode: Optional[int] = None) -> Dict[str, Any]:
        """エピソード処理を実行する。

        フロー:
            1. ルールエンジン有効時: エピソード開始前に process_episode 実行
               (プロットイベントは episode_id に対応するエピソードから取得)
            2. 脚本から感情ベクトル抽出 (Week 1)
            3. 両方のベクトルをそれぞれのネームスペースに保存

        Args:
            episode_id: エピソード ID (例: "ep14")
            script: 脚本テキスト
            episode: エピソード番号 (ルールエンジン用、省略時は episode_id から推定)

        Returns:
            処理結果サマリ
        """
        result: Dict[str, Any] = {"episode_id": episode_id}

        # 1. ルールエンジンステージ (エピソード開始前)
        rule_vector = self._run_rule_engine_stage(episode_id, episode)
        result["rule_engine_vector"] = rule_vector is not None

        # 2. 脚本抽出 (Week 1)
        pipeline_vector: Optional[EmotionalVector] = None
        if self.extractor is not None:
            pipeline_vector = self.extractor.extract_and_persist(episode_id, script)
        result["pipeline_vector"] = pipeline_vector is not None

        # 3. ネームスペース分離保存 (ルールエンジン側は _run_rule_engine_stage で保存済み)
        result["namespaces"] = {
            NAMESPACE_PIPELINE: pipeline_vector is not None,
            NAMESPACE_RULE_ENGINE: rule_vector is not None,
        }
        return result

    def _run_rule_engine_stage(self, episode_id: str, episode: Optional[int]) -> Optional[EmotionalVector]:
        """ルールエンジンステージを実行する。

        Args:
            episode_id: エピソード ID
            episode: エピソード番号

        Returns:
            生成されたベースラインベクトル (無効時は None)
        """
        if self.rule_engine is None:
            return None

        ep = episode if episode is not None else _extract_episode(episode_id)
        if ep is None:
            logger.warning("Cannot determine episode number from %s; skipping rule engine stage", episode_id)
            return None

        events = self._get_events_for_episode(ep)
        vector = self.rule_engine.process_episode(
            ep,
            events,
            previous_snapshot=self._last_rule_snapshot,
            previous_episode=self._last_rule_episode,
        )
        # エピソード間の状態引き継ぎ用に保存
        self._last_rule_snapshot = self.rule_engine.last_snapshot
        self._last_rule_episode = ep

        # 永続化 (ストアが利用可能な場合)
        if any(s is not None for s in (self.vector_store, self.graph_store, self.log_store)):
            self.rule_engine.persist_results(
                self.vector_store, self.graph_store, self.log_store, episode=ep,
            )
        return vector

    def _get_events_for_episode(self, episode: int) -> List[PlotEvent]:
        """エピソードに対応するプロットイベントを取得する。

        rule_engine にイベントソースが設定されている場合はそこから、
        なければ config/plot_events.yaml から取得する。
        """
        loader = getattr(self.rule_engine, "event_source", None)
        if loader is not None:
            events = loader(episode)
            if events is not None:
                return events
        # デフォルト: config ファイルから
        try:
            from src.rules.rule_loader import parse_episode_events

            events_by_ep = parse_episode_events()
            return events_by_ep.get(episode, [])
        except (FileNotFoundError, Exception) as e:
            logger.debug("No plot events available: %s", e)
            return []

    def get_baseline_vector(self, episode_id: str, episode: Optional[int] = None) -> Optional[EmotionalVector]:
        """ベースラインベクトル (rule_engine ネームスペース) を取得する。"""
        if self.vector_store is None:
            return None
        ep = episode if episode is not None else _extract_episode(episode_id)
        if ep is None:
            return None
        return self.vector_store.get_latest(
            NAMESPACE_RULE_ENGINE,
            (f"ep{ep}", f"ep{ep}"),
        ) if hasattr(self.vector_store, "get_latest") else None


def _extract_episode(episode_id: str) -> Optional[int]:
    """"ep14" 形式の ID からエピソード番号を推定。"""
    text = str(episode_id).strip().lower()
    if text.startswith("ep"):
        try:
            return int(text[2:])
        except ValueError:
            return None
    return None


def create_rule_engine(
    rules_path: Optional[str] = None,
    state_machine: Optional[EmotionalStateMachine] = None,
) -> RuleEngine:
    """設定からルールエンジンを生成するヘルパー。

    Args:
        rules_path: ルールセット YAML パス (省略時はデフォルト)
        state_machine: 感情状態マシン (省略時は新規生成)

    Returns:
        RuleEngine インスタンス
    """
    from src.rules.rule_loader import DEFAULT_RULES_PATH, RuleLoader

    rules = RuleLoader().load_rules(rules_path or DEFAULT_RULES_PATH)
    return RuleEngine(rules=rules, state_machine=state_machine or EmotionalStateMachine())


__all__ = [
    "CompressionPipeline",
    "create_rule_engine",
    "NAMESPACE_PIPELINE",
    "NAMESPACE_RULE_ENGINE",
    "NAMESPACE_ANNOTATION",
]
