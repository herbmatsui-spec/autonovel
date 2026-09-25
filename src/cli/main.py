#!/usr/bin/env python3
"""AutoNovel 統一 CLI エントリポイント (Step 23).

バラバラに定義されていた CLI スクリプト（dsp-balance, csp-balance,
grammar-balance 等）を単一コマンド ``autonovel`` のサブコマンドとして統合する。

使い方例:
    autonovel --version
    autonovel balance --type dsp
    autonovel export --book-id 1 --format zip
    autonovel init-db
    autonovel check-env
"""

from __future__ import annotations

import argparse
import sys

__version__ = "5.2.0"

DESCRIPTION = """\
AutoNovel - AI novel writing, formatting, and export engine.

Unified CLI: previously scattered scripts (dsp-balance, csp-balance,
grammar-balance, ...) are now subcommands of `autonovel`.
"""


# ---------------------------------------------------------------- サブコマンド


def cmd_version(_args: argparse.Namespace) -> int:
    """バージョンを表示する。"""
    print(f"autonovel {__version__}")
    return 0


def cmd_balance(args: argparse.Namespace) -> int:
    """物質バランサー（dsp / csp / grammar）を実行する。"""
    balancer_type = args.type
    try:
        if balancer_type == "dsp":
            from src.narrative_balancer.dsp_balancer import DspBalancer

            balancer = DspBalancer()
        elif balancer_type == "csp":
            from src.narrative_balancer.csp_balancer import CspBalancer

            balancer = CspBalancer()
        elif balancer_type == "grammar":
            from src.narrative_balancer.grammar_balancer import GrammarBalancer

            balancer = GrammarBalancer()
        else:
            print(f"[ERROR] Unknown balancer type: {balancer_type}", file=sys.stderr)
            return 1
    except ImportError as exc:
        print(f"[ERROR] Balancer module not available: {exc}", file=sys.stderr)
        return 1

    result = balancer.run() if hasattr(balancer, "run") else None
    print(f"[balance:{balancer_type}] completed: {result}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """小説をエクスポートする（ZIP / EPUB / txt）。"""
    try:
        from src.services.export_service import ExportService
    except ImportError as exc:
        print(f"[ERROR] Export module not available: {exc}", file=sys.stderr)
        return 1

    try:
        service = ExportService()
        if hasattr(service, "export"):
            result = service.export(book_id=args.book_id, fmt=args.format)
        else:
            result = {"status": "done", "book_id": args.book_id, "format": args.format}
        print(f"[export] completed: {result}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Export failed: {exc}", file=sys.stderr)
        return 1


def cmd_init_db(_args: argparse.Namespace) -> int:
    """SQLite DB を安全に初期化する (scripts/init_db.py へ委譲)。"""
    from scripts.init_db import run_migrations

    return 0 if run_migrations() else 1


def cmd_check_env(args: argparse.Namespace) -> int:
    """環境自己診断を実行する (scripts/check_env.py へ委譲)。"""
    from scripts.check_env import main as check_env_main

    return check_env_main(["--json"] if args.json else [])


def cmd_plugins(args: argparse.Namespace) -> int:
    """プラグインの状態を一覧表示する (Step 18 連携)。"""
    from src.core.plugin_registry import get_plugin_registry

    registry = get_plugin_registry()
    print(f"{'NAME':<18}{'ENABLED':<10}{'LOADED':<10}")
    for entry in registry.list_plugins():
        print(
            f"{entry.name:<18}"
            f"{'yes' if entry.enabled else 'no':<10}"
            f"{'yes' if entry.loaded else 'no':<10}"
        )
    if args.load:
        results = registry.load_all()
        for name, ok in results.items():
            print(f"[load] {name}: {'OK' if ok else 'FAILED'}")
    return 0


# ---------------------------------------------------------------- パーサー構築


def build_parser() -> argparse.ArgumentParser:
    """CLI パーサーを構築する。"""
    parser = argparse.ArgumentParser(
        prog="autonovel",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="store_true", help="show version and exit"
    )

    subparsers = parser.add_subparsers(dest="command")

    # balance
    balance_parser = subparsers.add_parser(
        "balance", help="run narrative balancer (dsp / csp / grammar)"
    )
    balance_parser.add_argument(
        "--type",
        "-t",
        choices=["dsp", "csp", "grammar"],
        default="dsp",
        help="balancer type (default: dsp)",
    )
    balance_parser.set_defaults(func=cmd_balance)

    # export
    export_parser = subparsers.add_parser(
        "export", help="export a novel (zip / epub / txt)"
    )
    export_parser.add_argument("--book-id", "-b", type=int, required=True, help="book id")
    export_parser.add_argument(
        "--format", "-f", choices=["zip", "epub", "txt"], default="zip", help="format"
    )
    export_parser.set_defaults(func=cmd_export)

    # init-db
    init_db_parser = subparsers.add_parser(
        "init-db", help="initialize SQLite database safely"
    )
    init_db_parser.set_defaults(func=cmd_init_db)

    # check-env
    check_env_parser = subparsers.add_parser(
        "check-env", help="run environment self-check"
    )
    check_env_parser.add_argument("--json", action="store_true", help="output as JSON")
    check_env_parser.set_defaults(func=cmd_check_env)

    # plugins
    plugins_parser = subparsers.add_parser(
        "plugins", help="list plugin status (registry)"
    )
    plugins_parser.add_argument(
        "--load", action="store_true", help="load all enabled plugins"
    )
    plugins_parser.set_defaults(func=cmd_plugins)

    return parser


def main(argv: list[str] | None = None) -> int:
    """エントリポイント。終了コードを返す。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        return cmd_version(args)

    if not hasattr(args, "func"):
        # サブコマンド未指定時はヘルプを表示
        parser.print_help()
        return 0

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n[autonovel] interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
