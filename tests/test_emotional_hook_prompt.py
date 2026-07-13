"""
tests/test_emotional_hook_prompt.py
prompts/manager.py の感情起点注入ロジックの単体テスト。
"""
import pytest

from src.models.emotional_hook import EmotionalHookSpec
from src.backend.tension_curve_config import EMOTIONAL_CURVES, DEFAULT_CURVE


class DummyPromptManager:
    """build_plot_expansion_prompt の注入ロジックのみをテストするためのダミー。"""

    async def build_plot_expansion_prompt(
        self,
        book_title: str,
        ep_num: int,
        ep_info,
        past_plots,
        arcs,
        book_genre: str,
        book_id=None,
        emotional_hook=None,
        **kwargs,
    ):
        base_prompt = f"【{book_title}】第{ep_num}話\nジャンル: {book_genre}\n"
        if emotional_hook is not None:
            from prompts.plotting import EMOTIONAL_HOOK_TEMPLATE
            hook_text = EMOTIONAL_HOOK_TEMPLATE.format(
                one_line_intent=getattr(emotional_hook, "one_line_intent", str(emotional_hook)),
                target_tension_peak=getattr(emotional_hook, "target_tension_peak", 80),
            )
            base_prompt = f"{base_prompt}\n\n{hook_text}"
        return base_prompt


class TestEmotionalHookPromptInjection:
    def setup_method(self):
        self.pm = DummyPromptManager()

    def test_none_hook_returns_base_prompt_only(self):
        import asyncio
        result = asyncio.run(self.pm.build_plot_expansion_prompt(
            book_title="テストタイトル",
            ep_num=1,
            ep_info={},
            past_plots=[],
            arcs=[],
            book_genre="test",
            emotional_hook=None,
        ))
        assert "刺さり" not in result
        assert "テストタイトル" in result

    def test_hook_injected_contains_one_line_intent(self):
        import asyncio
        hook = EmotionalHookSpec(
            hook_name="catharsis",
            one_line_intent="長い苦悩の末に訪れる解放",
            target_tension_peak=85,
        )
        result = asyncio.run(self.pm.build_plot_expansion_prompt(
            book_title="テストタイトル",
            ep_num=1,
            ep_info={},
            past_plots=[],
            arcs=[],
            book_genre="test",
            emotional_hook=hook,
        ))
        assert "長い苦悩の末に訪れる解放" in result
        assert "目標tensionピーク: 85/100" in result
        assert "品質はこの感情に従属させること" in result

    def test_hook_default_tension_peak_when_none(self):
        import asyncio
        hook = EmotionalHookSpec(
            hook_name="catharsis",
            one_line_intent="テスト",
        )
        result = asyncio.run(self.pm.build_plot_expansion_prompt(
            book_title="テスト",
            ep_num=1,
            ep_info={},
            past_plots=[],
            arcs=[],
            book_genre="test",
            emotional_hook=hook,
        ))
        assert "目標tensionピーク: 80/100" in result
