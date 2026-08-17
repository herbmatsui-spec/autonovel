"""
config/settings.py — 統一設定クラス (pydantic-settings)

このファイルが設定の単一真実源（SSOT）です。
pydantic-settings.BaseSettings を継承し、環境変数・.env・settings.toml を自動読み込み。

設計方針:
- 旧 constants.py の定数値をフィールド化
- 旧 GlobalConfigModel の全フィールドを統合
- 環境変数プレフィックス: KAKU_ (例: KAKU_DATABASE_URL, KAKU_MODEL_WRITING)
- .env ファイルからの読み込み対応
- settings.toml からの読み込みは validator.py で事前処理した値を環境変数経由で注入
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# プロジェクトルート
BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    """統一設定クラス — 全設定の単一真実源（SSOT）"""

    # ==========================================
    # Pydantic Settings 設定
    # ==========================================
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="KAKU_",  # 環境変数プレフィックス
        extra="ignore",  # 未定義の環境変数は無視
        protected_namespaces=(),
    )

    # ==========================================
    # 基本パス・ディレクトリ
    # ==========================================
    base_dir: Path = Field(default=BASE_DIR, description="プロジェクトルートディレクトリ")
    storage_dir: Path = Field(default=BASE_DIR / "storage", description="ストレージディレクトリ")
    chroma_db_path: Path = Field(default=BASE_DIR / "chroma_db", description="ChromaDBパス")

    # ==========================================
    # モデル設定
    # ==========================================
    model_writing: str = "gemma-4-31b-it"
    model_planning: str = "gemini-3.5-flash-lite"
    model_plot_expansion: str = "gemma-4-31b-it"
    model_climax: str = "gemma-4-31b-it"
    model_stable_fallback: str = "gemma-4-31b-it"
    model_ultra_stable: str = "gemma-4-31b-it"
    model_embedding: str = "text-embedding-004"

    # OpenAI互換プロバイダ設定 (OpenRouter等)
    openai_base_url: str = "https://openrouter.ai/api/v1"
    openai_api_key: str = ""

    # ==========================================
    # データベース設定
    # ==========================================
    database_url: str = "sqlite+aiosqlite:///./autonovel.db"
    db_file: str = "autonovel.db"

    # ==========================================
    # Redis キャッシュ設定
    # ==========================================
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10
    redis_default_ttl: int = 3600
    redis_namespace: str = "kaku:cache"

    # ==========================================
    # プロンプトキャッシュ設定
    # ==========================================
    prompt_cache_max_size: int = 100

    # ==========================================
    # コンテキストウィンドウ最適化設定
    # ==========================================
    context_window_target_ratio: float = 0.85
    context_window_min_reserve: int = 2000
    context_trimming_enabled: bool = True
    prefetch_enabled: bool = True
    prefetch_episode_count: int = 3
    hybrid_search_alpha: float = 0.5

    # ==========================================
    # EasyMode / パイプライン設定
    # ==========================================
    default_target_episodes: int = 8
    default_max_rewrite_iterations: int = 3
    default_target_audit_score: float = 95.0
    max_llm_retries: int = 3
    llm_retry_delay_sec: float = 1.0

    # Pipeline 話数マッピング
    ep_humiliation: int = 2
    ep_trigger: int = 3
    ep_musou_start: int = 4
    ep_final: int = 8
    tension_threshold: int = 75
    ep_climax: int = 7

    # ==========================================
    # タイムアウト値 (秒)
    # ==========================================
    default_api_timeout_sec: float = 120.0
    long_running_timeout_sec: float = 300.0
    stream_timeout_sec: float = 180.0

    # ==========================================
    # レート制限値
    # ==========================================
    rate_limit_max_requests: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_store_max_entries: int = 10000
    max_concurrent_api_calls: int = 5

    # ==========================================
    # システムパラメータ (旧 GlobalConfigModel)
    # ==========================================
    stress_catharsis_threshold: int = 85
    stress_filler_threshold: int = 35
    stress_climax_bonus: int = 50
    stress_hate_gain_base: int = 2
    max_history_len: int = 30
    auto_backup: bool = True
    safe_append_mode: str = "auto"
    cooldown_base: float = 0.0
    cooldown_min: float = 0.0
    cooldown_max: float = 90.0
    max_concurrency: int = 0
    optimized_prompt_patch: str = ""

    # ==========================================
    # 実行制御フラグ
    # ==========================================
    fail_fast_mode: bool = False
    enable_dogfeeding: bool = True
    enable_heavy_audit: bool = True

    # ==========================================
    # エッジ保全設定
    # ==========================================
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    enable_semantic_edge_preservation: bool = True

    # ==========================================
    # AI挙動設定
    # ==========================================
    draft_polish_enabled: bool = True
    polishing_min_content_ratio: float = 0.5
    actor_critic_enabled: bool = True
    actor_critic_max_iterations: int = 2
    actor_critic_severity_threshold: str = "Major"
    specialized_amplifier_enabled: bool = True

    # ==========================================
    # NSFW/セーフティ設定
    # ==========================================
    enable_nsfw: bool = False
    safety_filter_level: str = "BLOCK_ONLY_HIGH"
    default_erotic_intensity: int = 2
    erotic_intensity_scale: int = 3
    genre_erotic: str = "ero"

    # ==========================================
    # 拡張設定（ファイル由来・バリデータ経由で注入）
    # ==========================================
    domain_profiles: Optional[Dict[str, Any]] = None
    interaction_matrix: Optional[Dict[str, Any]] = None
    tropes: Optional[Dict[str, Any]] = None
    system_plugins: Optional[Dict[str, Any]] = None

    # ==========================================
    # カタルシス自動最適化
    # ==========================================
    catharsis_threshold: int = 65
    catharsis_reset_value: int = 0
    wave_pattern_ratio: Dict[str, float] = Field(
        default={"small": 0.7, "medium": 0.15, "large": 0.15},
        description="カタルシスパターンの割合設定",
    )
    catharsis_density_range: Dict[str, int] = Field(
        default={"min": 2, "max": 5}, description="カタルシス密度スライダー設定"
    )
    min_immersion_score: float = Field(default=0.0, description="没入スコアの最低閾値 (0.0-100.0)")

    # ==========================================
    # コスト設定
    # ==========================================
    cost_input_flash: float = 0.0000375
    cost_input_pro: float = 0.0035
    cost_output_flash: float = 0.00015
    cost_output_pro: float = 0.0105

# ==========================================
    # その他定数 (旧 constants.py)
    # ==========================================
    content_separator: str = "\n---\n"
    max_prompt_chars: int = 8000
    default_golden_peaks: int = 1
    nsfw_default_enabled: bool = False

    # ==========================================
    # 環境変数オーバーライド明示マップ
    # KAKU_ プレフィックス付きで上書き可能な設定を明示
    # ==========================================
    ENV_OVERRIDE_MAP: ClassVar[Dict[str, str]] = {
        # 既知の標準環境変数 (プレフィックスなし)
        "DATABASE_URL": "database_url",
        "REDIS_URL": "redis_url",
        # 明示的な KAKU_ プレフィックス上書き
        "KAKU_MODEL_WRITING": "model_writing",
        "KAKU_MODEL_PLANNING": "model_planning",
        "KAKU_MODEL_PLOT_EXPANSION": "model_plot_expansion",
        "KAKU_MODEL_CLIMAX": "model_climax",
        "KAKU_MODEL_STABLE_FALLBACK": "model_stable_fallback",
        "KAKU_MODEL_ULTRA_STABLE": "model_ultra_stable",
        "KAKU_MODEL_EMBEDDING": "model_embedding",
        "KAKU_OPENAI_BASE_URL": "openai_base_url",
        "KAKU_OPENAI_API_KEY": "openai_api_key",
        "KAKU_REDIS_MAX_CONNECTIONS": "redis_max_connections",
        "KAKU_REDIS_DEFAULT_TTL": "redis_default_ttl",
        "KAKU_REDIS_NAMESPACE": "redis_namespace",
        "KAKU_PROMPT_CACHE_MAX_SIZE": "prompt_cache_max_size",
        "KAKU_CONTEXT_WINDOW_TARGET_RATIO": "context_window_target_ratio",
        "KAKU_CONTEXT_WINDOW_MIN_RESERVE": "context_window_min_reserve",
        "KAKU_CONTEXT_TRIMMING_ENABLED": "context_trimming_enabled",
        "KAKU_PREFETCH_ENABLED": "prefetch_enabled",
        "KAKU_PREFETCH_EPISODE_COUNT": "prefetch_episode_count",
        "KAKU_HYBRID_SEARCH_ALPHA": "hybrid_search_alpha",
        "KAKU_STRESS_CATHARSIS_THRESHOLD": "stress_catharsis_threshold",
        "KAKU_STRESS_FILLER_THRESHOLD": "stress_filler_threshold",
        "KAKU_STRESS_CLIMAX_BONUS": "stress_climax_bonus",
        "KAKU_STRESS_HATE_GAIN_BASE": "stress_hate_gain_base",
        "KAKU_MAX_HISTORY_LEN": "max_history_len",
        "KAKU_AUTO_BACKUP": "auto_backup",
        "KAKU_SAFE_APPEND_MODE": "safe_append_mode",
        "KAKU_COOLDOWN_BASE": "cooldown_base",
        "KAKU_COOLDOWN_MIN": "cooldown_min",
        "KAKU_COOLDOWN_MAX": "cooldown_max",
        "KAKU_MAX_CONCURRENCY": "max_concurrency",
        "KAKU_OPTIMIZED_PROMPT_PATCH": "optimized_prompt_patch",
        "KAKU_FAIL_FAST_MODE": "fail_fast_mode",
        "KAKU_ENABLE_DOGFEEDING": "enable_dogfeeding",
        "KAKU_ENABLE_HEAVY_AUDIT": "enable_heavy_audit",
        "KAKU_DRAFT_POLISH_ENABLED": "draft_polish_enabled",
        "KAKU_POLISHING_MIN_CONTENT_RATIO": "polishing_min_content_ratio",
        "KAKU_ACTOR_CRITIC_ENABLED": "actor_critic_enabled",
        "KAKU_ACTOR_CRITIC_MAX_ITERATIONS": "actor_critic_max_iterations",
        "KAKU_ACTOR_CRITIC_SEVERITY_THRESHOLD": "actor_critic_severity_threshold",
        "KAKU_SPECIALIZED_AMPLIFIER_ENABLED": "specialized_amplifier_enabled",
        "KAKU_ENABLE_NSFW": "enable_nsfw",
        "KAKU_SAFETY_FILTER_LEVEL": "safety_filter_level",
        "KAKU_MAX_CONCURRENT_API_CALLS": "max_concurrent_api_calls",
        "KAKU_DATABASE_URL": "database_url",
        "KAKU_REDIS_URL": "redis_url",
        "KAKU_BASE_DIR": "base_dir",
    }

    # ==========================================
    # CORS / API サーバー設定
    # ==========================================
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:8501"
    api_host: str = "0.0.0.0"
    api_port: int = 8200

    # ==========================================
    # ログ設定
    # ==========================================
    log_level: str = "INFO"

    # ==========================================
    # ヘルパーメソッド
    # ==========================================

    def get_auto_concurrency(self) -> int:
        """CPU コア数から自動並行処理数を算出"""
        return min(8, (os.cpu_count() or 1) * 2)

    def validate_consistency(self) -> List[str]:
        """
        設定値同士の論理整合性を検証する。戻り値はエラーメッセージのリスト
        (空なら整合性OK)。Pydantic の型検証は通った後のセマンティクス検証用。
        """
        errors: List[str] = []
        if self.cooldown_min > self.cooldown_max:
            errors.append(
                f"cooldown_min ({self.cooldown_min}) > cooldown_max ({self.cooldown_max}) です"
            )
        if not (0.0 <= self.context_window_target_ratio <= 1.0):
            errors.append(
                f"context_window_target_ratio は 0.0-1.0 の範囲です: {self.context_window_target_ratio}"
            )
        if self.max_concurrency < 0:
            errors.append(f"max_concurrency は 0 以上である必要があります: {self.max_concurrency}")
        if self.prefetch_episode_count < 0:
            errors.append(
                f"prefetch_episode_count は 0 以上である必要があります: {self.prefetch_episode_count}"
            )
        return errors


# ==========================================
# グローバル設定インスタンス（シングルトン）
# ==========================================
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """設定インスタンスを取得（シングルトン）"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings() -> None:
    """設定インスタンスをリセット（テスト用）"""
    global _settings_instance
    _settings_instance = None


