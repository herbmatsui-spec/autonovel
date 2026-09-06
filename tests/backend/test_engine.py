import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.backend.engine import UltimateHegemonyEngine, HookGenerationStep
from src.infrastructure.repositories.foreshadowing_repository import InMemoryForeshadowingRepository
from src.infrastructure.repositories.hook_repository import InMemoryHookRepository
from src.services.pipeline_base import WorkflowContext


class TestUltimateHegemonyEngine:
    """UltimateHegemonyEngine のテストクラス"""
    
    def test_engine_initialization_with_all_dependencies(self):
        """全ての依存関係を指定してエンジンを初期化"""
        mock_repo = Mock()
        mock_db = Mock()
        mock_llm = Mock()
        mock_cooldown = Mock()
        mock_plot_service = Mock()
        mock_foreshadowing_repo = InMemoryForeshadowingRepository()
        mock_hook_repo = InMemoryHookRepository()
        
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            repo=mock_repo,
            db=mock_db,
            llm=mock_llm,
            cooldown=mock_cooldown,
            plot_service=mock_plot_service,
            foreshadowing_repository=mock_foreshadowing_repo,
            hook_repository=mock_hook_repo,
            planner=Mock(),
            writer=Mock(),
            pm=Mock(),
            ctx_mgr=Mock(),
            formatter=Mock(),
            validator=Mock(),
            auditor=Mock(),
            narrative=Mock(),
            critique=Mock(),
            marketing=Mock(),
            bible_agent=Mock(),
            plot_agent=Mock(),
            style_rag=Mock(),
            illustration_agent=Mock()
        )
        
        assert engine.api_key == "test-key"
        assert engine.repo == mock_repo
        assert engine.db == mock_db
        assert engine.llm == mock_llm
        assert engine.cooldown == mock_cooldown
        assert engine.plot_service == mock_plot_service
        assert engine.foreshadowing_repository == mock_foreshadowing_repo
        assert engine.hook_repository == mock_hook_repo
        
    def test_engine_initialization_with_plot_service_auto_creation(self):
        """plot_service が None の場合、repo から自動生成されることを確認"""
        mock_repo = Mock()
        mock_llm = Mock()
        
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            repo=mock_repo,
            llm=mock_llm,
            plot_service=None
        )
        
        assert engine.plot_service is not None
        # PlotService が作成されることを確認（実際のクラス名は省略）
        
    def test_engine_initialization_without_plot_service_and_repo(self):
        """plot_service も repo も None の場合、plot_service が None のままになることを確認"""
        mock_llm = Mock()
        
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            llm=mock_llm,
            plot_service=None,
            repo=None
        )
        
        assert engine.plot_service is None
        
    def test_legacy_dep_raises_attribute_error_when_not_injected(self):
        """レガシー依存関係が注入されていない場合に AttributeError が発生することを確認"""
        engine = UltimateHegemonyEngine(api_key="test-key")
        
        with pytest.raises(AttributeError, match="has no lazy dependency 'planner'"):
            _ = engine.planner
            
    def test_legacy_dep_returns_correct_object_when_injected(self):
        """レガシー依存関係が注入されている場合に正しいオブジェクトを返すことを確認"""
        mock_planner = Mock()
        engine = UltimateHegemonyEngine(
            api_key="test-key",
            planner=mock_planner
        )
        
        assert engine.planner == mock_planner
        assert engine.planning_agent == mock_planner  # planning_agent も planner を参照
        
    def test_all_legacy_properties_work_when_injected(self):
        """全てのレガシープロパティが正しく動作することを確認"""
        mocks = {
            "planner": Mock(),
            "writer": Mock(),
            "pm": Mock(),
            "ctx_mgr": Mock(),
            "formatter": Mock(),
            "validator": Mock(),
            "auditor": Mock(),
            "narrative": Mock(),
            "critique": Mock(),
            "marketing": Mock(),
            "bible_agent": Mock(),
            "plot_agent": Mock(),
            "style_rag": Mock(),
            "illustration_agent": Mock()
        }
        
        engine = UltimateHegemonyEngine(api_key="test-key", **mocks)
        
        assert engine.planner == mocks["planner"]
        assert engine.planning_agent == mocks["planner"]
        assert engine.writer == mocks["writer"]
        assert engine.pm == mocks["pm"]
        assert engine.ctx_mgr == mocks["ctx_mgr"]
        assert engine.formatter == mocks["formatter"]
        assert engine.validator == mocks["validator"]
        assert engine.auditor == mocks["auditor"]
        assert engine.narrative == mocks["narrative"]
        assert engine.critique == mocks["critique"]
        assert engine.marketing == mocks["marketing"]
        assert engine.bible_agent == mocks["bible_agent"]
        assert engine.plot_agent == mocks["plot_agent"]
        assert engine.style_rag == mocks["style_rag"]
        assert engine.illustration_agent == mocks["illustration_agent"]
        
    def test_deprecated_properties_warn_and_return_llm(self):
        """非推奨プロパティが警告を出し llm を返すことを確認"""
        mock_llm = Mock()
        engine = UltimateHegemonyEngine(api_key="test-key", llm=mock_llm)
        
        with pytest.warns(FutureWarning, match="ai_api is deprecated"):
            assert engine.ai_api == mock_llm
            
        with pytest.warns(FutureWarning, match="llm_client is deprecated"):
            assert engine.llm_client == mock_llm
            
    def test_logic_validator_returns_validator(self):
        """logic_validator プロパティが validator を返すことを確認"""
        mock_validator = Mock()
        engine = UltimateHegemonyEngine(api_key="test-key", validator=mock_validator)
        
        assert engine.logic_validator == mock_validator
        
    def test_generate_json_returns_llm_generate_json(self):
        """generate_json プロパティが llm.generate_json を返すことを確認"""
        mock_llm = Mock()
        mock_llm.generate_json = Mock()
        engine = UltimateHegemonyEngine(api_key="test-key", llm=mock_llm)
        
        assert engine.generate_json == mock_llm.generate_json
        
    def test_dispose_calls_db_engine_dispose_if_exists(self):
        """dispose メソッドが db.engine.dispose() を呼び出すことを確認"""
        mock_db = Mock()
        mock_engine = Mock()
        mock_db.engine = mock_engine
        
        engine = UltimateHegemonyEngine(api_key="test-key", db=mock_db)
        engine.dispose()
        
        mock_engine.dispose.assert_called_once()
        
    def test_dispose_does_nothing_if_db_has_no_engine(self):
        """dispose メソッドが db に engine がない場合でもエラーにならないことを確認"""
        mock_db = Mock()
        del mock_db.engine  # engine 属性を削除
        
        engine = UltimateHegemonyEngine(api_key="test-key", db=mock_db)
        # 例外が発生しないことを確認
        engine.dispose()
        
    @pytest.mark.asyncio
    async def test_sync_bible_calls_bible_agent(self):
        """sync_bible メソッドが bible_agent.sync_bible_lifecycle を呼び出すことを確認"""
        mock_bible_agent = Mock()
        mock_bible_agent.sync_bible_lifecycle = AsyncMock(return_value="result")
        
        engine = UltimateHegemonyEngine(api_key="test-key", bible_agent=mock_bible_agent)
        mock_reporter = Mock()
        
        result = await engine.sync_bible(book_id=1, reporter=mock_reporter)
        
        assert result == "result"
        mock_bible_agent.sync_bible_lifecycle.assert_called_once_with(1, reporter=mock_reporter)
        
    @pytest.mark.asyncio
    async def test_resolve_bible_setting_calls_repo(self):
        """resolve_bible_setting メソッドが repo.resolve_pending_setting を呼び出すことを確認"""
        mock_repo = Mock()
        mock_repo.resolve_pending_setting = AsyncMock()
        
        engine = UltimateHegemonyEngine(api_key="test-key", repo=mock_repo)
        
        await engine.resolve_bible_setting(setting_id=1, status="approved")
        
        mock_repo.resolve_pending_setting.assert_called_once_with(1, "approved")
        
    @pytest.mark.asyncio
    async def test_determine_target_tension_calls_plot_service(self):
        """determine_target_tension メソッドが plot_service.determine_target_tension を呼び出すことを確認"""
        mock_plot_service = Mock()
        mock_plot_service.determine_target_tension = AsyncMock(return_value=0.75)
        
        engine = UltimateHegemonyEngine(api_key="test-key", plot_service=mock_plot_service)
        
        result = await engine.determine_target_tension(
            book_id=1, ep_num=1, genre="fantasy", story_type="adventure"
        )
        
        assert result == 0.75
        mock_plot_service.determine_target_tension.assert_called_once_with(
            book_id=1, ep_num=1, genre="fantasy", story_type="adventure"
        )
        
    @pytest.mark.asyncio
    async def test_validate_tension_deviation_calls_plot_service(self):
        """validate_tension_deviation メソッドが plot_service.validate_tension_deviation を呼び出すことを確認"""
        mock_plot_service = Mock()
        mock_plot_service.validate_tension_deviation = AsyncMock(return_value=(True, 0.5))
        
        engine = UltimateHegemonyEngine(api_key="test-key", plot_service=mock_plot_service)
        
        result = await engine.validate_tension_deviation(
            ep_num=1, generated_tension=0.6, book_id=1, tolerance=0.2
        )
        
        assert result == (True, 0.5)
        mock_plot_service.validate_tension_deviation.assert_called_once_with(
            ep_num=1, generated_tension=0.6, book_id=1, tolerance=0.2
        )
        
    @pytest.mark.asyncio
    async def test_reverse_plot_generation_workflow_creates_and_executes_workflow(self):
        """reverse_plot_generation_workflow が ReversePlotGenerationWorkflow を作成して実行することを確認"""
        mock_repo = Mock()
        mock_pm = Mock()
        mock_generate_json = Mock()
        
        with patch('src.backend.workflows.reverse_plot_workflow.ReversePlotGenerationWorkflow') as mock_workflow_class:
            mock_workflow_instance = Mock()
            mock_workflow_instance.execute = AsyncMock(return_value={"result": "success"})
            mock_workflow_class.return_value = mock_workflow_instance
            
            engine = UltimateHegemonyEngine(
                api_key="test-key",
                repo=mock_repo,
                pm=mock_pm,
                llm=Mock()  # generate_json 経由で llm が必要
            )
            engine.llm.generate_json = mock_generate_json
            
            mock_reporter = Mock()
            result = await engine.reverse_plot_generation_workflow(
                answers={"key": "value"},
                target_episodes=5,
                genre="fantasy",
                reporter=mock_reporter
            )
            
            assert result == {"result": "success"}
            mock_workflow_class.assert_called_once_with(mock_repo, mock_pm, mock_generate_json)
            mock_workflow_instance.execute.assert_called_once_with(
                mock_reporter,
                answers={"key": "value"},
                target_episodes=5,
                genre="fantasy"
            )


class TestHookGenerationStep:
    """HookGenerationStep のテストクラス"""
    
    @pytest.mark.asyncio
    async def test_execute_returns_true_skeleton_implementation(self):
        """execute メソッドが骨格実装通り True を返すことを確認"""
        step = HookGenerationStep()
        mock_ctx = Mock()
        mock_engine = Mock()
        mock_reporter = Mock()
        
        result = await step.execute(mock_ctx, mock_engine, mock_reporter)
        
        assert result is True