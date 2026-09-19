"""プロットイベントファイル監視・再計算 (Week 2 Step 17、簡易版)。

プロット修正時の手動再計算コマンドを提供する。

CLI 使用例::

    python -m src.rules.watcher recompute --from 14
"""
from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import Optional

from src.rules.engine import RuleEngine
from src.rules.rule_loader import (
    DEFAULT_EVENTS_PATH,
    DEFAULT_RULES_PATH,
    RuleLoader,
    parse_episode_events,
)
from src.rules.state_machine import EmotionalStateMachine
from src.stores.event_log import DEFAULT_LOG_PATH, EventLogStore
from src.stores.graph_store import InMemoryGraphStore, KuzuGraphStore

logger = logging.getLogger(__name__)


def recompute_from_episode(
    start_ep: int,
    rules_path: str = DEFAULT_RULES_PATH,
    events_path: str = DEFAULT_EVENTS_PATH,
    log_path: str = DEFAULT_LOG_PATH,
    graph_store=None,
    vector_store=None,
) -> dict:
    """指定エピソードから再計算する。

    EventLog に記録済みの状態を start_ep の直前までリプレイし、
    その後 start_ep 以降のイベントを再処理してストアに永続化する。

    Args:
        start_ep: 再計算開始エピソード番号
        rules_path: ルールセット YAML パス
        events_path: プロットイベント YAML パス
        log_path: イベントログパス
        graph_store: GraphStore (省略時は InMemory)
        vector_store: VectorStore (省略時はスキップ)

    Returns:
        再計算結果サマリ::

            {
                "episodes_processed": [14, 15, 16],
                "num_events": 3,
                "final_vector": {...},
            }
    """
    # 1. ルール・イベントロード
    rules = RuleLoader().load_rules(rules_path)
    events_by_ep = parse_episode_events(events_path)
    engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())

    # 2. start_ep 直前までの状態をログからリプレイ
    log_store = EventLogStore(log_path)
    previous_episode = start_ep - 1
    replayed = log_store.replay_to_episode(previous_episode)
    previous_snapshot = replayed.snapshot() if len(replayed) > 0 else None

    # 3. start_ep 以降のエピソードを順に処理
    target_eps = sorted(ep for ep in events_by_ep if ep >= start_ep)
    if graph_store is None:
        graph_store = InMemoryGraphStore()

    snapshot = previous_snapshot
    prev_ep = previous_episode if previous_snapshot is not None else None
    processed: list[int] = []
    num_events = 0

    for ep in target_eps:
        vector = engine.process_episode(
            ep, events_by_ep[ep],
            previous_snapshot=snapshot,
            previous_episode=prev_ep,
        )
        engine.persist_results(vector_store, graph_store, log_store, episode=ep)
        snapshot = engine.last_snapshot
        prev_ep = ep
        processed.append(ep)
        num_events += len(events_by_ep[ep])

    result = {
        "episodes_processed": processed,
        "num_events": num_events,
        "final_vector": engine.last_vector.to_dict() if engine.last_vector else {},
    }
    logger.info("Recomputed from episode %d: %d episodes", start_ep, len(processed))
    return result


def main(argv: Optional[list[str]] = None) -> int:
    """CLI エントリポイント。"""
    parser = argparse.ArgumentParser(
        prog="python -m src.rules.watcher",
        description="プロットイベント再計算ツール (簡易版)",
    )
    sub = parser.add_subparsers(dest="command")
    recompute = sub.add_parser("recompute", help="指定エピソードから再計算")
    recompute.add_argument("--from", dest="from_ep", type=int, default=1,
                           help="再計算開始エピソード番号")
    recompute.add_argument("--rules", dest="rules_path", default=DEFAULT_RULES_PATH,
                           help="ルールセット YAML パス")
    recompute.add_argument("--events", dest="events_path", default=DEFAULT_EVENTS_PATH,
                           help="プロットイベント YAML パス")
    recompute.add_argument("--log", dest="log_path", default=DEFAULT_LOG_PATH,
                           help="イベントログ JSONL パス")
    recompute.add_argument("--graph", dest="graph_db", default=None,
                           help="Kuzu データベースパス (省略時はインメモリ)")

    args = parser.parse_args(argv)
    if args.command != "recompute":
        parser.print_help()
        return 1

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    graph_store = None
    if args.graph_db:
        graph_store = KuzuGraphStore(args.graph_db)

    result = recompute_from_episode(
        start_ep=args.from_ep,
        rules_path=args.rules_path,
        events_path=args.events_path,
        log_path=args.log_path,
        graph_store=graph_store,
    )
    print(f"Episodes processed: {result['episodes_processed']}")
    print(f"Events processed: {result['num_events']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
