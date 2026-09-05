import pytest
from src.services.pipeline_steps import ForeshadowingResolutionStep
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
        self.stored_foreshadowings = {}  # book_id -> List[Foreshadowing]
        self.updated_foreshadowings = []  # 更新された伏線のリスト
    
    def add(self, foreshadowing: Foreshadowing):
        # 簡易実装: 実際のブックID計算に合わせる
        book_id = foreshadowing.hang_volume * 1000 + foreshadowing.hang_episode
        if book_id not in self.stored_foreshadowings:
            self.stored_foreshadowings[book_id] = []
        self.stored_foreshadowings[book_id].append(foreshadowing)
    
    def get_by_book_id(self, book_id: int):
        return self.stored_foreshadowings.get(book_id, []).copy()
    
    def get_unresolved(self, book_id: int):
        foreshadowings = self.stored_foreshadowings.get(book_id, [])
        unresolved = [
            fs for fs in foreshadowings
            if fs.resolution_volume is None and fs.resolution_episode is None
        ]
        return unresolved.copy()
    
    def resolve(self, foreshadowing_id: str, volume: int, episode: int):
        # 簡易実装: 実際のロジックに合わせる
        # すべての書籍を検索
        for book_id, foreshadowings in self.stored_foreshadowings.items():
            for fs in foreshadowings:
                if fs.id == foreshadowing_id:
                    fs.resolution_volume = volume
                    fs.resolution_episode = episode
                    self.updated_foreshadowings.append(fs)
                    return
    
    def get_balance(self, volume: int):
        hang_count = 0
        resolve_count = 0
        
        # すべての書籍を検索
        for foreshadowings in self.stored_foreshadowings.values():
            for fs in foreshadowings:
                if fs.hang_volume == volume:
                    hang_count += 1
                    if fs.resolution_volume is not None and fs.resolution_episode is not None:
                        resolve_count += 1
        
        balance = hang_count - resolve_count
        
        return {
            "hang_count": hang_count,
            "resolve_count": resolve_count,
            "balance": balance
        }


def test_foreshadowing_resolution_step_create():
    """ForeshadowingResolutionStep のインスタンス作成テスト"""
    step = ForeshadowingResolutionStep()
    assert step is not None
    assert isinstance(step, ForeshadowingResolutionStep)


@pytest.mark.asyncio
async def test_foreshadowing_resolution_step_execute_no_book_id():
    """book_id が None の場合のテスト"""
    step = ForeshadowingResolutionStep()
    
    # book_id が None のコンテキスト
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=None,  # 重要: None
        current_volume=1,
        current_episode=1
    )
    engine = MockEngineWithRepository()
    reporter = MockStatusReporter()
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認（継続）
    assert result is True
    
    # 特にエラーが発生していないことを確認
    # 何も報告されていないことを確認（早期リターンのため）
    # 警報や情報が報告されていないことを確認する必要はない


@pytest.mark.asyncio
async def test_foreshadowing_resolution_step_execute_no_volume_episode():
    """巻数または話数が設定されていない場合のテスト"""
    step = ForeshadowingResolutionStep()
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=123,
        current_volume=0,  # 重要: 0 または負の値
        current_episode=1
    )
    engine = MockEngineWithRepository()
    reporter = MockStatusReporter()
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認（継続）
    assert result is True
    
    # 警告レポートが含まれていることを確認
    warning_reports = [msg for msg, level in reporter.reports if level == "warning"]
    assert any("巻数または話数が設定されていないため" in msg for msg in warning_reports)


@pytest.mark.asyncio
async def test_foreshadowing_resolution_step_execute_with_repository_no_matches():
    """リポジトリがあるが一致する伏線がない場合のテスト"""
    step = ForeshadowingResolutionStep()
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=123,
        current_volume=5,  # 存在しない巻話
        current_episode=3
    )
    engine = MockEngineWithRepository()
    reporter = MockStatusReporter()
    
    # 事前にいくつかの伏線を追加しておく（異なる巻話）
    fs1 = Foreshadowing(
        id="F-001",
        content="伏線1",
        hang_volume=1,
        hang_episode=1,
        hang_chapter=1,
        hang_type="implicit",
        importance="★"
    )
    fs2 = Foreshadowing(
        id="F-002",
        content="伏線2",
        hang_volume=2,
        hang_episode=2,
        hang_chapter=2,
        hang_type="explicit",
        importance="★★",
        resolution_volume=3,
        resolution_episode=1
    )
    engine.foreshadowing_repository.add(fs1)
    engine.foreshadowing_repository.add(fs2)
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認（継続）
    assert result is True
    
    # 情報レポートが含まれていることを確認
    info_reports = [msg for msg, level in reporter.reports if level == "info"]
    assert any("解決対象の伏線が見つかりませんでした" in msg for msg in info_reports)
    
    # 伏線に変更がないことを確認
    assert len(engine.foreshadowing_repository.updated_foreshadowings) == 0


