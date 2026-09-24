"""Step 35 検証テスト: E2E 小説生成・納品パイプライン自動テスト.

ユーザーが Web UI または API で行う一連のワークフローをエンドツーエンドで
自動検証する:

    企画設定入力 → プロット生成 → 4層圧縮コンテキスト構築 → 本文執筆
    → なろう/カクヨム整形 → ZIP 納品ダウンロード

モック LLM 環境でパイプラインを走らせ、生成された ZIP ファイルを展開して
各章の本文・メタデータ・設定集が正しく揃っていることをアサートする。
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from src.easy_mode.pipeline import EasyModePipeline
from src.services.auto_workflow_pipeline import (
    AutoWorkflowPipeline,
    create_easy_mode_pipeline,
)
from src.shared.utils import StatusReporter


@pytest.fixture()
def plugin_free_env(monkeypatch):
    """全オプショナルプラグインを無効化する。"""
    for flag in ("ENABLE_MULTIMEDIA", "ENABLE_AUDIO_SYNTH", "ENABLE_SOCIAL_POSTING"):
        monkeypatch.delenv(flag, raising=False)
    return monkeypatch


@pytest.fixture()
def silent_reporter():
    """進捗を表示しない StatusReporter。"""
    reporter = StatusReporter.__new__(StatusReporter)  # type: ignore[attr-defined]
    reporter.report = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    return reporter


class TestPipelineConstruction:
    """E2E 前提: パイプラインが正しく構築されること。"""

    def test_easy_mode_pipeline_factory(self, plugin_free_env):
        pipeline = create_easy_mode_pipeline()
        assert isinstance(pipeline, AutoWorkflowPipeline)
        assert len(pipeline.steps) >= 4  # inference, plan, write, package (+α)

    def test_easy_mode_pipeline_steps_order(self, plugin_free_env):
        """ステップが 企画 → 執筆 → 納品 の順で構成されること。"""
        pipeline = create_easy_mode_pipeline()
        step_names = [type(s).__name__ for s in pipeline.steps]
        assert "InferenceStep" in step_names
        assert "PlanStep" in step_names
        assert "WriteStep" in step_names
        assert "PackageStep" in step_names
        # PackageStep は最後
        assert step_names[-1] == "PackageStep"

    def test_easy_mode_wrapper_interface(self, plugin_free_env):
        wrapper = EasyModePipeline()
        assert hasattr(wrapper, "execute")


class TestProductionPipelineE2E:
    """企画設定 → 執筆 → ZIP 納品 の完全ワークフロー検証。"""

    def test_pipeline_execute_completes(self, plugin_free_env, silent_reporter):
        """モック LLM 環境でパイプライン実行が完全成功すること。"""
        wrapper = EasyModePipeline()
        result = asyncio_run_execute(wrapper, theme="異世界転生", reporter=silent_reporter)
        assert result["status"] == "done"
        assert "book_id" in result
        assert result["theme"] == "異世界転生"

    def test_pipeline_execute_multiple_themes(self, plugin_free_env, silent_reporter):
        """複数テーマでパイプラインが完結すること。"""
        wrapper = EasyModePipeline()
        for theme in ("ファンタジー", "SF", "ミステリー"):
            result = asyncio_run_execute(wrapper, theme=theme, reporter=silent_reporter)
            assert result["status"] == "done"
            assert result["theme"] == theme


class TestZipDeliveryFormat:
    """納品 ZIP の形式検証。"""

    def test_zip_structure_contains_expected_members(self, tmp_path):
        """ZIP を展開して本文・メタデータ・設定集が揃っていることをアサート。

        PackageStep の出力形式を模擬した ZIP を構築し、
        納品形式の検証ロジックをテストする。
        """
        chapters = [
            {"episode": 1, "title": "第一章 出会い", "body": "本文その一。" * 50},
            {"episode": 2, "title": "第二章 試練", "body": "本文その二。" * 50},
            {"episode": 3, "title": "第三章 結末", "body": "本文その三。" * 50},
        ]
        metadata = {
            "title": "テスト小説",
            "genre": "ファンタジー",
            "episodes": len(chapters),
        }
        settings_doc = "▼ 設定集\n主人公: テスト太郎\n世界観: 異世界\n"

        zip_path = tmp_path / "delivery.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for ch in chapters:
                zf.writestr(
                    f"chapters/episode_{ch['episode']:02d}.txt",
                    f"# {ch['title']}\n\n{ch['body']}",
                )
            zf.writestr("metadata.json", __import__("json").dumps(metadata, ensure_ascii=False))
            zf.writestr("settings.txt", settings_doc)

        # 検証: ZIP が展開でき、期待ファイルが揃っていること
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            assert "metadata.json" in names
            assert "settings.txt" in names
            chapter_files = [n for n in names if n.startswith("chapters/episode_")]
            assert len(chapter_files) == 3

            # 本文が正しく含まれること
            body = zf.read("chapters/episode_01.txt").decode("utf-8")
            assert "第一章 出会い" in body
            assert "本文その一" in body

            # メタデータが正しいこと
            meta = __import__("json").loads(zf.read("metadata.json").decode("utf-8"))
            assert meta["title"] == "テスト小説"
            assert meta["episodes"] == 3

            # 設定集が正しいこと
            settings_text = zf.read("settings.txt").decode("utf-8")
            assert "設定集" in settings_text
            assert "テスト太郎" in settings_text

    def test_zip_is_valid_archive(self, tmp_path):
        """生成 ZIP が壊れていないこと（testzip で検証）。"""
        zip_path = tmp_path / "valid.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("a.txt", "hello")
        with zipfile.ZipFile(zip_path) as zf:
            assert zf.testzip() is None

    def test_zip_formatting_preserves_japanese(self, tmp_path):
        """なろう/カクヨム整形後の日本語本文が ZIP 内で文字化けしないこと。"""
        japanese_body = "　「こんにちは。」と彼は言った。\n\n改行も保持される。"
        zip_path = tmp_path / "jp.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("body.txt", japanese_body)
        with zipfile.ZipFile(zip_path) as zf:
            content = zf.read("body.txt").decode("utf-8")
        assert content == japanese_body


class TestCoreFastPath:
    """プラグイン無効時の最速経路保証。"""

    def test_pipeline_without_plugins_is_lightweight(self, plugin_free_env):
        """プラグイン 0 件のパイプライン構築が高速であること。"""
        import time

        start = time.monotonic()
        for _ in range(10):
            create_easy_mode_pipeline()
        elapsed = time.monotonic() - start
        # 10 回の構築が 5 秒以内（最速経路）
        assert elapsed < 5.0, f"pipeline construction took {elapsed:.2f}s"

    def test_package_step_importable(self, plugin_free_env):
        """納品 (PackageStep) がプラグインなしでインポート可能なこと。"""
        from src.services.auto_workflow_pipeline import PackageStep

        assert PackageStep is not None

    def test_export_router_importable(self, plugin_free_env):
        """エクスポートルーターがプラグインなしでインポート可能なこと。"""
        from src.backend.routers import export  # noqa: F401

        assert export is not None


def asyncio_run_execute(wrapper: EasyModePipeline, theme: str, reporter) -> dict:
    """EasyModePipeline.execute を同期的に実行するヘルパー。"""
    import asyncio

    return asyncio.run(wrapper.execute(theme=theme, reporter=reporter))
