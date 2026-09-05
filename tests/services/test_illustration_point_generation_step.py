import pytest
from src.services.pipeline_steps import IllustrationPointGenerationStep
from src.services.pipeline_base import WorkflowContext
from src.models.illustration_point import IllustrationPoint


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
        self.repo = MockRepo()


class MockRepo:
    """モックのリポジトリ"""
    def __init__(self):
        self.bible = MockBibleRepo()
        self.plot = MockPlotRepo()
        self.episode = MockEpisodeRepo()


class MockBibleRepo:
    """モックの Bible リポジトリ greco
    """
    async def get_by_book_id(self, book_id):
        return MockBible()


class MockPlotRepo:
    """モックの Plot リポジトリ"""
    async def get_all_plots(self, book_id):
        return [MockPlot() for _ in range(5)]
    
    async def get_by_book_and_number(self, book_id, number):
        return MockPlot()


class MockEpisodeRepo:
    """モックの Episode リポジトリ"""
    async def get_all_by_book_id(self, book_id):
        return [MockEpisode() for _ in range(3)]
    
    async def get_by_book_and_number(self, book_id, number):
        return MockEpisode()


class MockBible:
    """モックの Bible"""
    def __init__(self):
        self.characters = [
            MockCharacter("主人公"),
            MockCharacter("ヒロイン")
        ]


class MockCharacter:
    """モックのキャラクター"""
    def __init__(self, name):
        self.name = name


class MockPlot:
    """モックのプロット"""
    pass


class MockEpisode:
    """モックのエピソード"""
    pass


@pytest.mark.asyncio
async def test_illustration_point_generation_step_create():
    """IllustrationPointGenerationStep のインスタンス作成テスト"""
    step = IllustrationPointGenerationStep()
    assert step is not None
    assert isinstance(step, IllustrationPointGenerationStep)


@pytest.mark.asyncio
async def test_illustration_point_generation_step_execute():
    """IllustrationPointGenerationStep.execute の基本動作テスト"""
    step = IllustrationPointGenerationStep()
    
    # モックオブジェクトを作成
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        enable_illustration=True,
        illustration_settings={"enableIllustration": True},
        book_id=1
    )
    engine = MockEngine()
    reporter = MockStatusReporter()
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認
    assert result is True
    
    # illustration_points が生成されていることを確認
    assert len(ctx.illustration_points) > 0
    
    # 生成されたポイントが IllustrationPoint のインスタンスであることを確認
    for point in ctx.illustration_points:
        assert isinstance(point, IllustrationPoint)
        assert hasattr(point, 'id')
        assert hasattr(point, 'page')
        assert hasattr(point, 'scene_description')


@pytest.mark.asyncio
async def test_illustration_point_generation_step_skip_when_disabled():
    """illustration が無効の場合はスキップされることを確認"""
    step = IllustrationPointGenerationStep()
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        enable_illustration=False,  # 無効に設定
        book_id=1
    )
    engine = MockEngine()
    reporter = MockStatusReporter()
    
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認（スキップしても成功）
    assert result is True
    
    # スキップメッセージが報告されていることを確認
    skip_reports = [r for r in reporter.reports if "illustration_point:" in r[0] and "enable_illustration=False" in r[0]]
    assert len(skip_reports) > 0


@pytest.mark.asyncio
async def test_illustration_point_generation_step_skip_when_no_book_id():
    """book_id が None の場合はスキップされることを確認"""
    step = IllustrationPointGenerationStep()
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        enable_illustration=True,
        illustration_settings={"enableIllustration": True},
        book_id=None  # None に設定
    )
    engine = MockEngine()
    reporter = MockStatusReporter()
    
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認（スキップしても成功）
    assert result is True
    
    # スキップメッセージが報告されていることを確認
    skip_reports = [r for r in reporter.reports if "illustration_point:" in r[0] and "book_id is None" in r[0]]
    assert len(skip_reports) > 0


@pytest.mark.asyncio
async def test_illustration_point_generation_step_with_empty_characters():
    """キャラクター情報が空の場合でも動作することを確認"""
    step = IllustrationPointGenerationStep()
    
    # キャラクター情報が空のBibleを返すモック
    class MockEngineNoChars(MockEngine):
        def __init__(self):
            self.repo = MockRepoNoChars()
    
    class MockRepoNoChars(MockRepo):
        def __init__(self):
            self.bible = MockBibleRepoNoChars()
            self.plot = MockPlotRepo()
            self.episode = MockEpisodeRepo()
    
    class MockBibleRepoNoChars:
        async def get_by_book_id(self, book_id):
            return MockBibleNoChars()
    
    class MockBibleNoChars:
        def __init__(self):
            self.characters = []  # 空のキャラクター list
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        enable_illustration=True,
        illustration_settings={"enableIllustration": True},
        book_id=1
    )
    engine = MockEngineNoChars()
    reporter = MockStatusReporter()
    
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認
    assert result is True
    
    # 空のキャラクターでもポイントが生成されていることを確認
    assert len(ctx.illustration_points) > 0
