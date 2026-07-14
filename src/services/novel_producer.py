"""
src/services/novel_producer.py — 小説制作サービス
"""
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from src.models.production_config import (
    EpisodeResult,
    EpisodeGenerateRequest,
    NovelProject,
    ProductionProgress
)
from src.models.report import ProductionReport
from src.services.episode_writer import EpisodeWriter
from src.services.token_tracker import TokenTracker
from src.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class NovelProducer:
    """小説制作サービス
    
    1作品の全エピソードを生成し、レポートを作成する。
    """

    def __init__(self, token_tracker: Optional[TokenTracker] = None):
        """初期化
        
        Args:
            token_tracker: トークントラッカー（Noneの場合は新規作成）
        """
        self.token_tracker = token_tracker or TokenTracker()
        self.episode_writer = EpisodeWriter()
        self.report_generator = ReportGenerator()
        self.progress_callback: Optional[Callable] = None
        
        # 内部状態
        self._current_project: Optional[NovelProject] = None
        self._episodes: List[EpisodeResult] = []
        self._progress: Optional[ProductionProgress] = None

    def set_progress_callback(self, callback: Callable[[ProductionProgress], None]):
        """進捗コールバックを設定
        
        Args:
            callback: 進捗更新時に呼ばれるコールバック関数
        """
        self.progress_callback = callback

    def _update_progress(self, status: str, message: str = ""):
        """進捗を更新
        
        Args:
            status: ステータス
            message: メッセージ
        """
        if self._progress:
            self._progress.status = status
            self._progress.message = message
            
        if self.progress_callback and self._progress:
            self.progress_callback(self._progress)

    def create_project(self, config: NovelProject) -> NovelProject:
        """新規作品プロジェクトを作成
        
        Args:
            config: 作品設定
            
        Returns:
            NovelProject: 作成されたプロジェクト
        """
        self._current_project = config
        self._episodes = []
        self._progress = ProductionProgress(
            current_episode=0,
            total_episodes=config.target_episodes,
            status="idle",
            started_at=time.time()
        )
        logger.info(f"Project created: {config.title}")
        return config

    async def generate_episode(self, project_id: int, ep_num: int) -> EpisodeResult:
        """1話を生成
        
        Args:
            project_id: プロジェクトID
            ep_num: エピソード番号
            
        Returns:
            EpisodeResult: 生成結果
        """
        self._update_progress("generating", f"第{ep_num}話を生成中...")
        
        result = await self.episode_writer.write(
            book_id=project_id,
            ep_num=ep_num,
            context=self._build_context(ep_num)
        )
        
        # 結果を記録
        episode_result = EpisodeResult(
            ep_num=ep_num,
            title=f"第{ep_num}話",
            text=result.get("text", ""),
            word_count=len(result.get("text", "")),
            quality_score=result.get("quality_score", 0.0),
            token_usage=result.get("token_usage", {}),
            status="completed"
        )
        
        # エピソードを追加
        self._episodes.append(episode_result)
        
        # 進捗を更新
        if self._progress:
            self._progress.completed_eps.append(ep_num)
            self._progress.current_episode = ep_num
        
        self._update_progress("running", f"第{ep_num}話 生成完了")
        
        return episode_result

    def _build_context(self, ep_num: int) -> Dict[str, Any]:
        """エピソード生成用のコンテキストをビルド
        
        Args:
            ep_num: エピソード番号
            
        Returns:
            Dict[str, Any]: コンテキスト辞書
        """
        context = {
            "ep_num": ep_num,
            "is_first": ep_num == 1,
            "is_last": ep_num == self._current_project.target_episodes,
            "target_word_count": self._current_project.target_word_count_per_episode
        }
        
        # 前話の情報がある場合
        if ep_num > 1 and len(self._episodes) > 0:
            prev_episode = self._episodes[-1]
            context["previous_episode"] = {
                "title": prev_episode.title,
                "ending": prev_episode.text[-200:] if prev_episode.text else "",
                "summary": prev_episode.text[:200] if prev_episode.text else ""
            }
        
        return context

    async def generate_all_episodes(self, project_id: int) -> List[EpisodeResult]:
        """全話を生成
        
        Args:
            project_id: プロジェクトID
            
        Returns:
            List[EpisodeResult]: 生成結果リスト
        """
        if not self._current_project:
            raise ValueError("プロジェクトが設定されていません")
        
        self._update_progress("running", "制作開始")
        self.token_tracker.start()
        
        try:
            for ep_num in range(1, self._current_project.target_episodes + 1):
                episode_result = await self.generate_episode(project_id, ep_num)
                
                # トークン使用量を記録
                if episode_result.token_usage:
                    input_tokens = episode_result.token_usage.get("input_tokens", 0)
                    output_tokens = episode_result.token_usage.get("output_tokens", 0)
                    self.token_tracker.add_usage(input_tokens, output_tokens, ep_num)
                
                self.token_tracker.increment_episode_count()
                
        except Exception as e:
            logger.error(f"Episode generation failed: {e}")
            if self._progress:
                self._progress.status = "failed"
            raise
        
        self.token_tracker.stop()
        
        if self._progress:
            self._progress.status = "completed"
        self._update_progress("completed", "全話制作完了")
        
        return self._episodes

    def get_progress(self) -> Optional[ProductionProgress]:
        """進捗を取得
        
        Returns:
            Optional[ProductionProgress]: 進捗情報
        """
        return self._progress

    def get_episodes(self) -> List[EpisodeResult]:
        """生成されたエピソード一覧を取得
        
        Returns:
            List[EpisodeResult]: エピソードリスト
        """
        return self._episodes

    def generate_report(self) -> ProductionReport:
        """制作レポートを生成
        
        Returns:
            ProductionReport: 制作レポート
        """
        if not self._current_project:
            raise ValueError("プロジェクトが設定されていません")
        
        episodes_data = [
            {
                "ep_num": ep.ep_num,
                "title": ep.title,
                "text": ep.text,
                "quality_score": ep.quality_score
            }
            for ep in self._episodes
        ]
        
        report = self.report_generator.generate_production_report(
            title=self._current_project.title,
            genre=self._current_project.genre,
            token_tracker=self.token_tracker,
            episodes=episodes_data
        )
        
        return report

    async def check_episode_quality(self, episode_text: str) -> float:
        """エピソードの品質チェック
        
        Args:
            episode_text: エピソードのテキスト
            
        Returns:
            float: 品質スコア
        """
        from src.services.quality_scorer import QualityScorer
        scorer = QualityScorer()
        metrics = await scorer.score_all(episode_text)
        
        # 加重平均で総合スコアを算出
        weighted_score = (
            metrics.coherence_score * 0.2 +
            metrics.character_consistency * 0.15 +
            metrics.pacing_score * 0.15 +
            metrics.hook_retention * 0.2 +
            metrics.emotional_resonance * 0.15 +
            metrics.commercial_viability * 0.15
        )
        
        return weighted_score