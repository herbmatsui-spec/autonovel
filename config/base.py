import logging
import os
from pathlib import Path

"""
config/base.py — 旧設定定数モジュール (後方互換用・非推奨)

⚠️ 非推奨: 実行時設定の単一真理源 (SSOT) は `config/settings.toml` に移行しました。
実行時の設定値は `ProjectContext.get_setting("...")` 経由で取得してください。
本モジュールの定数は既存コードの互換性維持のためのみ残されています。
新しいコードでは `from config.project_context import ProjectContext` を使用してください。
"""

# ==========================================
# ロガー
# ==========================================
logger = logging.getLogger(__name__)

# ==========================================
# モデル設定
# ==========================================
MODEL_PLANNING        = "gemini-3.1-flash-lite"
MODEL_PLOT_EXPANSION  = "gemma-4-31b-it"
MODEL_EMBEDDING       = "gemini-embedding-2"
MODEL_WRITING         = "gemma-4-31b-it" # Keep this as is, only change MODEL_PLOT_EXPANSION
MODEL_CLIMAX          = "gemma-4-31b-it"
MODEL_STABLE_FALLBACK = "gemma-4-31b-it" # 503エラー時の緊急回避用モデルエラー時の緊急回避用モデル
MODEL_ULTRA_STABLE    = "gemma-4-31b-it"

# ==========================================
# ファイルパス
# ==========================================
BASE_DIR = Path(__file__).parent.parent.absolute()
DB_FILE  = "kaku_hegemony_v2.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR}/{DB_FILE}")


# ==========================================
# API制御定数
# ==========================================
MAX_PROMPT_CHARS        = 1_000_000
CONTENT_SEPARATOR       = "### NOVEL CONTENT ###"
DEFAULT_GOLDEN_PEAKS    = [5, 10, 15, 25, 50]

# Draft & Polish 二段階エージェント設定
DRAFT_POLISH_ENABLED    = True
POLISHING_MIN_CONTENT_RATIO = 0.5

# Actor-Critic 自律推敲ループ設定
ACTOR_CRITIC_ENABLED            = True    # Actor-Criticループ全体のON/OFF
ACTOR_CRITIC_MAX_ITERATIONS     = 2       # 最大反復回数（コスト注意: 1回のループで2回LLM呼び出し増）
ACTOR_CRITIC_SEVERITY_THRESHOLD = "Major" # "Major" or "Critical"のみトリガー (Minorはスキップ)

# Specialized Amplifier 設定
SPECIALIZED_AMPLIFIER_ENABLED = True  # 種別特化Amplifier全体のON/OFF




# カクヨム1位獲得のための「極限ヘイト・爆速カタルシス」調整
STRESS_CATHARSIS_THRESHOLD = 85   # 爆発力を高めるため、極限までヘイトを溜める
STRESS_FILLER_THRESHOLD    = 35   # 読者が飽きる前にヘイト（溜め）を補充
STRESS_CLIMAX_BONUS        = 50   # カタルシス回でのストレス解放量
STRESS_HATE_GAIN_BASE      = 2    # Hate フェーズでの標準ストレス積算量

# カタルシス・タイミング自動最適化エンジン設定
CATHARSIS_THRESHOLD       = 65   # カタルシス発動ストレス閾値
CATHARSIS_RESET_VALUE     = 0    # 解放後の累積リセット値
WAVE_PATTERN_RATIO        = {"small": 0.7, "medium": 0.15, "large": 0.15}
CATHARSIS_DENSITY_PRESETS = {
    0: {"label": "なし", "interval_min": 999, "interval_max": 999},
    1: {"label": "稀疏", "interval_min": 10, "interval_max": 15},
    2: {"label": "標準", "interval_min": 7,  "interval_max": 10},
    3: {"label": "多め", "interval_min": 5,  "interval_max": 7},
    4: {"label": "過激", "interval_min": 3,  "interval_max": 5},
    5: {"label": "狂気", "interval_min": 2,  "interval_max": 4},
}
MIN_IMMERSION_SCORE = 0.0

# 語彙ランダマイズ・強制置換設定
COST_INPUT_FLASH  = 0.00000025   # $0.25  / 1M tokens
COST_OUTPUT_FLASH = 0.0000015    # $1.50  / 1M tokens (思考トークン含む)
COST_INPUT_PRO    = 0.00000125   # $1.25  / 1M tokens (<128k)
COST_OUTPUT_PRO   = 0.00000375   # $3.75  / 1M tokens (<128k)

COOLDOWN_BASE_DEFAULT   = 0.0
COOLDOWN_MIN_DEFAULT    = 0.0
COOLDOWN_MAX_DEFAULT    = 90.0
SAFE_APPEND_MODE_OPTIONS = ["auto", "warn_only", "error_on_overflow"]
SAFE_APPEND_MODE_DEFAULT = "auto"
MAX_CONCURRENCY_DEFAULT = 0 # 0 for auto

# ==========================================
# 官能/NSFW設定
# ==========================================
GENRE_EROTIC = "官能/ロマンス"
EROTIC_INTENSITY_SCALE = {0: "ほのぼの", 1: "微熱", 2: "情熱", 3: "背徳", 4: "濃厚", 5: "過激"}
DEFAULT_EROTIC_INTENSITY = 2
NSFW_DEFAULT_ENABLED = False

# ==========================================
# チートスケール・代償定義（物語の軸）
# ==========================================

PLANNING_PRESETS = {
    "🔥 王道ざまぁ": {
        "cheat_scale": 5,
        "cost_severity": 1,
        "system_assist": 80,
        "desc": "圧倒的快感。最強の能力で敵を完封する構成"
    },
    "🌑 ダークファンタジー": {
        "cheat_scale": 3,
        "cost_severity": 5,
        "system_assist": 40,
        "desc": "重厚な絶望と代償。泥臭く這い上がる構成"
    },
    "🕊️ スローライフ": {
        "cheat_scale": 2,
        "cost_severity": 1,
        "system_assist": 60,
        "desc": "心地よい日常とゆるいチート。癒やし重視の構成"
    },
    "⚡ ハイブリッド": {
        "cheat_scale": 4,
        "cost_severity": 3,
        "system_assist": 60,
        "desc": "適度な緊張感と爽快感の両立。バランス型構成"
    }
}

