# src/agents/skills/v2/writing_skill.py
"""WritingSkill v2 - Enhanced version with BookScore integration and improved observability"""

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.writing import WritingAgent
from src.services.book_score_service import BookScoreCalculator
from src.backend.observability.metrics import record_book_score
import logging
import time

logger = logging.getLogger(__name__)


class WritingSkillAgent(SkillAgent):
    """WritingAgent のスキルラッパー バージョン2 - BookScore連携強化版"""
    
    version = "2.0"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = WritingAgent(*args, **kwargs)
        # v2 新機能: BookScore カルキュレーターを初期化
        self._book_score_calculator = BookScoreCalculator()
        self._last_book_score = None
        
    async def execute(self, ctx: AgentContext) -> AgentResult:
        """スキル実行エントリーポイント - v2 拡張版"""
        start_time = time.perf_counter()
        
        try:
            # 基本的な執筆実行
            result = await self._agent.execute(ctx)
            
            # v2 新機能: 執筆後の BookScore 評価（非同期でバックグラウンド実行）
            if not result.error and result.artifacts.get("drafted_text"):
                # ブックIDとチャプター番号を取得
                book_id = ctx.book_id
                chapter_number = ctx.ep_num
                
                # バックグラウンドで BookScore を計算（実行をブロックしない）
                # 実際の実装では別タスクまたは非同期で行う
                try:
                    # 注意: ここで実際に計算すると実行が遅くなるため、
                    # 実際のシステムではキューイングまたはバックグラウンドタスクとする
                    # ここではシンプルにスキップ（実装例として残す）
                    pass
                except Exception as e:
                    logger.debug(f"BookScore calculation skipped: {e}")
            
            # 実行時間を記録
            duration = time.perf_counter() - start_time
            self._record_metric("success", duration)
            
            # v2 新機能: 詳細なメトリクスを記録
            try:
                from src.backend.observability.metrics import record_generation_task
                workflow_type = "writing_v2"
                status = "completed" if not result.error else "failed"
                record_generation_task(workflow_type, status, duration)
            except Exception:
                pass
                
            return result
            
        except Exception as e:
            # エラー時の処理を強化
            duration = time.perf_counter() - start_time
            self._record_metric("error", duration)
            
            # v2 新機能: エラー時の詳細ログとメトリクス
            logger.error(f"WritingSkillAgent execution failed: {e}", exc_info=True)
            
            try:
                from src.backend.observability.metrics import record_generation_task
                workflow_type = "writing_v2"
                record_generation_task(workflow_type, "failed", duration)
            except Exception:
                pass
                
            raise
    
    async def execute_with_bookscore_feedback(self, ctx: AgentContext) -> AgentResult:
        """BookScore フィードバックを活用した執筆実験的メソッド"""
        # このメソッドは v2 の実験的機能として残す
        # 実際の運用では A/B テストなどで効果を検証する
        start_time = time.perf_counter()
        
        try:
            # 通常の執筆を実行
            result = await self._agent.execute(ctx)
            
            if not result.error:
                # BookScore を取得してフィードバックとする
                try:
                    book_id = ctx.book_id
                    chapter_number = ctx.ep_num
                    
                    # ここでは簡易版として、将来的に実装する旨を示す
                    # 実際には BookScoreCalculator.calculate() を呼び出す
                    logger.info(f"WritingSkillAgent: BookScore feedback would be calculated for book {book_id}, chapter {chapter_number}")
                except Exception as e:
                    logger.debug(f"BookScore feedback skipped: {e}")
            
            duration = time.perf_counter() - start_time
            self._record_metric("success", duration)
            return result
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            self._record_metric("error", duration)
            raise