from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class IllustrationType(Enum):
    COVER = "cover"  # 表紙
    EPISODE = "episode"  # 話数ごとの挿絵（シーン抽出）
    CHARACTER = "character"  # キャラクター立ち絵
    YONKOMA = "yonkoma"  # 1エピソードを6コマで要約する4コマ風漫画プロンプト
    MANGA_24PANEL = "manga_24panel"  # 1エピソードを4x6=24コマの1枚シートで描く


class IllustrationModel(Enum):
    AUTO = "auto"  # コンテキストに応じ自動選択
    FAST = "fast"
    QUALITY = "quality"
    ULTRA = "ultra"


class SafetyLevel(Enum):
    BLOCK_MOST = "BLOCK_MOST"
    BLOCK_SOME = "BLOCK_SOME"
    BLOCK_FEW = "BLOCK_FEW"
    R15_CONTENT = "R15_CONTENT"  # 官能モード用


@dataclass
class IllustrationRequest:
    book_id: int
    illustration_type: IllustrationType
    episode_number: int | None = None
    character_id: int | None = None
    scene_text: str | None = None
    book_context: dict[str, str] = field(default_factory=dict)
    model: IllustrationModel = IllustrationModel.AUTO
    safety_level: SafetyLevel = SafetyLevel.BLOCK_SOME
    aspect_ratio: str = "3:4"
    prompt_override: str | None = None
    panels: int = 6  # YONKOMA 用のコマ数 (3〜6) / MANGA_24PANEL 用 (1〜24)


@dataclass
class IllustrationResult:
    request: IllustrationRequest
    image_url: str
    prompt: str
    model_used: str
    generation_time_ms: int
    illustration_id: int | None = None
    #: 統合エンジンがローカル保存した実ファイルパス（未保存なら None）
    image_path: Path | None = None
    #: 品質ゲートの評価結果（`QualityEvaluation.to_dict()` 相当の dict）
    quality: dict | None = None
    #: 後処理（超解像・写植）後のパス
    upscaled_path: Path | None = None
    final_path: Path | None = None
    typeset_applied: bool = False
    estimated_cost_usd: float = 0.0

    @property
    def output_path(self) -> Path | None:
        """利用可能な最終出力パスを返す（写植 → 超解像 → 生出力 の順）。"""
        for candidate in (self.final_path, self.upscaled_path, self.image_path):
            if candidate is not None:
                return candidate
        return None

    def resolved_url(self) -> str:
        """`image_url` が空ならローカルパスから静的URLを組み立てる。"""
        if self.image_url:
            return self.image_url
        path = self.output_path
        if path is None:
            return ""
        posix = Path(path).as_posix()
        for prefix in ("static/",):
            if posix.startswith(prefix):
                return "/" + posix
        return "/" + posix
