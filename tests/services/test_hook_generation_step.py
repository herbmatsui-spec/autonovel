import pytest
from src.services.pipeline_steps import HookGenerationStep
from src.services.pipeline_base import WorkflowContext


class MockStatusReporter:
    """モックの StatusReporter"""
    def __init__(self):
        self.reports = []
        self._should_stop = False
    
    def report(self, message, level="info"):
        self.reports.append((message, level))
    
    def update_progress(self, current, total, message):
        pass
    
    @property
    def state(self):
        class State:
            def should_stop(self):
                return self._should_stop
        return State()


class MockEngine:
    """モックの UltimateHegemonyEngine"""
    def __init__(self):
        pass


@pytest.mark.asyncio
async def test_hook_generation_step_create():
    """HookGenerationStep のインスタンス作成テスト"""
    step = HookGenerationStep()
    assert step is not None
    assert isinstance(step, HookGenerationStep)


@pytest.mark.asyncio
async def test_hook_generation_step_execute():
    """HookGenerationStep.execute の基本動作テスト"""
    step = HookGenerationStep()
    
    # モックオブジェクトを作成
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000
    )
    engine = MockEngine()
    reporter = MockStatusReporter()
    
    # execute メソッドを呼び出す
    # 骨格実装なので常に True を返すはず
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認
    assert result is True
    
    # 特にエラーが発生していないことを確認
    # （エラーが発生した場合は例外が送出される）


@pytest.mark.asyncio
async def test_hook_generation_step_execute_with_none_values():
    """None 値でもエラーにならないことを確認"""
    step = HookGenerationStep()
    
    # None や空の値でも動作することを確認
    ctx = WorkflowContext(
        genre="",
        keywords="",
        archetype_key="",
        target_eps=0,
        initial_limit=0,
        word_count=0
    )
    engine = MockEngine()
    reporter = MockStatusReporter()
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認
    assert result is True


def test_hook_generation_step_inheritance():
    """WorkflowStep を継承していることを確認"""
    from src.services.pipeline_base import WorkflowStep
    
    step = HookGenerationStep()
    assert isinstance(step, WorkflowStep)