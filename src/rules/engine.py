"""ルールエンジンコア (Week 2 Steps 8-10, 13)。

プロットイベントを処理して感情シグナルを生成し、エピソード単位での
一括処理・減衰・永続化を提供する。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.pipeline.emotional_residue import (
    EmotionalSignal,
    EmotionalVector,
    EmotionType,
)
from src.rules.emotional_rules import EmotionalRule, PlotContext
from src.rules.plot_events import PlotEvent, Role
from src.rules.state_machine import EmotionalStateMachine

logger = logging.getLogger(__name__)

# ベースラインベクトルのネームスペース (Week 2)
RULE_ENGINE_NAMESPACE = "rule_engine"


class RuleEngine:
    """プロットイベント駆動の感情変化ルールエンジン。

    Args:
        rules: 適用可能な感情変化ルールのリスト
        state_machine: 感情状態マシン (ペアごとの状態管理)
    """

    def __init__(
        self,
        rules: List[EmotionalRule],
        state_machine: EmotionalStateMachine,
    ) -> None:
        self.rules = list(rules)
        self.state_machine = state_machine
        self._last_vector: Optional[EmotionalVector] = None

    # ------------------------------------------------------------------
    # Step 8: 単一イベント処理
    # ------------------------------------------------------------------
    def process_event(self, event: PlotEvent, context: PlotContext) -> List[EmotionalSignal]:
        """単一プロットイベントを処理してシグナルリストを返す。

        ロジック:
            1. マッチするルール抽出 (event_type 一致)
            2. 条件関数評価
            3. roles から source/target 解決
            4. state_machine.apply_delta 実行
            5. EmotionalSignal 生成 (evidence_span に event_id 記録)

        Args:
            event: プロットイベント
            context: ルール評価用コンテキスト

        Returns:
            生成された EmotionalSignal のリスト
        """
        signals: List[EmotionalSignal] = []

        # イベントの metadata をコンテキストに反映 (process_event 直呼び時も有効)
        context = self._merge_metadata(context, event)

        for rule in self.rules:
            # 1. event_type 一致判定
            if not rule.matches(event):
                continue

            # 2. 条件評価 (条件なし=常に適用、例外は False 扱い)
            if not rule.evaluate(context):
                continue

            # 3. source/target 解決 (役割に対応するキャラクターが両方いる場合のみ)
            source = event.get_character(rule.source_role)
            target = event.get_character(rule.target_role)
            if source is None or target is None or source == target:
                continue

            # 4. 状態マシンに delta 適用 (ルールの decay_per_episode を紐付け)
            for emotion_type, delta in rule.emotion_deltas.items():
                new_value = self.state_machine.apply_delta(
                    source, target, emotion_type, delta,
                    decay_per_episode=rule.decay_per_episode,
                )
                signal = EmotionalSignal(
                    source=source,
                    target=target,
                    emotion_type=emotion_type,
                    value=new_value,
                    confidence=1.0,  # ルールベースは確定値
                    evidence_span=event.event_id,  # 根拠として event_id を記録
                    episode_id=f"ep{event.episode}",
                    cause=event.event_type.value,
                )
                signals.append(signal)
                logger.debug(
                    "Rule %s applied: %s -> %s [%s] %.3f",
                    rule.rule_id, source, target, emotion_type.value, new_value,
                )

        return signals

    # ------------------------------------------------------------------
    # Step 10: エピソード間減衰
    # ------------------------------------------------------------------
    def apply_inter_episode_decay(self, episodes_passed: int) -> None:
        """エピソード間の減衰を各ルールの decay_per_episode で適用する。

        各状態キーは起源ルールの decay_per_episode を保持しており、
        ``value *= (1 - decay) ** episodes_passed`` を適用する。

        Args:
            episodes_passed: 経過エピソード数
        """
        if episodes_passed <= 0:
            return
        # ルールがない場合は減衰率が定義されないため何もしない
        if not self.rules:
            return
        # factor=1.0 → キーごとの decay を使用するモード
        self.state_machine.decay_all(1.0, episodes_passed=episodes_passed)

    # ------------------------------------------------------------------
    # Step 9: エピソード一括処理
    # ------------------------------------------------------------------
    def process_episode(
        self,
        episode: int,
        events: List[PlotEvent],
        initial_context: Optional[PlotContext] = None,
        previous_snapshot: Optional[Dict[str, Dict[str, float]]] = None,
        previous_episode: Optional[int] = None,
    ) -> EmotionalVector:
        """エピソードのイベント列を順に処理し、最終状態を EmotionalVector で返す。

        フロー:
            1. エピソード開始時: 前回スナップショットから state_machine 復元
               (previous_episode が指定されている場合はエピソード間減衰を適用)
            2. 各イベント順に process_event
            3. エピソード終了時: state_machine.snapshot() を保存
            4. 最終状態を EmotionalVector に変換して返却

        Args:
            episode: エピソード番号
            events: 処理するイベントリスト (scene 順にソートされる)
            initial_context: 初期コンテキスト (各イベント評価時に複製して使用)
            previous_snapshot: 前回エピソード終了時のスナップショット
            previous_episode: 前回エピソード番号 (減衰計算用)

        Returns:
            エピソードの感情ベクトル
        """
        # 1. 前回スナップショットからの復元 (減衰スナップショットも復元)
        if previous_snapshot is not None:
            self.state_machine.restore(previous_snapshot)
            if previous_episode is not None and previous_episode < episode:
                # エピソード境界で 1 話分の減衰を適用
                self.apply_inter_episode_decay(episode - previous_episode)

        ctx = initial_context or PlotContext(episode=episode)

        # 2. イベント順次処理 (scene 順)
        all_signals: List[EmotionalSignal] = []
        for event in sorted(events, key=lambda e: e.scene):
            event_ctx = self._build_context(ctx, event, previous_signal_event=None)
            signals = self.process_event(event, event_ctx)
            all_signals.extend(signals)
            # 次イベントの条件評価用に previous_event_type を記録
            ctx.custom_data["previous_event_type"] = event.event_type.value

        # 3. スナップショット保存
        self._last_snapshot = self.state_machine.snapshot()

        # 4. EmotionalVector 変換
        vector = self._signals_to_vector(episode, all_signals)
        self._last_vector = vector
        return vector

    # ------------------------------------------------------------------
    # Step 13: 永続化フック
    # ------------------------------------------------------------------
    def persist_results(
        self,
        vector_store: Any,
        graph_store: Any,
        log_store: Any,
        episode: int,
    ) -> None:
        """処理結果を Vector/Graph/Log の 3 ストアに書き込む。

        Args:
            vector_store: VectorStore (upsert(namespace, key, vector))
            graph_store: GraphStore (upsert_edge(source, target, props))
            log_store: EventLogStore (append(signal))
            episode: エピソード番号

        Raises:
            RuntimeError: process_episode が未実行の場合
        """
        vector = self._last_vector
        if vector is None:
            raise RuntimeError("process_episode must be called before persist_results")

        # Vector: rule_engine ネームスペースに保存
        if vector_store is not None:
            vector_store.upsert(
                RULE_ENGINE_NAMESPACE,
                f"rule_engine:ep{episode}",
                vector,
            )

        # Graph: 各シグナルからエッジ upsert
        if graph_store is not None:
            for signal in self._iter_last_signals(vector):
                graph_store.upsert_edge(signal.source, signal.target, {
                    "affection": vector.get_value(signal.source, signal.target, EmotionType.AFFECTION),
                    "tension": vector.get_value(signal.source, signal.target, EmotionType.TENSION),
                    "fear": vector.get_value(signal.source, signal.target, EmotionType.FEAR),
                    "trust": vector.get_value(signal.source, signal.target, EmotionType.TRUST),
                    "intimacy": vector.get_value(signal.source, signal.target, EmotionType.INTIMACY),
                    "cause": signal.cause or "",
                    "episode": episode,
                })

        # Log: 各シグナルを append
        if log_store is not None:
            for signal in self._iter_last_signals(vector):
                log_store.append(signal)

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------
    def _merge_metadata(self, ctx: PlotContext, event: PlotEvent) -> PlotContext:
        """イベントの metadata をコンテキストに反映する。"""
        rel = event.metadata.get("relationship_level")
        if rel is not None:
            ctx.relationship_level = float(rel)
        tension = event.metadata.get("previous_tension")
        if tension is not None:
            ctx.previous_tension = float(tension)
        return ctx

    def _build_context(
        self,
        base: PlotContext,
        event: PlotEvent,
        previous_signal_event: Optional[str],
    ) -> PlotContext:
        """イベント評価用コンテキストを構築する。"""
        import copy

        ctx = copy.deepcopy(base)
        ctx.episode = event.episode
        ctx.event = event
        ctx.roles = dict(event.roles)
        # metadata から関係レベル・緊張度を取り込む
        rel = event.metadata.get("relationship_level")
        if rel is not None:
            ctx.relationship_level = float(rel)
        tension = event.metadata.get("previous_tension")
        if tension is not None:
            ctx.previous_tension = float(tension)
        return ctx

    def _signals_to_vector(self, episode: int, signals: List[EmotionalSignal]) -> EmotionalVector:
        """シグナルリストを EmotionalVector に変換する。

        計画書仕様: 「最終状態を EmotionalVector に変換して返却」
        - シグナルから cause (最後の原因イベント) を採用
        - 状態マシンの全状態 (減衰後の値を含む) を確定値として反映
          (シグナル未生成の感情も最終状態として含める)
        """
        vector = EmotionalVector(episode_id=f"ep{episode}")
        # cause 記録用: シグナルの最後の原因を採用
        for signal in signals:
            key = signal.full_key
            if signal.cause:
                vector.causes[key] = signal.cause
        # 状態マシンの全状態を反映 (減衰のみで変化した感情も含む)
        for (source, target, emo), value in self.state_machine.items():
            key = (source, target, emo)
            vector.signals[key] = value
            vector.confidences[key] = 1.0
        vector.metadata = {"source": "rule_engine", "num_signals": len(signals)}
        return vector

    def _iter_last_signals(self, vector: EmotionalVector):
        """ベクトルからシグナルを再構築してイテレートする。"""
        for (source, target, emo), value in vector.signals.items():
            yield EmotionalSignal(
                source=source,
                target=target,
                emotion_type=emo,
                value=value,
                confidence=vector.confidences.get((source, target, emo), 1.0),
                evidence_span="",
                episode_id=vector.episode_id,
                cause=vector.causes.get((source, target, emo)),
            )

    # ------------------------------------------------------------------
    # アクセサ
    # ------------------------------------------------------------------
    @property
    def last_snapshot(self) -> Optional[Dict[str, Dict[str, float]]]:
        """直近の process_episode で保存されたスナップショット。"""
        return getattr(self, "_last_snapshot", None)

    @property
    def last_vector(self) -> Optional[EmotionalVector]:
        """直近の process_episode で生成されたベクトル。"""
        return self._last_vector


__all__ = ["RuleEngine", "RULE_ENGINE_NAMESPACE"]
