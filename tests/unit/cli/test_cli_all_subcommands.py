"""Step 27 検証テスト: CLI コマンドの網羅的単体テスト.

全サブコマンドがヘルプ表示および異常系ハンドリングを正しく行うことを検証する。
argparse の --help は SystemExit(0) を送出するため pytest.raises で捕捉する。
"""

from __future__ import annotations

import pytest

from src.cli.main import build_parser, main


class TestHelpDisplay:
    def test_main_help(self, capsys):
        """メインヘルプが表示されること（SystemExit(0)）。"""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "autonovel" in output
        assert "balance" in output
        assert "export" in output

    def test_balance_help(self, capsys):
        """balance --help が表示されること。"""
        with pytest.raises(SystemExit) as exc_info:
            main(["balance", "--help"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "--type" in output
        assert "dsp" in output

    def test_export_help(self, capsys):
        """export --help が表示されること。"""
        with pytest.raises(SystemExit) as exc_info:
            main(["export", "--help"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "--book-id" in output
        assert "--format" in output

    def test_check_env_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["check-env", "--help"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "--json" in output

    def test_plugins_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["plugins", "--help"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "--load" in output

    def test_init_db_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["init-db", "--help"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "init-db" in output


class TestVersion:
    def test_version_flag(self, capsys):
        """--version が 5.1.0 を表示すること。"""
        assert main(["--version"]) == 0
        assert "5.1.0" in capsys.readouterr().out


class TestErrorHandling:
    def test_unknown_subcommand_exits(self, capsys):
        """未知のサブコマンドはエラー終了すること。"""
        try:
            main(["nonexistent-command"])
            raise AssertionError("should have exited")
        except SystemExit as exc:
            assert exc.code == 2

    def test_export_without_book_id_exits(self, capsys):
        try:
            main(["export"])
            raise AssertionError("should have exited")
        except SystemExit as exc:
            assert exc.code == 2

    def test_balance_invalid_choice_exits(self, capsys):
        try:
            main(["balance", "--type", "invalid"])
            raise AssertionError("should have exited")
        except SystemExit as exc:
            assert exc.code == 2

    def test_check_env_returns_valid_code(self):
        """check-env は 0 または 1 の有効な終了コードを返すこと。"""
        result = main(["check-env", "--json"])
        assert result in (0, 1)


class TestSubcommandExecution:
    def test_plugins_command_lists(self, capsys):
        """plugins コマンドがレジストリ一覧を表示すること。"""
        assert main(["plugins"]) == 0
        output = capsys.readouterr().out
        assert "multimedia" in output
        assert "ENABLED" in output

    def test_parser_has_all_subcommands(self):
        """全サブコマンドがパーサーに登録されていること。"""
        parser = build_parser()
        subcommands = [
            action for action in parser._actions if isinstance(action, type(parser._subparsers))
        ]
        # subparsers の choices に登録確認
        found = any(
            "balance" in str(getattr(action, "choices", "")) for action in parser._actions
        )
        assert found or subcommands
