"""50話×3000文字 小説自動生成 設定定数モジュール (ステップ1〜2)"""

from pathlib import Path
from typing import Dict, List
import yaml

# ステップ1: 目標文字数の定数化
TARGET_CHARS: int = 3000
MIN_CHARS: int = 2900
MAX_CHARS: int = 3100

# ステップ2: エピソード総数
TOTAL_EPISODES: int = 50

# パート別文字数配分 (合計 3000文字)
# 中盤の盛り上がりに合わせ、サブキャラ描写(4)とアクション(5)を強化
PART_TARGETS: Dict[int, int] = {
    1: 300,  # パート①: 世界観・シンボル描写
    2: 400,  # パート②: 過去回想(100字) + 不安(300字)
    3: 400,  # パート③: 今回ミッション提示
    4: 500,  # パート④: サブキャラとの掛け合い・関係性深化
    5: 600,  # パート⑤: 最大緊張アクション
    6: 500,  # パート⑥: 感情クライマックス
    7: 300,  # パート⑦: 鋭い次回クリフハンガーへの収束
}

# 許容公差 (パート生成時 ±50文字)
PART_TOLERANCE: int = 50

# 最大再試行回数
MAX_PART_RETRIES: int = 3

# ベースディレクトリ定義
BASE_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = BASE_DIR.parent
OUTPUT_DIR: Path = BASE_DIR / "output"
LOG_DIR: Path = BASE_DIR / "log"
FINAL_DIR: Path = BASE_DIR / "final"
PROMPTS_DIR: Path = BASE_DIR / "prompts"

WORLD_FILE: Path = BASE_DIR / "world.yaml"
EMOTIONS_FILE: Path = BASE_DIR / "emotion_words.txt"
CLIFFS_FILE: Path = BASE_DIR / "cliff_patterns.txt"
TEMPLATE_FILE: Path = BASE_DIR / "template.md"
FORESHADOW_FILE: Path = BASE_DIR / "foreshadow.csv"
PROGRESS_FILE: Path = BASE_DIR / "progress.txt"
SCORES_FILE: Path = BASE_DIR / "scores.csv"
METADATA_FILE: Path = BASE_DIR / "metadata.json"
FORESHADOW_MAP_FILE: Path = BASE_DIR / "foreshadow_map.md"

# ステップ(1) 4コマ漫画プロンプト生成 オプトイン設定
MANGA_PROMPT_ENABLED: bool = False
MANGA_PROMPTS_DIR: Path = BASE_DIR / "manga_prompts"
MANGA_PANEL_COUNT: int = 4
MANGA_OUTPUT_FORMATS: List[str] = ["txt", "jsonl"]
MANGA_LAYOUT: str = "vertical"  # 'vertical' (縦4段) または '2x2'
MANGA_MAX_CHARS_PER_PANEL: int = 120
MANGA_STYLE_FILE: Path = BASE_DIR / "illust_style.yaml"

# ステップ57: 安全性チェック用 NG表現キーワード（過剰な暴力等の除外）
ILLUST_SAFETY: List[str] = [
    "過剰な流血",
    "グロテスク",
    "暴力的な表現",
    "露骨な描写",
    "残酷な描写",
]

# 視点指定の有効値
VALID_VIEWPOINTS: List[str] = [
    "third_person",
    "first_person_watashi",
    "first_person_boku",
    "first_person_ore",
]

# ステップ58: ドライラン（サンプル1話だけ生成）
MANGA_DRY_RUN: bool = False


# 文体ガイド デフォルト値 (world.yaml 未設定時のフォールバック)
STYLE_GUIDE_DEFAULT: dict = {
    "tone": "常体",
    "vocabulary_level": "中級",
    "avg_sentence_length": 45,
    "unique_words_target": 180,
    "formality": "やや硬め",
    "sentence_endings": ["だ。", "である。", "た。"],
    "forbidden_endings": ["です。", "ます。"],
}


def enable_manga_prompts() -> None:
    """ステップ12: オプトインを実行時に有効化する（CLIフラグ等から呼ぶ）"""
    global MANGA_PROMPT_ENABLED
    MANGA_PROMPT_ENABLED = True


def is_manga_enabled() -> bool:
    """ステップ12: オプトイン状態を呼び出し時に評価して返す"""
    return MANGA_PROMPT_ENABLED


# ステップ36: 画風設定の読み込み（illust_style.yaml）
def load_illust_style() -> dict:
    """illust_style.yaml を読み込み、欠損時はデフォルトを返す"""
    defaults = {
        "style_hint": "セルルックアニメ風",
        "color_tone": "淡い青白い光脈を基調に温かみのあるアクセント",
        "aspect_ratio": "vertical_strip",
        "font": "丸みのある可読な日本語フォント",
    }
    if not MANGA_STYLE_FILE.exists():
        return defaults
    try:
        data = yaml.safe_load(MANGA_STYLE_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return defaults
    # ステップ41: MANGA_LAYOUT と aspect_ratio の整合補正
    if data.get("aspect_ratio") in (None, ""):
        data["aspect_ratio"] = "vertical_strip" if MANGA_LAYOUT == "vertical" else "2x2"
    merged = dict(defaults)
    merged.update(data)
    return merged


def load_world_with_viewpoint() -> dict:
    """world.yaml を読み込み、viewpoint を検証して返す"""
    if not WORLD_FILE.exists():
        return {}
    try:
        data = yaml.safe_load(WORLD_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    # viewpoint 検証
    vp = data.get("viewpoint", "third_person")
    if vp not in VALID_VIEWPOINTS:
        print(f"[WARN] 無効な viewpoint: {vp}, デフォルト 'third_person' を使用")
        data["viewpoint"] = "third_person"
    return data


# 各種ディレクトリの自動生成
for d in [OUTPUT_DIR, LOG_DIR, FINAL_DIR, PROMPTS_DIR, MANGA_PROMPTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
