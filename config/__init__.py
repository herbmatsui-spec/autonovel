"""
config パッケージ
アプリケーション全体の設定・定数・ドメインプロファイルを一元管理します。
"""

# 1. 分割された定数群のインポート
from .archetypes_new import (
    ARCHETYPE_KEY_ALIASES,
    CHEAT_DESCRIPTIONS,
    COST_DESCRIPTIONS,
    DEBUFF_PROFILES,
    EASY_GENRES,
    EASY_MODE_KEYWORDS_MAP,
    PLOT_STRUCTURES,
    STORY_ARCHETYPES,
    VILLAIN_STRATEGIES,
    WIZARD_ARCHETYPE_LABELS,
    WIZARD_GENRE_OPTIONS,
    resolve_archetype_key,
)
from .constants import (
    ACTOR_CRITIC_ENABLED,
    ACTOR_CRITIC_MAX_ITERATIONS,
    ACTOR_CRITIC_SEVERITY_THRESHOLD,
    BASE_DIR,
    CONTENT_SEPARATOR,
    COOLDOWN_BASE_DEFAULT,
    COOLDOWN_MAX_DEFAULT,
    COOLDOWN_MIN_DEFAULT,
    COST_INPUT_FLASH,
    COST_INPUT_PRO,
    COST_OUTPUT_FLASH,
    COST_OUTPUT_PRO,
    DATABASE_URL,
    DB_FILE,
    DEFAULT_EROTIC_INTENSITY,
    DEFAULT_GOLDEN_PEAKS,
    DRAFT_POLISH_ENABLED,
    EROTIC_INTENSITY_SCALE,
    GENRE_EROTIC,
    MAX_CONCURRENCY_DEFAULT,
    MAX_PROMPT_CHARS,
    MODEL_CLIMAX,
    MODEL_EMBEDDING,
    MODEL_PLANNING,
    MODEL_PLOT_EXPANSION,
    MODEL_STABLE_FALLBACK,
    MODEL_ULTRA_STABLE,
    MODEL_WRITING,
    NSFW_DEFAULT_ENABLED,
    POLISHING_MIN_CONTENT_RATIO,
    SAFE_APPEND_MODE_DEFAULT,
    SAFE_APPEND_MODE_OPTIONS,
    SPECIALIZED_AMPLIFIER_ENABLED,
    STRESS_CATHARSIS_THRESHOLD,
    STRESS_CLIMAX_BONUS,
    STRESS_FILLER_THRESHOLD,
    STRESS_HATE_GAIN_BASE,
)

# 3. Streamlit アダプター（必要に応じてクライアントがインポート）
# from .streamlit_adapter import StreamlitConfig
# 4. サブモジュールのエクスポート
from .domain_profile_manager import DomainProfileManager, DomainProfileService

# 官能/NSFWモジュール
from .erotic_pacing import EroticBeat, EroticCurve
from .erotic_platform_presets import PLATFORM_PRESETS, get_preset, get_preset_names
from .erotic_vocabulary import (
    METAPHOR_BANK,
    ONOMATOPOEIA_BANK,
    PSYCHOLOGY_TEMPLATES,
    VOCABULARY_TIERS,
    get_vocabulary_for_tier,
)
from .erotic_vocabulary_ext import (
    INTENSE_METAPHORS,
    INTENSE_ONOMATOPOEIA,
    INTENSE_PSYCHOLOGY,
    VOCABULARY_TIERS_EXT,
    get_vocabulary_for_tier_ext,
)
from .models import GlobalConfigModel
from .narrative import (
    ANTI_PATTERNS,
    AUDIT_TRIGGER_KEYWORDS,
    CHARACTER_EXPANSION_THEMES,
    ROUTINE_VARIATIONS,
    TRAGEDY_VARIATIONS,
)

# 2. project_context から新しいシステム中枢クラスと定数を上書きエクスポート
from .project_context import PROMPT_TEMPLATES, GlobalConfig, ProjectContext, get_config, set_config
from .styles import (
    DAILY_MICRO_HOOKS,
    FORBIDDEN_SUMMARY_PATTERNS,
    FORBIDDEN_WORD_REPLACEMENTS,
    NARRATIVE_PROPS,
    RULE_SET_A_NEG,
    RULE_SET_A_RULES,
    RULE_SET_B_NEG,
    RULE_SET_B_RULES,
    RULE_SET_C_NEG,
    RULE_SET_C_RULES,
    RULE_SET_D_NEG,
    RULE_SET_D_RULES,
    STYLE_DEFINITIONS,
    STYLE_REFINEMENT_DIRECTIONS,
)

__all__ = [
    "ProjectContext",
    "GlobalConfig",
    "GlobalConfigModel",
    "set_config",
    "get_config",
    "PROMPT_TEMPLATES",
    "DomainProfileManager",
    "DomainProfileService",
    "EroticBeat",
    "EroticCurve",
    "get_vocabulary_for_tier",
    "get_preset",
    "get_preset_names"
]
