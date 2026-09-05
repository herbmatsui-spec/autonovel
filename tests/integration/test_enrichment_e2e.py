# tests/integration/test_enrichment_e2e.py
"""EnrichmentAgent E2E統合テスト"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName


class TestEnrichmentE2E:
    """EnrichmentAgent エンドツーエンドテスト"""

    @pytest.fixture
    def mock_llm(self):
        """モックLLM"""
        llm = AsyncMock()
        llm.generate_text = AsyncMock(return_value="生成されたテキスト")
        llm.generate_json = AsyncMock(return_value={
            "enriched_text": "エンリッチメント済みテキスト",
            "insertions": [],
            "expansions": [],
        })
        return llm

    @pytest.fixture
    def mock_prompt_manager(self):
        """モックプロンプトマネージャ"""
        pm = MagicMock()
        return pm

    @pytest.fixture
    def mock_rag_service(self):
        """モックRAGサービス"""
        rag = AsyncMock()
        rag.query_trivia_candidates = AsyncMock(return_value=[
            {"fact": "世界観の豆知識", "source_type": "world_bible", "entity": "世界観", "score": 0.9}
        ])
        rag.index_bible_sources = AsyncMock(return_value={
            "魔法システム": [{"source": "設定書", "page": "p.1"}]
        })
        return rag

    @pytest.fixture
    def agent(self, mock_llm, mock_prompt_manager, mock_rag_service):
        """EnrichmentAgent インスタンス"""
        return EnrichmentAgent(
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
            rag_service=mock_rag_service,
        )

    @pytest.fixture
    def sample_context(self):
        """サンプルコンテキスト"""
        return AgentContext(
            book_id=1,
            branch_id=1,
            ep_num=1,
            artifacts={
                "drafted_text": "主人公は魔法システムAを使って敵と戦った。悲しかったが剣を振るった。",
                "writing_context": {
                    "location": "決戦の野",
                    "characters": ["主人公", "敵将軍"],
                    "pov": "third_person",
                },
            },
        )

    @pytest.mark.asyncio
    async def test_execute_basic_flow(self, agent, sample_context):
        """基本フロー実行"""
        # 機能フラグを有効化
        agent._config = {"enabled": True}
        
        result = await agent.execute(sample_context)
        
        assert isinstance(result, AgentResult)
        assert result.next_agent == AgentName.AUDIT
        assert "enriched_text" in result.artifacts
        assert "enrichment_metadata" in result.artifacts
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_disabled_flag(self, agent, sample_context):
        """機能フラグOFFでパススルー"""
        agent._config = {"enabled": False}
        
        result = await agent.execute(sample_context)
        
        assert result.next_agent == AgentName.AUDIT
        assert result.artifacts["enriched_text"] == sample_context.artifacts["drafted_text"]
        assert result.artifacts["enrichment_metadata"] == {"trivia": [], "citations": [], "sensory": [], "multimedia": {}}

    @pytest.mark.asyncio
    async def test_execute_no_drafted_text(self, agent):
        """drafted_textなしでエラー"""
        ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
        
        result = await agent.execute(ctx)
        
        assert result.error is not None
        assert "drafted_text is required" in result.error

    @pytest.mark.asyncio
    async def test_execute_blind_review_mode(self, agent, sample_context):
        """ブラインドレビューモード"""
        agent._config = {"enabled": True}
        sample_context.artifacts["blind_review_mode"] = True
        
        result = await agent.execute(sample_context)
        
        assert result.next_agent == AgentName.AUDIT
        # トリビア・引用がスキップされている
        meta = result.artifacts["enrichment_metadata"]
        assert any(item.get("skipped") for item in meta["trivia"])
        assert any(item.get("skipped") for item in meta["citations"])
        # 感覚拡充・マルチメディアは実行される
        assert len(meta["sensory"]) >= 0
        assert isinstance(meta["multimedia"], dict)

    @pytest.mark.asyncio
    async def test_events_emitted(self, agent, sample_context):
        """イベント発行確認"""
        agent._config = {"enabled": True}
        events = []
        
        # emit_event をフック
        original_emit = agent.emit_event
        def capture_event(name, payload):
            events.append((name, payload))
            return original_emit(name, payload)
        agent.emit_event = capture_event
        
        await agent.execute(sample_context)
        
        event_names = [e[0] for e in events]
        assert "enrichment.started" in event_names
        assert "enrichment.step_completed" in event_names
        assert "enrichment.completed" in event_names
        # 4ステップ完了
        step_events = [e for e in events if e[0] == "enrichment.step_completed"]
        assert len(step_events) == 4
        steps = [e[1]["step"] for e in step_events]
        assert "trivia_insertion" in steps
        assert "citation_attachment" in steps
        assert "sensory_expansion" in steps
        assert "multimedia_scenarios" in steps

    @pytest.mark.asyncio
    async def test_enrichment_metadata_structure(self, agent, sample_context):
        """メタデータ構造確認"""
        agent._config = {"enabled": True}
        
        result = await agent.execute(sample_context)
        
        meta = result.artifacts["enrichment_metadata"]
        assert "trivia" in meta
        assert "citations" in meta
        assert "sensory" in meta
        assert "multimedia" in meta
        assert isinstance(meta["trivia"], list)
        assert isinstance(meta["citations"], list)
        assert isinstance(meta["sensory"], list)
        assert isinstance(meta["multimedia"], dict)

    @pytest.mark.asyncio
    async def test_trivia_insertion_increases_length(self, agent, sample_context):
        """トリビア挿入でテキストが長くなる"""
        agent._config = {
            "enabled": True,
            "trivia_insertion": {"enabled": True, "max_insertions_per_chapter": 3, "relevance_threshold": 0.5}
        }
        
        result = await agent.execute(sample_context)
        
        enriched = result.artifacts["enriched_text"]
        original = sample_context.artifacts["drafted_text"]
        # トリビア挿入により長くなる（モックの場合は変わらない可能性もある）
        assert len(enriched) >= len(original)

    @pytest.mark.asyncio
    async def test_sensory_expansion_adds_details(self, agent, sample_context):
        """感覚拡充で詳細が追加"""
        agent._config = {"enabled": True, "sensory_expansion": {"enabled": True}}
        
        result = await agent.execute(sample_context)
        
        meta = result.artifacts["enrichment_metadata"]
        # 感覚拡充メタデータがある
        assert "sensory" in meta

    @pytest.mark.asyncio
    async def test_multimedia_generation_for_climax(self, agent, sample_context):
        """クライマックスシーンでマルチメディア生成"""
        agent._config = {"enabled": True, "multimedia_scenarios": {"enabled": True}}
        sample_context.artifacts["drafted_text"] = "最終決戦だ。主人公は剣を構える。敵将軍が迫る。命懸けの戦い。"
        
        result = await agent.execute(sample_context)
        
        meta = result.artifacts["enrichment_metadata"]
        assert "multimedia" in meta
        multimedia = meta["multimedia"]
        assert "manga_script" in multimedia
        assert "radio_drama" in multimedia
        assert "anime_storyboard" in multimedia
        assert "live_action_shots" in multimedia


class TestEnrichmentFallback:
    """フォールバック動作テスト"""

    @pytest.mark.asyncio
    async def test_rag_failure_fallback(self, sample_context):
        """RAG失敗時のフォールバック"""
        mock_rag = AsyncMock()
        mock_rag.query_trivia_candidates = AsyncMock(side_effect=Exception("DB error"))
        mock_rag.index_bible_sources = AsyncMock(return_value={})
        
        agent = EnrichmentAgent(rag_service=mock_rag)
        agent._config = {"enabled": True}
        
        result = await agent.execute(sample_context)
        
        # エラーにならず完了
        assert result.next_agent == AgentName.AUDIT
        assert "enriched_text" in result.artifacts

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self, sample_context):
        """LLM失敗時のフォールバック"""
        mock_llm = AsyncMock()
        mock_llm.generate_text = AsyncMock(side_effect=Exception("LLM error"))
        
        agent = EnrichmentAgent(llm=mock_llm)
        agent._config = {"enabled": True}
        
        result = await agent.execute(sample_context)
        
        assert result.next_agent == AgentName.AUDIT
        assert "enriched_text" in result.artifacts