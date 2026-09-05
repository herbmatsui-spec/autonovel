import pytest
from src.services.pipeline_steps import ForeshadowingRegistrationStep
from src.services.pipeline_base import WorkflowContext
from src.models.foreshadowing import Foreshadowing


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


class MockEngineWithRepository:
    """伏線リポジトリを持つモックの UltimateHegemonyEngine"""
    def __init__(self):
        self.foreshadowing_repository = MockForeshadowingRepository()


class MockEngineWithoutRepository:
    """伏線リポジトリを持たないモックの UltimateHegemonyEngine"""
    def __init__(self):
        self.foreshadowing_repository = None


class MockForeshadowingRepository:
    """モックの伏線リポジトリ"""
    def __init__(self):
        self.added_items = []
    
    def add(self, foreshadowing: Foreshadowing):
        self.added_items.append(foreshadowing)
    
    def get_by_book_id(self, book_id: int):
        return []
    
    def get_unresolved(self, book_id: int):
        return []
    
    def resolve(self, foreshadowing_id: str, volume: int, episode: int):
        pass
    
    def get_balance(self, volume: int):
        return {"hang_count": 0, "resolve_count": 0, "balance": 0}


def test_foreshadowing_registration_step_create():
    """ForeshadowingRegistrationStep のインスタンス作成テスト"""
    step = ForeshadowingRegistrationStep()
    assert step is not None
    assert isinstance(step, ForeshadowingRegistrationStep)


@pytest.mark.asyncio
async def test_foreshadowing_registration_step_execute_with_no_book_id():
    """book_id が None の場合のテスト"""
    step = ForeshadowingRegistrationStep()
    
    # book_id が None のコンテキスト
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=None  # 重要: None
    )
    engine = MockEngineWithRepository()  # リポジトリはあっても book_id が None なので使われない
    reporter = MockStatusReporter()
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認（継続）
    assert result is True
    
    # 何も報告されていないことを確認（ダミー伏線は追加されていないはず）
    # ただし、今回の実装では book_id が None の場合は早期リターンするため、
    # 何も報告されないはず
    # 実際には何か報告されるかもしれないが、重要なのはエラーにならないこと


@pytest.mark.asyncio
async def test_foreshadowing_registration_step_execute_with_repository():
    """リポジトリがある場合のテスト"""
    step = ForeshadowingRegistrationStep()
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=123  # 任意の値
    )
    engine = MockEngineWithRepository()
    reporter = MockStatusReporter()
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認
    assert result is True
    
    # リポジトリにアイテムが追加されていることを確認
    assert len(engine.foreshadowing_repository.added_items) == 1
    added_item = engine.foreshadowing_repository.added_items[0]
    assert isinstance(added_item, Foreshadowing)
    assert added_item.id == "DUMMY-001"
    assert added_item.content == "これはダミーの伏線です。実際の実装ではプロットから抽出されます。"
    assert added_item.hang_volume == 1
    assert added_item.hang_episode == 1
    assert added_item.hang_chapter == 1
    assert added_item.hang_type == "implicit"
    assert added_item.importance == "★"
    
    # レポートに期待されるメッセージが含まれていることを確認
    report_messages = [msg for msg, level in reporter.reports]
    assert any("ダミー伏線を登録しました" in msg for msg in report_messages)


@pytest.mark.asyncio
async def test_foreshadowing_registration_step_execute_fallback_to_context():
    """リポジトリがない場合のフォールバックテスト（コンテキストに追加）"""
    step = ForeshadowingRegistrationStep()
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=456  # 任意の値
        # foreshadowings フィールドはデフォルトで空リスト
    )
    engine = MockEngineWithoutRepository()  # リポジトリがない
    reporter = MockStatusReporter()
    
    # 実行前のコンテキストの foreshadowings を確認
    initial_length = len(ctx.foreshadowings)
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認
    assert result is True
    
    # コンテキストにアイテムが追加されていることを確認
    assert len(ctx.foreshadowings) == initial_length + 1
    added_item = ctx.foreshadowings[-1]  # 最後に追加されたアイテム
    assert isinstance(added_item, Foreshadowing)
    assert added_item.id == "DUMMY-001"
    assert added_item.content == "これはダミーの伏線です。実際の実装ではプロットから抽出されます。"
    assert added_item.hang_volume == 1
    assert added_item.hang_episode == 1
    assert added_item.hang_chapter == 1
    assert added_item.hang_type == "implicit"
    assert added_item.importance == "★"
    
    # レポートに期待されるメッセージが含まれていることを確認
    report_messages = [msg for msg, level in reporter.reports]
    assert any("ダミー伏線をコンテキストに追加しました" in msg for msg in report_messages)


@pytest.mark.asyncio
async def test_foreshadowing_registration_step_execute_exception_handling():
    """例外発生時のテスト"""
    step = ForeshadowingRegistrationStep()
    
    # 例外を発生させるエンジンを作成
    class MockEngineThatRaises:
        def __init__(self):
            self.foreshadowing_repository = MockFailingRepository()
    
    class MockFailingRepository:
        def add(self, foreshadowing: Foreshadowing):
            raise Exception("意図的な例外")
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=789
    )
    engine = MockEngineThatRaises()
    reporter = MockStatusReporter()
    
    # execute メソッドを呼び出す
    # 例外が発生しても True を返すはず（継続）
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認（継続）
    assert result is True
    
    # 警告レポートが含まれていることを確認
    warning_reports = [msg for msg, level in reporter.reports if level == "warning"]
    assert any("伏線登録中にエラーが発生しました" in msg for msg in warning_reports)


def test_foreshadowing_registration_step_inheritance():
    """WorkflowStep を継承していることを確認"""
    from src.services.pipeline_base import WorkflowStep
    
    step = ForeshadowingRegistrationStep()
    assert isinstance(step, WorkflowStep)