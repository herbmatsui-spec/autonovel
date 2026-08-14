"""プロジェクト全体で使用する定数値"""
from typing import Final, Optional

# EasyMode
DEFAULT_TARGET_EPISODES: Final[int] = 8
DEFAULT_MAX_REWRITE_ITERATIONS: Final[int] = 3
DEFAULT_TARGET_AUDIT_SCORE: Final[float] = 95.0

# LLM Retry
MAX_LLM_RETRIES: Final[int] = 3
LLM_RETRY_DELAY_SEC: Final[float] = 1.0

# Pipeline 話数マッピング
EP_HUMILIATION: Final[int] = 2
EP_TRIGGER: Final[int] = 3
EP_MUSOU_START: Final[int] = 4
EP_FINAL: Final[int] = 8
TENSION_THRESHOLD: Final[int] = 75

# 設定デフォルト値 (schemas/config.py から)
ACTOR_CRITIC_ENABLED: Final[bool] = True
ACTOR_CRITIC_MAX_ITERATIONS: Final[int] = 2
ACTOR_CRITIC_SEVERITY_THRESHOLD: Final[str] = "Major"
BASE_DIR: Final[str] = ""  # 実際の値は実行時に決定される
CONTENT_SEPARATOR: Final[str] = "\n---\n"
COOLDOWN_BASE_DEFAULT: Final[float] = 0.0
COOLDOWN_MAX_DEFAULT: Final[float] = 90.0
COOLDOWN_MIN_DEFAULT: Final[float] = 0.0
COST_INPUT_FLASH: Final[float] = 0.0000375
COST_INPUT_PRO: Final[float] = 0.0035
COST_OUTPUT_FLASH: Final[float] = 0.00015
COST_OUTPUT_PRO: Final[float] = 0.0105
DATABASE_URL: Final[Optional[str]] = None
DB_FILE: Final[str] = "autonovel.db"
DEFAULT_EROTIC_INTENSITY: Final[int] = 2
DEFAULT_GOLDEN_PEAKS: Final[int] = 1
DRAFT_POLISH_ENABLED: Final[bool] = True
EROTIC_INTENSITY_SCALE: Final[int] = 3
GENRE_EROTIC: Final[str] = "ero"
MAX_CONCURRENCY_DEFAULT: Final[int] = 0
MAX_PROMPT_CHARS: Final[int] = 8000
MODEL_CLIMAX: Final[str] = "gemma-4-31b-it"
MODEL_EMBEDDING: Final[str] = "text-embedding-004"
MODEL_PLANNING: Final[str] = "gemini-3.5-flash-lite"
MODEL_PLOT_EXPANSION: Final[str] = "gemma-4-31b-it"
MODEL_STABLE_FALLBACK: Final[str] = "gemma-4-31b-it"
MODEL_ULTRA_STABLE: Final[str] = "gemma-4-31b-it"
MODEL_WRITING: Final[str] = "gemma-4-31b-it"
NSFW_DEFAULT_ENABLED: Final[bool] = False
POLISHING_MIN_CONTENT_RATIO: Final[float] = 0.5
SAFE_APPEND_MODE_DEFAULT: Final[str] = "auto"
SAFE_APPEND_MODE_OPTIONS: Final[list[str]] = ["auto", "warn_only", "error_on_overflow"]
SPECIALIZED_AMPLIFIER_ENABLED: Final[bool] = True
STRESS_CATHARSIS_THRESHOLD: Final[int] = 85
STRESS_CLIMAX_BONUS: Final[int] = 50
STRESS_FILLER_THRESHOLD: Final[int] = 35
STRESS_HATE_GAIN_BASE: Final[int] = 2