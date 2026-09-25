"""Step 24: P1全結合検証。

企画情報入力 → 35文字キャッチコピー生成 → 本文整形
（カクヨム字下げなし＋段落分割） → 投稿用ペイロード出力の
一連のフローが完全動作することを検証する。
"""

import asyncio
import inspect

import pytest

from src.config.kakuyomu_syntax_patterns import (
    CATCHPHRASE_MAX_LENGTH,
    CATCHPHRASE_POWER_WORDS,
)
from src.services.marketing.catchphrase_scorer import score_catchphrase_ctr
from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter
from src.services.publishers.kakuyomu import (
    KakuyomuCredentials,
    KakuyomuPublisher,
)


class TestStep1ConfigLayer:
    """Step 1: 設定レイヤーの結合確認。"""

    def test_catchphrase_constants_exist(self) -> None:
        assert CATCHPHRASE_MAX_LENGTH == 35
        assert CATCHPHRASE_POWER_WORDS
        assert all(isinstance(w, str) for w in CATCHPHRASE_POWER_WORDS)


class TestStep2ScorerLayer:
    """Step 2: スコアラーレイヤーの結合確認。"""

    def test_high_ctr_catchphrase_scores(self) -> None:
        score = score_catchphrase_ctr(
            "「お前はクビだ」――そう言った元パーティが翌日全滅していた件。"
        )
        assert 0 <= score <= 100
        assert score >= 80


class TestStep10To12FormatterLayer:
    """Step 10〜12: 整形レイヤーの結合確認。"""

    def test_kakuyomu_no_indent_and_line_rhythm(self) -> None:
        res = PlatformCopyFormatter.format_for_platform(
            "第1話",
            "段落1\n\n\n\n段落2",
            platform="kakuyomu",
            indent_enabled=False,
        )
        assert not res.body.startswith("　")
        assert "\n\n\n" not in res.body
        assert res.body.count("\n\n") == 1

    def test_dense_paragraph_auto_split(self) -> None:
        res = PlatformCopyFormatter.split_dense_paragraphs("長い文。長い文。長い文。長い文。")
        assert "\n\n" in res

    def test_kakuyomu_ruby_and_bouten_preserved(self) -> None:
        res = PlatformCopyFormatter.format_for_platform(
            "T",
            "｜魔法《マジック》を使った。《《重要》》だ。",
            platform="kakuyomu",
            indent_enabled=False,
        )
        assert "|魔法《マジック》" in res.body
        assert "《《重要》》" in res.body

    def test_split_dense_paragraphs_is_static_callable(self) -> None:
        """検証コマンド互換: クラスメソッドとして直接呼び出せる。"""
        result = PlatformCopyFormatter.split_dense_paragraphs("あ。い。う。え。")
        assert isinstance(result, str)


class TestStep16To17PublisherLayer:
    """Step 16〜17: Publisherレイヤーの結合確認。"""

    def test_no_fake_api_requests(self) -> None:
        """架空API（api.kakuyomu.jp）へのHTTPリクエスト処理が撤廃されている。"""
        import src.services.publishers.kakuyomu as kakuyomu_module

        source = inspect.getsource(kakuyomu_module)
        assert "api.kakuyomu.jp" not in source
        assert "client.post" not in source

    def test_episode_creation_url_generated(self) -> None:
        pub = KakuyomuPublisher()
        url = pub.get_episode_creation_url("123456")
        assert url == "https://kakuyomu.jp/works/123456/episodes/new"
        assert "episodes/new" in url

    def test_publish_returns_handoff_payload(self) -> None:
        pub = KakuyomuPublisher()
        credentials = KakuyomuCredentials()
        novel = {"work_id": "123456", "title": "テスト作品"}
        chapter = {"ep_num": 1, "title": "第1話", "content": "本文です。"}

        result = asyncio.run(pub.publish(novel, chapter, credentials))
        assert result.success is True
        assert result.url == "https://kakuyomu.jp/works/123456/episodes/new"
        assert result.metadata["body"] == "本文です。"


class TestP1FullFlow:
    """Step 24: 企画入力 → キャッチコピー生成 → 本文整形 → 投稿ペイロードの全フロー。"""

    def test_end_to_end_kakuyomu_flow(self) -> None:
        # --- 1. 企画情報入力 ---
        project_settings = "ジャンル: 異世界ファンタジー、追放ざまぁ、実は神鑑定士"
        work_id = "123456"

        # --- 2. 35文字キャッチコピー生成＆スコアリング ---
        raw_candidates = [
            "「お前はクビだ」――そう言った元パーティが翌日全滅していた件。",
            "追放された元無能、実は世界で唯一の【神鑑定士】でした。",
            "今更戻ってこい？ もう世界最強の美少女たちと暮らしてますが？",
            "処刑されたはずの元英雄、気ままなスローライフ始めます。",
            "ただの鑑定士ですが、なぜか周囲が神だと勘違いして崇めてきます。",
        ]
        scored = sorted(
            ((c, score_catchphrase_ctr(c)) for c in raw_candidates),
            key=lambda pair: -pair[1],
        )
        # 全候補が35文字以内
        for catchphrase, score in scored:
            assert len(catchphrase) <= CATCHPHRASE_MAX_LENGTH
            assert 0 <= score <= 100
        # 最上位候補は高CTR
        best_catchphrase, best_score = scored[0]
        assert best_score >= 80

        # --- 3. 本文整形（カクヨム字下げなし＋段落分割） ---
        raw_body = (
            "「師匠、俺はまだ弱いでしょうか。」\n"
            "鑑定士は静かに首を振った。どこか悲しげだった。\n"
            "\n"
            "その夜、パーティは全滅した。彼だけが生き残った。"
            "生き残った彼は気づく。自分の力の本当の意味に。"
        )
        split_body = PlatformCopyFormatter.split_dense_paragraphs(raw_body)
        res = PlatformCopyFormatter.format_for_platform(
            "第1話 旅立ち",
            split_body,
            platform="kakuyomu",
            indent_enabled=False,
        )
        # 字下げなし
        assert not res.body.startswith("　")
        # 3連続改行なし
        assert "\n\n\n" not in res.body
        # 段落分割で空行が挿入されている
        assert "\n\n" in res.body

        # --- 4. 投稿用ペイロード出力 ---
        pub = KakuyomuPublisher()
        handoff = pub.build_episode_handoff(work_id, "第1話 旅立ち", res.body)
        assert handoff.episode_creation_url == (
            "https://kakuyomu.jp/works/123456/episodes/new"
        )
        assert handoff.body == res.body
        assert handoff.total_characters == len(res.body)

        # publish 経由でも同一ペイロードが得られる
        credentials = KakuyomuCredentials()
        result = asyncio.run(
            pub.publish(
                {"work_id": work_id, "title": "テスト作品"},
                {"ep_num": 1, "title": "第1話 旅立ち", "content": res.body},
                credentials,
            )
        )
        assert result.success is True
        assert result.metadata["body"] == res.body
        assert result.metadata["episode_creation_url"] == handoff.episode_creation_url

    def test_publish_result_via_update_chapter_flow(self) -> None:
        """第2話以降の追加フローも投稿画面URL生成で完結する。"""
        pub = KakuyomuPublisher()
        credentials = KakuyomuCredentials()

        result = asyncio.run(
            pub.update_chapter(
                "123456",
                {"ep_num": 2, "title": "第2話 鑑定", "content": "2話目の本文。"},
                credentials,
            )
        )
        assert result.success is True
        assert result.url == "https://kakuyomu.jp/works/123456/episodes/new"
        assert result.metadata["body"] == "2話目の本文。"
