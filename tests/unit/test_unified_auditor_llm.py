import pytest
from src.core.llm.types import LLMRequest, LLMResponse, LLMUsage
from src.agents.specialist_auditor_base import SpecialistAuditResult

# Mock LLM client that returns a fixed JSON response for auditors
class MockLLMClient:
    def __init__(self):
        self.called = False

    async def agenerate(self, req: LLMRequest) -> LLMResponse:
        self.called = True
        # Return a fixed JSON response that matches the auditor's expected format
        import json
        response_dict = {
            "score": 85.0,
            "critique": "テスト用の講評",
            "suggestions": ["具体的な改善提案1", "具体的な改善提案2"],
            "confidence": 0.9,
            "reasoning": "テスト用の理由",
            "actionable_diffs": [
                {
                    "location": "テスト場所",
                    "original_quote": "問題のある原文",
                    "improved_suggestion": "改善後の具体的な文章",
                    "rationale": "書き換え理由"
                }
            ]
        }
        return LLMResponse(
            content=json.dumps(response_dict),
            model="test_model",
            usage=LLMUsage(),
        )

    def generate(self, req: LLMRequest) -> LLMResponse:
        # Synchronous version (not used by auditors but implemented for completeness)
        import json
        response_dict = {
            "score": 85.0,
            "critique": "テスト用の講評",
            "suggestions": ["具体的な改善提案1", "具体的な改善提案2"],
            "confidence": 0.9,
            "reasoning": "テスト用の理由",
            "actionable_diffs": [
                {
                    "location": "テスト場所",
                    "original_quote": "問題のある原文",
                    "improved_suggestion": "改善後の具体的な文章",
                    "rationale": "書き換え理由"
                }
            ]
        }
        return LLMResponse(
            content=json.dumps(response_dict),
            model="test_model",
            usage=LLMUsage(),
        )

@pytest.mark.asyncio
async def test_consistency_auditor_with_mock_llm():
    from src.agents.specialists.consistency_auditor import ConsistencyAuditor
    mock_llm = MockLLMClient()
    auditor = ConsistencyAuditor(llm=mock_llm)
    # Minimal context for consistency auditor
    ctx = {
        "draft_text": "これはテスト用のドラフト本文です。",
        "world_bible_snapshot": {
            "characters": [{"name": "太郎", "status": "健康"}],
            "terms": [],
            "rules": []
        }
    }
    result = await auditor.audit(ctx)
    assert isinstance(result, SpecialistAuditResult)
    assert result.specialist_name == "consistency"
    assert mock_llm.called

@pytest.mark.asyncio
async def test_factual_auditor_with_mock_llm():
    from src.agents.specialists.factual_auditor import FactualAuditor
    mock_llm = MockLLMClient()
    auditor = FactualAuditor(llm=mock_llm)
    ctx = {
        "draft_text": "これはテスト用のドラフト本文です。",
        "world_bible_snapshot": {}
    }
    result = await auditor.audit(ctx)
    assert isinstance(result, SpecialistAuditResult)
    assert result.specialist_name == "factual"
    assert mock_llm.called

@pytest.mark.asyncio
async def test_reader_hook_auditor_with_mock_llm():
    from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor
    mock_llm = MockLLMClient()
    auditor = ReaderHookAuditor(llm=mock_llm)
    ctx = {
        "draft_text": "これはテスト用のドラフト本文です。"
    }
    result = await auditor.audit(ctx)
    assert isinstance(result, SpecialistAuditResult)
    assert result.specialist_name == "reader_hook"
    assert mock_llm.called

@pytest.mark.asyncio
async def test_style_auditor_with_mock_llm():
    from src.agents.specialists.style_auditor import StyleAuditor
    mock_llm = MockLLMClient()
    auditor = StyleAuditor(llm=mock_llm)
    ctx = {
        "draft_text": "これはテスト用のドラフト本文です。"
    }
    result = await auditor.audit(ctx)
    assert isinstance(result, SpecialistAuditResult)
    assert result.specialist_name == "style"
    assert mock_llm.called

@pytest.mark.asyncio
async def test_structure_auditor_with_mock_llm():
    from src.agents.specialists.structure_auditor import StructureAuditor
    mock_llm = MockLLMClient()
    auditor = StructureAuditor(llm=mock_llm)
    ctx = {
        "draft_text": "これはテスト用のドラフト本文です。"
    }
    result = await auditor.audit(ctx)
    assert isinstance(result, SpecialistAuditResult)
    assert result.specialist_name == "structure"
    assert mock_llm.called

@pytest.mark.asyncio
async def test_multimodal_auditor_with_mock_llm():
    from src.agents.specialists.multimodal_auditor import MultimodalAuditor
    mock_llm = MockLLMClient()
    auditor = MultimodalAuditor(llm=mock_llm)
    ctx = {
        "draft_text": "これはテスト用のドラフト本文です。",
        "illustration_prompts": "テスト用の挿絵プロンプト"
    }
    result = await auditor.audit(ctx)
    assert isinstance(result, SpecialistAuditResult)
    assert result.specialist_name == "multimodal"
    assert mock_llm.called

@pytest.mark.asyncio
async def test_emotion_curve_auditor_with_mock_llm():
    from src.agents.specialists.emotion_curve_auditor import EmotionCurveAuditor
    mock_llm = MockLLMClient()
    auditor = EmotionCurveAuditor(llm=mock_llm)
    ctx = {
        "draft_text": "これはテスト用のドラフト本文です。"
    }
    result = await auditor.audit(ctx)
    assert isinstance(result, SpecialistAuditResult)
    assert result.specialist_name == "emotion_curve"
    assert mock_llm.called

@pytest.mark.asyncio
async def test_creativity_auditor_with_mock_llm():
    from src.agents.specialists.creativity_auditor import CreativityAuditor
    mock_llm = MockLLMClient()
    auditor = CreativityAuditor(llm=mock_llm)
    ctx = {
        "draft_text": "これはテスト用のドラフト本文です。"
    }
    result = await auditor.audit(ctx)
    assert isinstance(result, SpecialistAuditResult)
    assert result.specialist_name == "creativity"
    assert mock_llm.called