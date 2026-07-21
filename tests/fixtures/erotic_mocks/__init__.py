"""tests/fixtures/erotic_mocks/__init__.py
テスト用モック官能小説の読み込みヘルパー。
"""
from pathlib import Path

MOCKS_DIR = Path(__file__).parent


def load_mock(filename: str) -> str:
    """指定されたモックファイルの内容を返す。"""
    path = MOCKS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Mock file not found: {path}")
    return path.read_text(encoding="utf-8")


def get_all_mock_names() -> list[str]:
    """利用可能なすべてのモックファイル名を返す。"""
    return [f.name for f in MOCKS_DIR.glob("*.md") if f.name != "__init__.py"]


def get_mock_metadata(text: str) -> dict:
    """モックテキストのメタデータセクションを解析する。"""
    metadata = {}
    in_metadata = False
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("## 【テスト用メタデータ】"):
            in_metadata = True
            continue
        if in_metadata:
            if line.startswith("- "):
                parts = line[2:].split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    metadata[key] = value
            elif line.startswith("---"):
                break
    return metadata


def extract_intensity_from_metadata(metadata: dict) -> int:
    """メタデータから数値の強度を抽出する。"""
    raw = metadata.get("想定強度", "")
    # "3 (官能的)" -> 3
    digits = "".join(c for c in raw if c.isdigit())
    return int(digits) if digits else 0


def count_phases(text: str) -> dict:
    """各フェーズの出現回数を数える。"""
    phases = {"BUILD": 0, "PEAK": 0, "AFTERGLOW": 0}
    for line in text.split("\n"):
        if "【BUILD フェーズ" in line:
            phases["BUILD"] += 1
        if "【PEAK フェーズ" in line:
            phases["PEAK"] += 1
        if "【AFTERGLOW フェーズ" in line:
            phases["AFTERGLOW"] += 1
    return phases


def estimate_intensity_from_text(text: str) -> int:
    """テキストの内容から推定強度を返す（簡易版）。"""
    intensity_indicators = {
        5: ["自我の消失", "溶解", "崩壊", "飽和", "限界"],
        4: ["葛藤", "背徳", "タブー", "迷い", "許容されない"],
        3: ["好き", "愛してる", "幸せ", "陶酔"],
    }

    for intensity, keywords in sorted(intensity_indicators.items(), reverse=True):
        for keyword in keywords:
            if keyword in text:
                # 否定表現の直後は除外（例: "背徳なし"）
                import re

                negated_pattern = re.compile(keyword + r"(?!.)", re.DOTALL)
                # 簡易的否定チェック: 同じ文内に「なし」「ない」が無いか確認
                if keyword + "なし" in text or keyword + "ない" in text:
                    continue
                return intensity
    return 2
