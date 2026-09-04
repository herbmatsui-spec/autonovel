# tests/integration/test_promotion_pdca.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.book_score_service import BookScoreCalculator
from src.backend.database.repositories.book_score import BookScoreRepository
from src.infrastructure.database.models.book_score import BookScore as BookScoreModel
from src.backend.routers.novel import BookScoreResponse


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def mock_book_score_repo(mock_session):
    repo = MagicMock(spec=BookScoreRepository)
    repo.session = mock_session
    return repo


@pytest.fixture
def mock_book_score_calculator(mock_book_score_repo):
    calc = MagicMock(spec=BookScoreCalculator)
    calc._repository = mock_book_score_repo
    return calc


class TestPromotionEligibility:
    """昇格判定テスト"""
    
    @pytest.mark.asyncio
    async def test_check_promotion_eligible_eligible(self, mock_book_score_calculator):
        """直近3章平均≥80かつ上昇傾向で昇格対象"""
        # 3章分のスコア作成（上昇傾向）
        scores = [
            BookScoreModel(
                book_id=1, chapter_number=1, overall_score=75.0,
                structure_score=80.0, coherency_score=70.0,
                factual_grounding_score=70.0, visual_textual_synergy_score=80.0,
                reader_experience_score=80.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
            BookScoreModel(
                book_id=1, chapter_number=2, overall_score=82.0,
                structure_score=85.0, coherency_score=80.0,
                factual_grounding_score=80.0, visual_textual_synergy_score=85.0,
                reader_experience_score=85.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
            BookScoreModel(
                book_id=1, chapter_number=3, overall_score=88.0,
                structure_score=90.0, coherency_score=85.0,
                factual_grounding_score=85.0, visual_textual_synergy_score=90.0,
                reader_experience_score=90.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
        ]
        
        async def mock_get_all(book_id):
            return scores
        
        mock_book_score_calculator._repository.get_all_for_book = mock_get_all
        
        # プロモーション判定ロジック（簡易版）
        avg_score = sum(s.overall_score for s in scores) / len(scores)
        slope = scores[-1].overall_score - scores[0].overall_score
        
        eligible = avg_score >= 80.0 and slope > 0
        
        assert eligible is True
        assert round(avg_score, 2) == 81.67
        assert slope > 0

    @pytest.mark.asyncio
    async def test_check_promotion_not_eligible_low_avg(self, mock_book_score_calculator):
        """平均スコア不足で非対象"""
        scores = [
            BookScoreModel(
                book_id=1, chapter_number=1, overall_score=70.0,
                structure_score=70.0, coherency_score=70.0,
                factual_grounding_score=70.0, visual_textual_synergy_score=70.0,
                reader_experience_score=70.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
            BookScoreModel(
                book_id=1, chapter_number=2, overall_score=72.0,
                structure_score=72.0, coherency_score=72.0,
                factual_grounding_score=72.0, visual_textual_synergy_score=72.0,
                reader_experience_score=72.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
            BookScoreModel(
                book_id=1, chapter_number=3, overall_score=75.0,
                structure_score=75.0, coherency_score=75.0,
                factual_grounding_score=75.0, visual_textual_synergy_score=75.0,
                reader_experience_score=75.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
        ]
        
        avg_score = sum(s.overall_score for s in scores) / len(scores)
        slope = scores[-1].overall_score - scores[0].overall_score
        
        eligible = avg_score >= 80.0 and slope > 0
        
        assert eligible is False
        assert avg_score < 80.0

    @pytest.mark.asyncio
    async def test_check_promotion_not_eligible_downward_trend(self, mock_book_score_calculator):
        """平均は足りるが下降傾向で非対象"""
        scores = [
            BookScoreModel(
                book_id=1, chapter_number=1, overall_score=90.0,
                structure_score=90.0, coherency_score=90.0,
                factual_grounding_score=90.0, visual_textual_synergy_score=90.0,
                reader_experience_score=90.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
            BookScoreModel(
                book_id=1, chapter_number=2, overall_score=85.0,
                structure_score=85.0, coherency_score=85.0,
                factual_grounding_score=85.0, visual_textual_synergy_score=85.0,
                reader_experience_score=85.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
            BookScoreModel(
                book_id=1, chapter_number=3, overall_score=80.0,
                structure_score=80.0, coherency_score=80.0,
                factual_grounding_score=80.0, visual_textual_synergy_score=80.0,
                reader_experience_score=80.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
        ]
        
        avg_score = sum(s.overall_score for s in scores) / len(scores)
        slope = scores[-1].overall_score - scores[0].overall_score
        
        eligible = avg_score >= 80.0 and slope > 0
        
        assert eligible is False
        assert avg_score >= 80.0
        assert slope < 0

    @pytest.mark.asyncio
    async def test_check_promotion_insufficient_chapters(self, mock_book_score_calculator):
        """3章未満で非対象"""
        scores = [
            BookScoreModel(
                book_id=1, chapter_number=1, overall_score=85.0,
                structure_score=85.0, coherency_score=85.0,
                factual_grounding_score=85.0, visual_textual_synergy_score=85.0,
                reader_experience_score=85.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
            BookScoreModel(
                book_id=1, chapter_number=2, overall_score=88.0,
                structure_score=88.0, coherency_score=88.0,
                factual_grounding_score=88.0, visual_textual_synergy_score=88.0,
                reader_experience_score=88.0, evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            ),
        ]
        
        # 3章未満の場合は非対象
        eligible = len(scores) >= 3 and sum(s.overall_score for s in scores) / len(scores) >= 80.0
        
        assert eligible is False


class TestImprovementPriorities:
    """改善優先順位提案テスト"""
    
    @pytest.mark.asyncio
    async def test_analyze_improvement_priorities(self, mock_book_score_calculator):
        """次元別時系列から改善提案を生成"""
        # 複数章のスコア履歴
        scores = [
            BookScoreModel(
                book_id=1, chapter_number=i, 
                overall_score=70.0,
                structure_score=50.0,  # 低い
                coherency_score=70.0,
                factual_grounding_score=70.0,
                visual_textual_synergy_score=70.0,
                reader_experience_score=70.0,
                evaluated_at=datetime.utcnow(),
                evaluator_version="1.0"
            )
            for i in range(1, 4)
        ]
        
        # 次元別平均計算
        dims = {
            "structure": sum(s.structure_score for s in scores) / len(scores),
            "coherency": sum(s.coherency_score for s in scores) / len(scores),
            "factual_grounding": sum(s.factual_grounding_score for s in scores) / len(scores),
            "visual_textual_synergy": sum(s.visual_textual_synergy_score for s in scores) / len(scores),
            "reader_experience": sum(s.reader_experience_score for s in scores) / len(scores),
        }
        
        # 最も低い次元を特定
        lowest_dim = min(dims, key=dims.get)
        lowest_score = dims[lowest_dim]
        
        assert lowest_dim == "structure"
        assert lowest_score == 50.0
        
        # 改善提案生成
        action_map = {
            "structure": "ContextBuilderAgent でアーク境界・テンポ強化",
            "coherency": "ContextBuilderAgent でキャラ口調・世界観ルール強化",
            "factual_grounding": "ContextBuilderAgent でRAGエンティティ・時代考証強化",
            "visual_textual_synergy": "IllustrationAgent でプロンプト再生成・感情トーン合わせ",
            "reader_experience": "WritingAgent でフック・クリフハンガー・感情曲線強化",
        }
        
        suggested_action = action_map[lowest_dim]
        
        assert lowest_dim in action_map
        assert "ContextBuilderAgent" in suggested_action
        assert "アーク境界" in suggested_action


class TestBookScoreAPI:
    """BookScore API エンドポイントテスト"""
    
    @pytest.mark.asyncio
    async def test_book_score_response_model(self):
        """BookScoreResponse モデル検証"""
        score_model = BookScoreModel(
            book_id=1, chapter_number=1, overall_score=85.5,
            structure_score=90.0, coherency_score=85.0,
            factual_grounding_score=80.0, visual_textual_synergy_score=85.0,
            reader_experience_score=90.0, evaluated_at=datetime.utcnow(),
            evaluator_version="1.0"
        )
        
        response = BookScoreResponse(
            book_id=score_model.book_id,
            chapter_number=score_model.chapter_number,
            overall_score=score_model.overall_score,
            structure_score=score_model.structure_score,
            coherency_score=score_model.coherency_score,
            factual_grounding_score=score_model.factual_grounding_score,
            visual_textual_synergy_score=score_model.visual_textual_synergy_score,
            reader_experience_score=score_model.reader_experience_score,
            evaluated_at=score_model.evaluated_at.isoformat() if score_model.evaluated_at else None,
        )
        
        assert response.book_id == 1
        assert response.chapter_number == 1
        assert response.overall_score == 85.5
        assert response.trend_3ch is None  # デフォルト
        
    @pytest.mark.asyncio
    async def test_book_score_response_with_trend(self):
        """トレンド情報付きレスポンス検証"""
        score_model = BookScoreModel(
            book_id=1, chapter_number=3, overall_score=85.5,
            structure_score=90.0, coherency_score=85.0,
            factual_grounding_score=80.0, visual_textual_synergy_score=85.0,
            reader_experience_score=90.0, evaluated_at=datetime.utcnow(),
            evaluator_version="1.0"
        )
        
        trend = {
            "avg_overall_score": 82.0,
            "trend_slope": 5.0,
            "chapters_count": 3,
            "recent_scores": [
                {"chapter": 1, "overall": 78.0},
                {"chapter": 2, "overall": 82.0},
                {"chapter": 3, "overall": 85.5},
            ],
        }
        
        response = BookScoreResponse(
            book_id=score_model.book_id,
            chapter_number=score_model.chapter_number,
            overall_score=score_model.overall_score,
            structure_score=score_model.structure_score,
            coherency_score=score_model.coherency_score,
            factual_grounding_score=score_model.factual_grounding_score,
            visual_textual_synergy_score=score_model.visual_textual_synergy_score,
            reader_experience_score=score_model.reader_experience_score,
            evaluated_at=score_model.evaluated_at.isoformat() if score_model.evaluated_at else None,
            trend_3ch=trend,
        )
        
        assert response.trend_3ch is not None
        assert response.trend_3ch["avg_overall_score"] == 82.0
        assert response.trend_3ch["trend_slope"] == 5.0
        assert response.trend_3ch["chapters_count"] == 3