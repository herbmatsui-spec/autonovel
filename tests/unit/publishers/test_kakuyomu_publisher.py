"""Step 18: カクヨムPublisher単体テスト。

架空APIエラーが出ないこと、正しい投稿画面URLと整形テキストが
返ることを検証する。
"""

import asyncio

import pytest

from src.services.publishers.kakuyomu import (
    KakuyomuCredentials,
    KakuyomuPublisher,
    create_kakuyomu_publisher,
)
from src.services.publishers.base import ValidationError


class TestKakuyomuPublisherNoExternalApi:
    """Step 16: 架空外部API撤廃のテスト。"""

    def test_no_api_base_attribute(self) -> None:
        """API_BASE属性は存在しない（api.kakuyomu.jp撤廃済み）。"""
        pub = KakuyomuPublisher()
        assert not hasattr(pub, "API_BASE") or getattr(pub, "API_BASE", None) is None

    def test_no_httpx_dependency_in_module(self) -> None:
        """モジュール内にhttpxリクエスト処理が残っていない。"""
        import inspect

        import src.services.publishers.kakuyomu as kakuyomu_module

        source = inspect.getsource(kakuyomu_module)
        assert "api.kakuyomu.jp" not in source
        assert "client.post" not in source
        assert "client.get" not in source

    def test_authenticate_without_token_succeeds(self) -> None:
        """トークンなしでも認証は成功扱い（手動投稿支援モード）。"""
        pub = KakuyomuPublisher()
        credentials = KakuyomuCredentials()
        result = asyncio.run(pub.authenticate(credentials))
        assert result is True

    def test_authenticate_with_token_succeeds(self) -> None:
        """トークンありでもHTTPリクエストなしで成功扱い。"""
        pub = KakuyomuPublisher()
        credentials = KakuyomuCredentials(api_token="dummy-token", user_id="u1")
        result = asyncio.run(pub.authenticate(credentials))
        assert result is True


class TestKakuyomuEpisodeCreationUrl:
    """Step 17: エピソード新規作成URL生成のテスト。"""

    def test_get_episode_creation_url(self) -> None:
        """正しい投稿画面URLを生成する。"""
        pub = KakuyomuPublisher()
        url = pub.get_episode_creation_url("123456")
        assert url == "https://kakuyomu.jp/works/123456/episodes/new"
        assert "episodes/new" in url

    def test_get_episode_creation_url_strips_whitespace(self) -> None:
        """work_idの前後空白は除去される。"""
        pub = KakuyomuPublisher()
        url = pub.get_episode_creation_url("  999  ")
        assert url == "https://kakuyomu.jp/works/999/episodes/new"

    def test_build_episode_handoff(self) -> None:
        """ハンドオフペイロード（URL + 整形本文）を構築する。"""
        pub = KakuyomuPublisher()
        handoff = pub.build_episode_handoff("123456", "第1話", "本文\n\r\n続き")
        assert handoff.work_id == "123456"
        assert handoff.episode_creation_url == "https://kakuyomu.jp/works/123456/episodes/new"
        assert handoff.title == "第1話"
        # 改行正規化（\r\n 除去）
        assert "\r" not in handoff.body
        assert handoff.total_characters == len(handoff.body)


class TestKakuyomuPublishHandoff:
    """publish / update_chapter のハンドオフ動作テスト。"""

    def test_publish_generates_url_without_http(self) -> None:
        """publishはHTTPリクエストなしで投稿画面URLを返す。"""
        pub = KakuyomuPublisher()
        credentials = KakuyomuCredentials()
        novel = {"work_id": "123456", "title": "テスト作品"}
        chapter = {"ep_num": 1, "title": "第1話", "content": "本文です。"}

        result = asyncio.run(pub.publish(novel, chapter, credentials))
        assert result.success is True
        assert result.url == "https://kakuyomu.jp/works/123456/episodes/new"
        assert result.metadata["work_id"] == "123456"
        assert result.metadata["body"] == "本文です。"

    def test_publish_without_work_id_raises_validation_error(self) -> None:
        """work_id欠落時はValidationError。"""
        pub = KakuyomuPublisher()
        credentials = KakuyomuCredentials()
        novel = {"title": "テスト作品"}
        chapter = {"ep_num": 1, "title": "第1話", "content": "本文です。"}

        with pytest.raises(ValidationError):
            asyncio.run(pub.publish(novel, chapter, credentials))

    def test_update_chapter_generates_url_without_http(self) -> None:
        """update_chapterはHTTPリクエストなしで投稿画面URLを返す。"""
        pub = KakuyomuPublisher()
        credentials = KakuyomuCredentials()
        chapter = {"ep_num": 2, "title": "第2話", "content": "2話目です。"}

        result = asyncio.run(pub.update_chapter("123456", chapter, credentials))
        assert result.success is True
        assert result.url == "https://kakuyomu.jp/works/123456/episodes/new"
        assert result.metadata["episode_number"] == 2

    def test_get_post_status_returns_manual_publish(self) -> None:
        """get_post_statusはHTTPリクエストなしでステータスを返す。"""
        pub = KakuyomuPublisher()
        credentials = KakuyomuCredentials()
        status = asyncio.run(pub.get_post_status("123456", credentials))
        assert status["status"] == "manual_publish"
        assert status["url"] == "https://kakuyomu.jp/works/123456"


class TestKakuyomuPublisherFactory:
    """ファクトリ関数のテスト。"""

    def test_create_kakuyomu_publisher(self) -> None:
        pub = create_kakuyomu_publisher()
        assert isinstance(pub, KakuyomuPublisher)
        assert pub.platform == "kakuyomu"
