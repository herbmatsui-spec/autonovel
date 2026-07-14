"""
src/models/production_config.py — 作品制作設定モデル
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NovelProject:
    """小説作品プロジェクト"""
    title: str
    genre: str
    synopsis: str
    keywords: List[str] = field(default_factory=list)
    target_episodes: int = 10
    target_word_count_per_episode: int = 3000
    style_key: str = "default"
    engine_key: str = "standard"
    
    def __post_init__(self):
        """デフォルト値の設定"""
        if not self.keywords:
            self.keywords = []
        if self.target_episodes <= 0:
            self.target_episodes = 10
        if self.target_word_count_per_episode <= 0:
            self.target_word_count_per_episode = 3000


@dataclass
class EpisodeGenerateRequest:
    """エピソード生成リクエスト"""
    project_id: int
    ep_num: int
    context: dict = field(default_factory=dict)
    word_count_target: int = 3000
    
    def validate(self) -> bool:
        """リクエストの妥当性を検証"""
        if self.project_id <= 0:
            return False
        if self.ep_num <= 0:
            return False
        if self.word_count_target <= 0:
            return False
        return True


@dataclass
class EpisodeResult:
    """エピソード生成結果"""
    ep_num: int
    title: str
    text: str
    word_count: int
    quality_score: float = 0.0
    token_usage: dict = field(default_factory=dict)
    status: str = "pending"  # pending, generating, completed, failed
    
    @property
    def is_success(self) -> bool:
        """生成成功判定"""
        return self.status == "completed" and self.word_count > 0


@dataclass
class ProductionProgress:
    """制作進捗"""
    current_episode: int
    total_episodes: int
    status: str  # idle, running, paused, completed, failed
    message: str = ""
    started_at: Optional[float] = None
    completed_eps: List[int] = field(default_factory=list)
    
    @property
    def progress_percent(self) -> float:
        """進捗パーセント"""
        if self.total_episodes <= 0:
            return 0.0
        return (len(self.completed_eps) / self.total_episodes) * 100
    
    @property
    def is_complete(self) -> bool:
        """完了判定"""
        return len(self.completed_eps) >= self.total_episodes