@pytest.mark.asyncio
async def test_foreshadowing_resolution_step_execute_with_repository_has_matches():
    """リポジトリがあり一致する伏線がある場合のテスト"""
    step = ForeshadowingResolutionStep()
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=123,
        current_volume=3,
        current_episode=2
    )
    engine = MockEngineWithRepository()
    reporter = MockStatusReporter()
    
    # 事前にいくつかの伏線を追加しておく
    # 一致する伏線（未解決）
    fs1 = Foreshadowing(
        id="F-001",
        content="解決対象の伏線",
        hang_volume=3,
        hang_episode=2,
        hang_chapter=5,
        hang_type="implicit",
        importance="★★"
    )
    # 一致しない伏線（異なる巻話）
    fs2 = Foreshadowing(
        id="F-002",
        content="他の巻話の伏線",
        hang_volume=2,
        hang_episode=2,
        hang_chapter=3,
        hang_type="reader_task",
        importance="★"
    )
    # 既に解決済みの伏線
    fs3 = Foreshadowing(
        id="F-003",
        content="既に解決済みの伏線",
        hang_volume=3,
        hang_episode=2,
        hang_chapter=3,
        hang_type="implicit",
        importance="★",
        resolution_volume=4,
        resolution_episode=2
    )
    
    engine.foreshadowing_repository.add(fs1)
    engine.foreshadowing_repository.add(fs2)
    engine.foreshadowing_repository.add(fs3)
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)

    # 結果が True であることを確認（継続）
    assert result is True

    # 情報レポートが含まれていることを確認
    info_reports = [msg for msg, level in reporter.reports if level == "info"]
    assert any("1件の伏線を解決済みとしてマークしました" in msg for msg in info_reports)
    assert any("(巻3話2)" in msg for msg in info_reports)

    # 正しく1件の伏線が更新されていることを確認
    assert len(engine.foreshadowing_repository.updated_foreshadowings) == 1
    updated_fs = engine.foreshadowing_repository.updated_foreshadowings[0]
    assert updated_fs.id == "F-001"
    assert updated_fs.resolution_volume == 3
    assert updated_fs.resolution_episode == 2


@pytest.mark.asyncio
async def test_foreshadowing_resolution_step_execute_fallback_to_context_no_matches():
    """リポジトリがない場合のフォールバックテスト（一致する伏線がない場合）"""
    step = ForeshadowingResolutionStep()
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=123,
        current_volume=5,  # 存在しない巻話
        current_episode=3,
        foreshadowings=[]  # 空のリストで初期化
    )
    engine = MockEngineWithoutRepository()
    reporter = MockStatusReporter()
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認（継続）
    assert result is True
    
    # 情報レポートが含まれていることを確認
    info_reports = [msg for msg, level in reporter.reports if level == "info"]
    assert any("解決対象の伏線が見つかりませんでした" in msg for msg in info_reports)
    
    # コンテキストに変更がないことを確認
    assert len(ctx.foreshadowings) == 0


@pytest.mark.asyncio
async def test_foreshadowing_resolution_step_execute_fallback_to_context_has_matches():
    """リポジトリがない場合のフォールバックテスト（一致する伏線がある場合）"""
    step = ForeshadowingResolutionStep()
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=123,
        current_volume=2,
        current_episode=4,
        foreshadowings=[  # 初期値としていくつかの伏線を設定
            Foreshadowing(
                id="F-001",
                content="解決対象の伏線",
                hang_volume=2,
                hang_episode=4,
                hang_chapter=7,
                hang_type="implicit",
                importance="★"
            ),
            Foreshadowing(
                id="F-002",
                content="他の巻話の伏線",
                hang_volume=3,
                hang_episode=1,
                hang_chapter=3,
                hang_type="reader_task",
                importance="★★"
            ),
            Foreshadowing(
                id="F-003",
                content="同じ巻話だが異なるエピソードの伏線",
                hang_volume=2,
                hang_episode=5,
                hang_chapter=8,
                hang_type="explicit",
                importance="★★★",
                resolution_volume=2,
                resolution_episode=6  # 既に解決済み
            )
        ]
    )
    engine = MockEngineWithoutRepository()
    reporter = MockStatusReporter()
    
    # 実行前の未解決伏線の数を確認
    initial_unresolved = [
        fs for fs in ctx.foreshadowings
        if fs.resolution_volume is None and fs.resolution_episode is None
    ]
    assert len(initial_unresolved) == 2  # F-001 と F-002
    
    # execute メソッドを呼び出す
    result = await step.execute(ctx, engine, reporter)
    
    # 結果が True であることを確認（継続）
    assert result is True
    
    # 情報レポートが含まれていることを確認
    info_reports = [msg for msg, level in reporter.reports if level == "info"]
    assert any("1件の伏線を解決済みとしてマークしました" in msg for msg in info_reports)
    assert any("(巻2話4)" in msg for msg in info_reports)
    
    # 正しく1件の伏線が更新されていることを確認
    updated_count = [
        fs for fs in ctx.foreshadowings
        if fs.resolution_volume == 2 and fs.resolution_episode == 4
    ]
    assert len(updated_count) == 1
    assert updated_count[0].id == "F-001"


@pytest.mark.asyncio
async def test_foreshadowing_resolution_step_execute_exception_handling():
    """例外発生時のテスト"""
    step = ForeshadowingResolutionStep()
    
    # 例外を発生させるエンジンを作成
    class MockEngineThatRaises:
        def __init__(self):
            self.foreshadowing_repository = MockFailingRepository()
    
    class MockFailingRepository:
        def get_unresolved(self, book_id: int):
            raise Exception("意図的な例外")
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        book_id=123,
        current_volume=1,
        current_episode=1
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
    assert any("伏線解決中にエラーが発生しました" in msg for msg in warning_reports)


def test_foreshadowing_resolution_step_inheritance():
    """WorkflowStep を継承していることを確認"""
    from src.services.pipeline_base import WorkflowStep
    
    step = ForeshadowingResolutionStep()
    assert isinstance(step, WorkflowStep)