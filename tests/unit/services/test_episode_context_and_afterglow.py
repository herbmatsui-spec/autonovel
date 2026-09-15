"""src/services/episode_context.py と src/services/erotic_afterglow_evaluator.py の単体テスト."""

import pytest

from src.services.episode_context import EpisodeContextBuilder
from src.services.erotic_afterglow_evaluator import AfterglowEvaluator


class TestEpisodeContextBuilder:
    """EpisodeContextBuilder のテスト."""

    def setup_method(self):
        self.builder = EpisodeContextBuilder()

    def test_build_context_first_episode(self):
        ctx = self.builder.build_context(book_id=1, ep_num=1)
        assert ctx["book_id"] == 1
        assert ctx["ep_num"] == 1
        assert ctx["is_first"] is True
        assert ctx["is_last"] is False
        assert ctx["target_word_count"] == 3000

    def test_build_context_with_previous(self):
        prev = {"title": "第1話", "ending": "終わり", "summary": "要約", "key_events": ["event"]}
        ctx = self.builder.build_context(book_id=1, ep_num=2, previous_episode=prev)
        assert ctx["is_first"] is False
        assert ctx["previous_episode"]["title"] == "第1話"
        assert ctx["previous_episode"]["key_events"] == ["event"]

    def test_build_context_prev_defaults(self):
        # prev.get("title", f"第{ep_num-1}話") のデフォルトフォールバックを検証するため
        # get に渡す prev は None キーではなく、キー自体が存在しない状態にする
        prev = {"ending": "", "summary": "", "key_events": []}
        ctx = self.builder.build_context(book_id=1, ep_num=5, previous_episode=prev)
        assert ctx["previous_episode"]["title"] == "第4話"
        assert ctx["previous_episode"]["key_events"] == []

    def test_build_context_no_prev_not_first(self):
        ctx = self.builder.build_context(book_id=1, ep_num=3, previous_episode=None)
        # ヒストリー未登録のため空の概要が返る
        assert ctx["previous_episode"]["title"] == ""
        assert "ending" in ctx["previous_episode"]

    def test_history_max_10(self):
        for i in range(1, 13):
            self.builder.build_context(book_id=1, ep_num=i, previous_episode={"title": f"t{i}"})
        history = self.builder.get_history()
        assert len(history) == 10
        assert history[-1]["ep_num"] == 12
        assert history[0]["ep_num"] == 3

    def test_clear_history(self):
        self.builder.build_context(book_id=1, ep_num=1)
        self.builder.clear_history()
        assert self.builder.get_history() == []

    def test_set_final_episode(self):
        self.builder.build_context(book_id=1, ep_num=5)
        self.builder.set_final_episode(5)
        history = self.builder.get_history()
        assert history[0]["context"]["is_last"] is True

    def test_set_final_episode_not_found(self):
        self.builder.build_context(book_id=1, ep_num=1)
        self.builder.set_final_episode(99)  # 存在しないエピソード、エラーなし
        assert self.builder.get_history()[0]["context"]["is_last"] is False

    def test_get_last_episode_summary_from_history(self):
        self.builder.build_context(book_id=1, ep_num=1)
        self.builder.build_context(
            book_id=1, ep_num=2, previous_episode={"title": "T1", "ending": "E1", "summary": "S1"}
        )
        # ep3 を前話なしで生成すると ep2 の context から概要が拾われる
        self.builder._episode_history.clear()
        self.builder._episode_history.append(
            {"ep_num": 2, "context": {"previous_episode": {"title": "T1", "ending": "E1", "summary": "S1"}}}
        )
        summary = self.builder._get_last_episode_summary()
        assert summary["title"] == "T1"
        assert summary["ending"] == "E1"
        assert summary["summary"] == "S1"

    def test_get_last_episode_summary_empty_history(self):
        summary = self.builder._get_last_episode_summary()
        assert summary == {"title": "", "ending": "", "summary": ""}


class TestAfterglowEvaluator:
    """AfterglowEvaluator のテスト."""

    def setup_method(self):
        self.evaluator = AfterglowEvaluator()

    def test_count_paragraphs(self):
        text = "段落1\n\n段落2\n\n\n段落3"
        assert self.evaluator.count_paragraphs(text) == 3

    def test_count_paragraphs_empty(self):
        assert self.evaluator.count_paragraphs("") == 0

    def test_check_emotional_settling_hit(self):
        assert self.evaluator.check_emotional_settling("静けさが訪れた") is True

    def test_check_emotional_settling_miss(self):
        assert self.evaluator.check_emotional_settling("暴力的な文章") is False

    def test_check_distance_reconfirm_hit(self):
        assert self.evaluator.check_distance_reconfirm("距離を確認した") is True

    def test_check_foreshadow_hit(self):
        assert self.evaluator.check_foreshadow("次の話で明らかになる") is True

    def test_evaluate_acceptable(self):
        # 閾値: 400文字以上 / 2段落以上 / 全キーワードカテゴリを含む
        para1 = (
            "余韻に浸る二人は静けさの中で温もりを感じていた。安らぎの時間が過ぎていく。"
            "沈静の空気が漂い、穏やかな心持ちで隣り合う距離を確認する。"
            "この距離が縮まったことを確かめ、互いに寄り添う。"
            "静けさが部屋を満たし、穏やかな余韻が温もりを残して安らぎへと沈静していく。"
            "窓の外では夕闇が広がり、二人の距離が静かに縮まっていくのを実感していた。"
            "温もりが指先から伝わり、穏やかな安らぎが心を満たしていくのを感じた。"
            "静けさが漂う部屋の隅で、余韻に沈む穏やかな時間が静かに過ぎていく。"
            "温もりが残る手のひらの感触を確かめながら、安らぎの中で目を閉じた。"
        )
        para2 = (
            "次の話で明らかになる伏線がここに予感として眠っている。"
            "待ち望む結末へ続く道のりが、いま静かに始まろうとしていた。"
            "次の展開で明らかになる真実へ、読者の心は待ち望む。"
            "この伏線が明らかになる時、二人の距離はさらに近了し、"
            "新たな余韻と温もりが安らぎとして沈静するだろう。"
            "穏やかな静けさの中、次の話への期待が確かな予感となって膨らんでいく。"
            "この余韻が次話への架け橋となり、伏線は静かに記憶へと刻まれていく。"
            "読者は次の展開を心待ちにし、その結末に思いを馳せることになるだろう。"
            "物語の余韻は静かに落ち着きながらも、次の展開への伏線を確かに残している。"
        )
        text = para1 + "\n\n" + para2
        assert len(text) >= 400
        assert self.evaluator.count_paragraphs(text) >= 2
        ok, issues = self.evaluator.evaluate(text)
        assert ok is True
        assert issues == []

    def test_evaluate_insufficient(self):
        ok, issues = self.evaluator.evaluate("短い")
        assert ok is False
        assert len(issues) >= 3  # 段落・文字数・感情・距離・伏線
        assert any("段落数" in i for i in issues)
        assert any("文字数" in i for i in issues)
        assert any("沈降" in i for i in issues)