def validate_api_keys() -> None:
    """起動時 API キーバリデーション。未設定なら例外"""
    settings = get_settings()
    if not (
        getattr(settings, "gemini_api_key", None)
        or os.environ.get("GEMINI_API_KEY")
        or settings.openai_api_key
    ):
        raise RuntimeError(
            "API キーが設定されていません。環境変数 GEMINI_API_KEY または "
            "設定ファイルの gemini_api_key / openai_api_key を指定してください。"
        )


# 後方互換性のためのモジュールレベルシングルトン
settings = get_settings()

# ==========================================
# 後方互換エイリアス (段階的移行用)
# ==========================================

# 旧 constants.py からの参照をエイリアスで提供
BASE_DIR = BASE_DIR
DEFAULT_TARGET_EPISODES = 8
DEFAULT_MAX_REWRITE_ITERATIONS = 3
DEFAULT_TARGET_AUDIT_SCORE = 95.0
MAX_LLM_RETRIES = 3
LLM_RETRY_DELAY_SEC = 1.0
EP_HUMILIATION = 2
EP_TRIGGER = 3
EP_MUSOU_START = 4
EP_FINAL = 8
TENSION_THRESHOLD = 75
EP_CLIMAX = 7

# 旧 constants.py のシステム定数
ACTOR_CRITIC_ENABLED = True
ACTOR_CRITIC_MAX_ITERATIONS = 2
ACTOR_CRITIC_SEVERITY_THRESHOLD = "Major"
CONTENT_SEPARATOR = "\n---\n"
COOLDOWN_BASE_DEFAULT = 0.0
COOLDOWN_MAX_DEFAULT = 90.0
COOLDOWN_MIN_DEFAULT = 0.0
COST_INPUT_FLASH = 0.0000375
COST_INPUT_PRO = 0.0035
COST_OUTPUT_FLASH = 0.00015
COST_OUTPUT_PRO = 0.0105
DATABASE_URL = "sqlite+aiosqlite:///./autonovel.db"
DB_FILE = "autonovel.db"
DEFAULT_EROTIC_INTENSITY = 2
DEFAULT_GOLDEN_PEAKS = 1
DRAFT_POLISH_ENABLED = True
EROTIC_INTENSITY_SCALE = 3
GENRE_EROTIC = "ero"
MAX_CONCURRENCY_DEFAULT = 0
MAX_PROMPT_CHARS = 8000
MODEL_CLIMAX = "gemma-4-31b-it"
MODEL_EMBEDDING = "text-embedding-004"
MODEL_PLANNING = "gemini-3.5-flash-lite"
MODEL_PLOT_EXPANSION = "gemma-4-31b-it"
MODEL_STABLE_FALLBACK = "gemma-4-31b-it"
MODEL_ULTRA_STABLE = "gemma-4-31b-it"
MODEL_WRITING = "gemma-4-31b-it"
NSFW_DEFAULT_ENABLED = False
POLISHING_MIN_CONTENT_RATIO = 0.5
SAFE_APPEND_MODE_DEFAULT = "auto"
SAFE_APPEND_MODE_OPTIONS = ["auto", "warn_only", "error_on_overflow"]
SPECIALIZED_AMPLIFIER_ENABLED = True
STRESS_CATHARSIS_THRESHOLD = 85
STRESS_CLIMAX_BONUS = 50
STRESS_FILLER_THRESHOLD = 35
STRESS_HATE_GAIN_BASE = 2

# タイムアウト値
DEFAULT_API_TIMEOUT_SEC = 120.0
LONG_RUNNING_TIMEOUT_SEC = 300.0
STREAM_TIMEOUT_SEC = 180.0

# レート制限値
RATE_LIMIT_MAX_REQUESTS = 100
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_STORE_MAX_ENTRIES = 10000
MAX_CONCURRENT_API_CALLS = 5


# ==========================================
# 後方互換: ConfigManager (旧コード互換用)
# ==========================================
class ConfigManager:
    """旧 ConfigManager 互換ラッパー"""

    _instance: Optional[Settings] = None

    @classmethod
    def get_config(cls) -> Settings:
        if cls._instance is None:
            cls._instance = get_settings()
        return cls._instance
