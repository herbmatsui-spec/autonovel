"""開発者向けデバッグCLI (Week 2 Step 20)。

感情状態・グラフ・ログを確認するコマンドラインツール。

CLI 使用例::

    python -m src.rules.debug_cli show-state --episode 15 --pair A B
    python -m src.rules.debug_cli show-graph-path --source A --target B
    python -m src.rules.debug_cli show-log --pair A B --from 10 --to 15
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from src.rules.rule_loader import DEFAULT_EVENTS_PATH, DEFAULT_RULES_PATH
from src.rules.state_machine import EmotionalStateMachine
from src.stores.event_log import DEFAULT_LOG_PATH, EventLogStore
from src.stores.graph_store import InMemoryGraphStore


def _rebuild_state(episode: int, log_path: str = DEFAULT_LOG_PATH) -> EmotionalStateMachine:
    """指定エピソードまでの状態をログから再構築する。"""
    log_store = EventLogStore(log_path)
    return log_store.replay_to_episode(episode)


def show_state(
    episode: int,
    pair: Optional[tuple[str, str]] = None,
    log_path: str = DEFAULT_LOG_PATH,
) -> dict:
    """指定エピソード時点の感情状態を表示する。

    Args:
        episode: エピソード番号
        pair: (source, target) ペア (None なら全件)
        log_path: イベントログパス

    Returns:
        状態辞書::

            {"A->B": {"affection": -0.6, ...}, ...}
    """
    sm = _rebuild_state(episode, log_path)
    if pair is not None:
        state = sm.get_state(pair[0], pair[1])
        return {f"{pair[0]}->{pair[1]}": state}
    return sm.snapshot()


def show_graph_path(
    source: str,
    target: str,
    max_hops: int = 3,
    log_path: str = DEFAULT_LOG_PATH,
) -> list[dict]:
    """指定ペア間の因果パスを表示する。

    ログからグラフを再構築してパスを探索する。

    Args:
        source: 開始キャラクター名
        target: 終了キャラクター名
        max_hops: 最大ホップ数
        log_path: イベントログパス

    Returns:
        パス上のエッジ情報リスト
    """
    # ログから InMemoryGraphStore を再構築
    graph = InMemoryGraphStore()
    log_store = EventLogStore(log_path)
    for entry in log_store.query():
        graph.upsert_edge(entry.source, entry.target, {
            "affection": 0.0,
            "tension": 0.0,
            "fear": 0.0,
            "trust": 0.0,
            "intimacy": 0.0,
            "cause": entry.cause or "",
            "episode": log_store._extract_episode(entry.episode_id) or 0,
        })
    return graph.query_causal_path(source, target, max_hops=max_hops)


def show_log(
    pair: Optional[tuple[str, str]] = None,
    from_ep: int = 0,
    to_ep: int = 10**9,
    log_path: str = DEFAULT_LOG_PATH,
) -> list[dict]:
    """イベントログを表示する。

    Args:
        pair: (source, target) ペア (None なら全件)
        from_ep: 開始エピソード番号 (含む)
        to_ep: 終了エピソード番号 (含む)
        log_path: イベントログパス

    Returns:
        シグナルエントリのリスト
    """
    log_store = EventLogStore(log_path)
    signals = log_store.query(pair=pair, from_ep=from_ep, to_ep=to_ep)
    return [
        {
            "source": s.source,
            "target": s.target,
            "emotion_type": s.emotion_type.value,
            "value": s.value,
            "episode_id": s.episode_id,
            "cause": s.cause,
        }
        for s in signals
    ]


def main(argv: Optional[list[str]] = None) -> int:
    """CLI エントリポイント。"""
    parser = argparse.ArgumentParser(
        prog="python -m src.rules.debug_cli",
        description="感情状態キャッシュ デバッグCLI",
    )
    sub = parser.add_subparsers(dest="command")

    # show-state
    p_state = sub.add_parser("show-state", help="指定エピソード時点の感情状態を表示")
    p_state.add_argument("--episode", type=int, required=True, help="エピソード番号")
    p_state.add_argument("--pair", nargs=2, metavar=("SOURCE", "TARGET"),
                         help="ペア指定 (省略時は全件)")
    p_state.add_argument("--log", dest="log_path", default=DEFAULT_LOG_PATH)

    # show-graph-path
    p_graph = sub.add_parser("show-graph-path", help="ペア間の因果パスを表示")
    p_graph.add_argument("--source", required=True, help="開始キャラクター名")
    p_graph.add_argument("--target", required=True, help="終了キャラクター名")
    p_graph.add_argument("--max-hops", type=int, default=3, help="最大ホップ数")
    p_graph.add_argument("--log", dest="log_path", default=DEFAULT_LOG_PATH)

    # show-log
    p_log = sub.add_parser("show-log", help="イベントログを表示")
    p_log.add_argument("--pair", nargs=2, metavar=("SOURCE", "TARGET"),
                       help="ペア指定 (省略時は全件)")
    p_log.add_argument("--from", dest="from_ep", type=int, default=0, help="開始エピソード")
    p_log.add_argument("--to", dest="to_ep", type=int, default=10**9, help="終了エピソード")
    p_log.add_argument("--log", dest="log_path", default=DEFAULT_LOG_PATH)

    args = parser.parse_args(argv)
    if args.command == "show-state":
        pair = tuple(args.pair) if args.pair else None
        result = show_state(args.episode, pair=pair, log_path=args.log_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "show-graph-path":
        result = show_graph_path(args.source, args.target, max_hops=args.max_hops,
                                 log_path=args.log_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "show-log":
        pair = tuple(args.pair) if args.pair else None
        result = show_log(pair=pair, from_ep=args.from_ep, to_ep=args.to_ep,
                          log_path=args.log_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
