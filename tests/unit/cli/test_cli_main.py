"""Step 23 検証テスト: 統一 CLI エントリポイント src.cli.main の単体テスト."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.cli.main import (  # noqa: E402
    __version__,
    build_parser,
    cmd_balance,
    cmd_check_env,
    cmd_export,
    cmd_init_db,
    cmd_plugins,
    cmd_version,
    main,
)


class TestParser:
    def test_prog_name(self):
        parser = build_parser()
        assert parser.prog == "autonovel"

    def test_subcommands_registered(self):
        parser = build_parser()
        # parse_args で各サブコマンドの func が解決されること
        # export は --book-id が必須なのでダミー値を渡す
        cases: list[tuple[str, list[str]]] = [
            ("balance", []),
            ("export", ["--book-id", "1"]),
            ("init-db", []),
            ("check-env", []),
            ("plugins", []),
        ]
        for cmd, extra in cases:
            args = parser.parse_args([cmd, *extra])
            assert hasattr(args, "func"), f"missing func for {cmd}"

    def test_version_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--version"])
        assert args.version is True

    def test_balance_type_choices(self):
        parser = build_parser()
        args = parser.parse_args(["balance", "--type", "csp"])
        assert args.type == "csp"

    def test_balance_default_type(self):
        parser = build_parser()
        args = parser.parse_args(["balance"])
        assert args.type == "dsp"

    def test_export_requires_book_id(self, capsys):
        parser = build_parser()
        try:
            parser.parse_args(["export"])
            raise AssertionError("should have exited")
        except SystemExit:
            pass  # argparse の required エラー


class TestCommands:
    def test_cmd_version(self, capsys):
        assert cmd_version(__import__("argparse").Namespace(version=True)) == 0
        output = capsys.readouterr().out
        assert __version__ in output

    def test_cmd_check_env_json(self, capsys):
        args = __import__("argparse").Namespace(json=True)
        assert cmd_check_env(args) in (0, 1)
        output = capsys.readouterr().out
        assert "ok" in output or "results" in output

    def test_cmd_plugins_lists_entries(self, capsys):
        args = __import__("argparse").Namespace(load=False)
        assert cmd_plugins(args) == 0
        output = capsys.readouterr().out
        assert "multimedia" in output

    def test_cmd_balance_unknown_type(self, capsys):
        args = __import__("argparse").Namespace(type="nonexistent")
        assert cmd_balance(args) == 1


class TestMain:
    def test_main_version(self, capsys):
        assert main(["--version"]) == 0
        assert __version__ in capsys.readouterr().out

    def test_main_no_subcommand_shows_help(self, capsys):
        assert main([]) == 0
        assert "usage" in capsys.readouterr().out.lower()

    def test_main_balance_unknown_type(self, capsys):
        """choices 外の type は argparse が SystemExit(2) でエラー終了する。"""
        try:
            main(["balance", "--type", "nonexistent"])
            raise AssertionError("should have exited")
        except SystemExit as exc:
            assert exc.code == 2

    def test_version_constant(self):
        assert __version__ == "5.1.0"
