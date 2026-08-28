"""文字数・品質チェックツール (ステップ19〜27)"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re
import sys
from typing import Dict, List, Optional, Tuple, Union

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from novel_50ep.config import (
        CLIFFS_FILE,
        EMOTIONS_FILE,
        MAX_CHARS,
        MIN_CHARS,
        PART_TARGETS,
        PART_TOLERANCE,
        TARGET_CHARS,
    )
except ImportError:
    from config import (
        CLIFFS_FILE,
        EMOTIONS_FILE,
        MAX_CHARS,
        MIN_CHARS,
        PART_TARGETS,
        PART_TOLERANCE,
        TARGET_CHARS,
    )


METAPHOR_PATTERNS: List[str] = [
    r"まるで[^。！？]*?(?:ようだ|ような|ような気がする|のように見える|のように)",
    r"[^。！？]*?(?:のようだ|のように見える|のように|のようで|のような)",
    r"[^。！？]*?(?:に似て|に酷似)",
    r"[^。！？]*?といった",
    r"[^。！？]*?のごとく",
]

MAX_METAPHOR_RATIO: float = 0.15
MAX_METAPHOR_PER_EP: int = 4


@dataclass
class MetaphorResult:
    count: int
    type_counts: Dict[str, int]
    dup_found: bool
    dup_details: List[str]
    ratio: float


@dataclass
class ValidationResult:
    is_valid: bool
    total_chars: int
    part_chars: Dict[int, int]
    emotion_count: int
    matched_emotions: List[str]
    has_cliff: bool
    matched_cliff: Optional[str]
    dup_found: bool
    dup_details: List[str]
    metaphor_count: int = 0
    metaphor_types: Dict[str, int] = field(default_factory=dict)
    metaphor_dup_found: bool = False
    metaphor_dup_details: List[str] = field(default_factory=list)
    metaphor_ratio: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        status_str = "【合格 (PASSED)】" if self.is_valid else "【不合格 (FAILED)】"
        lines = [
            f"=== エピソード品質判定結果: {status_str} ===",
            f"・総文字数: {self.total_chars}字 (目標: {TARGET_CHARS}字 / 許容: {MIN_CHARS}〜{MAX_CHARS}字)",
            f"・感情語出現数: {self.emotion_count}個 (一致: {', '.join(self.matched_emotions) if self.matched_emotions else 'なし'})",
            f"・クリフハンガー: {'検出済み (' + str(self.matched_cliff) + ')' if self.has_cliff else '未検出'}",
            f"・連続重複表現: {'検出あり' if self.dup_found else 'なし'}",
            f"・比喩出現数: {self.metaphor_count}個 (率: {self.metaphor_ratio:.1%}, 重複: {'あり' if self.metaphor_dup_found else 'なし'})",
            "・パート別文字数内訳:",
        ]
        for p, count in sorted(self.part_chars.items()):
            target = PART_TARGETS.get(p, 0)
            p_min = target - PART_TOLERANCE
            p_max = target + PART_TOLERANCE
            p_ok = p_min <= count <= p_max
            tag = "OK" if p_ok else "NG"
            lines.append(f"  - パート{p}: {count}字 (目標: {target}±{PART_TOLERANCE}字 [{p_min}〜{p_max}]) [{tag}]")

        if self.errors:
            lines.append("・不合格エラー理由:")
            for err in self.errors:
                lines.append(f"  [FAIL] {err}")

        if self.warnings:
            lines.append("・警告事項:")
            for warn in self.warnings:
                lines.append(f"  [WARN] {warn}")

        return "\n".join(lines)


# =========================================================================
# 文体統計計算 (長編トーン・文体ズレ対策)
# =========================================================================

@dataclass
class StyleStats:
    """文体統計データクラス"""
    avg_sentence_length: float    # 平均文長（文字）
    plain_form_ratio: float       # 常体率 (0.0〜1.0)
    unique_word_count: int        # ユニーク語数
    sentence_count: int           # 文数
    total_chars: int              # 総文字数


def _split_words(text: str) -> List[str]:
    """簡易単語分割（形態素解析なし・正規表現ベース・低性能LLM対応）"""
    # ひらがな・カタカナ・漢字・英数字の連続を単語とみなす
    # 記号・句読点・空白で分割
    words = re.findall(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\uFF66-\uFF9F\u0030-\u0039\u0041-\u005A\u0061-\u007A]+", text)
    # 1文字のみの助詞・助動詞等は除外（より実態に近いユニーク語数にするため）
    words = [w for w in words if len(w) >= 2]
    return words


def _split_sentences(text: str) -> List[str]:
    """文分割（句点・感嘆符・疑問符で分割）"""
    sentences = re.split(r"[。！？]", text)
    return [s.strip() for s in sentences if s.strip()]


def calculate_style_stats(text: str) -> StyleStats:
    """文体統計を計算する（低性能LLM環境でも動作する簡易実装）"""
    if not text:
        return StyleStats(
            avg_sentence_length=0.0,
            plain_form_ratio=0.0,
            unique_word_count=0,
            sentence_count=0,
            total_chars=0,
        )

    # 総文字数
    total_chars = len(text)

    # 文分割
    sentences = _split_sentences(text)
    sentence_count = len(sentences)

    if sentence_count == 0:
        return StyleStats(
            avg_sentence_length=0.0,
            plain_form_ratio=0.0,
            unique_word_count=0,
            sentence_count=0,
            total_chars=total_chars,
        )

    # 平均文長
    avg_sentence_length = total_chars / sentence_count

    # 常体率計算（文末が「だ。」「である。」「た。」で終わる文の割合）
    plain_endings = ("だ。", "である。", "た。")
    plain_count = sum(1 for s in sentences if s.endswith(plain_endings))
    plain_form_ratio = plain_count / sentence_count

    # ユニーク語数（簡易単語分割＋重複除去）
    words = _split_words(text)
    unique_words = set(words)
    unique_word_count = len(unique_words)

    return StyleStats(
        avg_sentence_length=round(avg_sentence_length, 1),
        plain_form_ratio=round(plain_form_ratio, 3),
        unique_word_count=unique_word_count,
        sentence_count=sentence_count,
        total_chars=total_chars,
    )


# ステップ19: count_chars
def count_chars(target: Union[str, Path]) -> int:
    """引数のファイルまたは文字列の文字数をカウントして返す（改行・空白のみの行間調整を考慮）"""
    if isinstance(target, Path) or (isinstance(target, str) and Path(target).is_file()):
        content = Path(target).read_text(encoding="utf-8")
    else:
        content = str(target)

    # 改行や空白を除外せず、小説本文としての文字数をカウント (CRLF正規化)
    normalized = content.replace("\r\n", "\n").strip()
    # 完全に空行だけの連続を取り除いた実質文字数
    return len(re.sub(r"\s+", "", normalized))


# ステップ20: check_range
def check_range(count: int, min_val: int = MIN_CHARS, max_val: int = MAX_CHARS) -> bool:
    """MIN〜MAX 内なら True を返す"""
    return min_val <= count <= max_val


# ステップ21: extract_parts
def extract_parts(data: Union[str, Path, Dict[int, str]]) -> Dict[int, int]:
    """結合前/結合後の各パート文字数を個別表示・抽出する"""
    if isinstance(data, dict):
        return {part_id: count_chars(text) for part_id, text in data.items()}

    file_path: Optional[Path] = None
    if isinstance(data, Path) or (isinstance(data, str) and Path(data).is_file()):
        file_path = Path(data)
        content = file_path.read_text(encoding="utf-8")
    else:
        content = str(data)

    # もし同ディレクトリに epNN_raw.md や epNN_pX.txt があればそれを参照
    if file_path and file_path.suffix == ".md":
        raw_neighbor = file_path.parent / file_path.name.replace(".md", "_raw.md")
        if raw_neighbor.exists() and raw_neighbor != file_path:
            raw_content = raw_neighbor.read_text(encoding="utf-8")
            if "<!-- PART:" in raw_content:
                content = raw_content

    parts: Dict[int, int] = {}
    # パート区切りタグ <!-- PART:X --> または ## パートX がある場合
    part_blocks = re.split(r"(?:<!--\s*PART:(\d+)\s*-->|##\s*パート(?:[①-⑦]|\d+))", content)
    if len(part_blocks) > 1:
        # split結果のパース
        current_part = 1
        for i in range(1, len(part_blocks), 2):
            p_num = int(part_blocks[i]) if part_blocks[i] and part_blocks[i].isdigit() else current_part
            p_text = part_blocks[i + 1] if i + 1 < len(part_blocks) else ""
            parts[p_num] = count_chars(p_text)
            current_part += 1
    else:
        # 空行区切りで7つ前後の段落ブロックがある場合
        blocks = [b.strip() for b in content.split("\n\n") if b.strip() and not b.strip().startswith("第") and not b.strip().startswith("#")]
        if len(blocks) == 7:
            for idx, blk in enumerate(blocks, 1):
                parts[idx] = count_chars(blk)
        elif len(blocks) > 7:
            # 7パートに均等配分
            chunk_size = len(blocks) / 7.0
            for p in range(1, 8):
                start_i = int((p - 1) * chunk_size)
                end_i = int(p * chunk_size) if p < 7 else len(blocks)
                p_text = "\n\n".join(blocks[start_i:end_i])
                parts[p] = count_chars(p_text)
        else:
            # 段落数が少ない場合は目標比率で按分
            total_c = count_chars(content)
            for p, target in PART_TARGETS.items():
                parts[p] = int(total_c * (target / 3000.0))

    return parts


# ステップ22: require_words
def require_words(text: str, word_list: Optional[List[str]] = None) -> Tuple[int, List[str]]:
    """感情語リストの出現数をカウントする（Step 7: 同一語3回超え警告・最低3種以上）"""
    if word_list is None:
        if EMOTIONS_FILE.exists():
            word_list = [w.strip() for w in EMOTIONS_FILE.read_text(encoding="utf-8").splitlines() if w.strip()]
        else:
            word_list = ["喜悦", "恐怖", "決意", "不安", "希望", "驚愕", "歓喜", "焦燥", "絶望", "哀惜", "慈愛", "安堵", "戦慄", "高揚", "疑惑"]

    matched = []
    total_matches = 0
    type_count = 0
    for word in word_list:
        cnt = text.count(word)
        if cnt > 0:
            type_count += 1
            if cnt > 3:
                matched.append(f"{word}({cnt})[WARN: 3回超え]")
            else:
                matched.append(f"{word}({cnt})")
            total_matches += cnt

    # 種別数チェック（3種未満なら警告相当）
    if type_count < 3:
        matched.append(f"[種別不足: {type_count}種]")

    return total_matches, matched


# ステップ23: check_cliff
def check_cliff(part7_text: str, patterns: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """パート⑦にクリフパターン文字列または類似キー表現が含まれるか確認する"""
    if patterns is None:
        if CLIFFS_FILE.exists():
            patterns = [p.strip() for p in CLIFFS_FILE.read_text(encoding="utf-8").splitlines() if p.strip()]
        else:
            patterns = ["染まり、脈打ち始めた", "冷酷な嗤い声", "崩落し始めた", "通信が途絶した", "鍵を差し込んだ", "肉親その人だった", "静かに眼を見開いた", "紋章が浮かび上がった", "向けられていた", "第二の月"]

    # 完全一致またはキーワード一致
    for pat in patterns:
        # パターンのコア部分（20字程度）が含まれているかチェック
        core_tokens = [t for t in re.findall(r"[\u4e00-\u9fa5\u3040-\u309f]{3,}", pat)]
        if pat in part7_text:
            return True, pat
        # 複数コアトークンの一致
        matched_tokens = [tok for tok in core_tokens if tok in part7_text]
        if len(core_tokens) > 0 and len(matched_tokens) >= max(1, len(core_tokens) - 1):
            return True, f"近似一致: {pat[:15]}..."

    # クリフハンガー特有のフック文末表現の簡易検出
    cliff_endings = ["始めた。", "途絶した。", "見開いた。", "向けられていた。", "浮かび上がった。", "だった。"]
    for ending in cliff_endings:
        if part7_text.strip().endswith(ending):
            return True, f"文末フック検出 ({ending})"

    return False, None


# ステップ24: detect_dup
def detect_dup(text: str, max_repeat: int = 3) -> Tuple[bool, List[str]]:
    """同一表現や同一行が3回以上連続していないか調べる"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    duplicates: List[str] = []

    # 1. 行単位の連続重複
    repeat_count = 1
    for i in range(1, len(lines)):
        if lines[i] == lines[i - 1]:
            repeat_count += 1
            if repeat_count >= max_repeat:
                duplicates.append(f"行の連続重複({repeat_count}回): 『{lines[i][:20]}...』")
        else:
            repeat_count = 1

    # 2. 短文・フレーズ単位の連続重複 (例: 「だ。だ。だ。」や同一センテンス)
    sentences = re.split(r"[。！？]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 4]
    repeat_s = 1
    for i in range(1, len(sentences)):
        if sentences[i] == sentences[i - 1]:
            repeat_s += 1
            if repeat_s >= max_repeat:
                duplicates.append(f"文の連続重複({repeat_s}回): 『{sentences[i][:20]}...』")
        else:
            repeat_s = 1

    return len(duplicates) > 0, duplicates


# ステップ27: extract_metaphors
def extract_metaphors(text: str) -> List[str]:
    """比喩構文に一致する句を抽出する"""
    found: List[str] = []
    for pat in METAPHOR_PATTERNS:
        matches = re.findall(pat, text)
        found.extend(matches)
    return found


# ステップ28: count_metaphor_types
def count_metaphor_types(text: str) -> Dict[str, int]:
    """パターン別の比喩出現回数を集計する"""
    counts: Dict[str, int] = {}
    # パターン→表示名のマッピング
    pattern_names = {
        0: "ようだ類",
        1: "のようだ類",
        2: "に似て",
        3: "といった",
        4: "のごとく",
    }
    for i, pat in enumerate(METAPHOR_PATTERNS):
        matches = re.findall(pat, text)
        if matches:
            counts[pattern_names.get(i, f"pattern_{i}")] = len(matches)
    return counts


# ステップ29: detect_metaphor_dup
def detect_metaphor_dup(text: str) -> Tuple[bool, List[str]]:
    """比喩の核（名詞部分）が重複していないか検出する"""
    metaphors = extract_metaphors(text)
    cores: List[str] = []
    for m in metaphors:
        # より精密な核抽出: 「まるで/あたかも」以降から比喩マーカー手前まで
        core_match = re.search(r"(?:まるで|あたかも)?([^のにと]{2,20}?)(?:のようだ|ような|に似て|といった|のごとく)", m)
        if core_match:
            core = core_match.group(1).strip()
            # 助詞で終わる場合は除去
            core = re.sub(r"[がをのはにと]$", "", core)
            if len(core) >= 2:
                cores.append(core)
    dup_cores = [c for c in set(cores) if cores.count(c) > 1]
    details = [f"比喩核重複: 『{c}』" for c in dup_cores]
    return len(details) > 0, details


# ステップ25 & 26: validate_episode
def validate_episode(
    data: Union[str, Path, Dict[int, str]],
    part7_text_override: Optional[str] = None,
) -> ValidationResult:
    """
    上記全チェックをまとめて実行し合否を返す。
    不合格時は「どのパートが短いか/長すぎるか」を明示する。
    """
    part_texts: Dict[int, str] = {}
    full_text = ""

    if isinstance(data, dict):
        part_texts = data
        full_text = "\n\n".join(part_texts.values())
        part_counts = {p: count_chars(t) for p, t in part_texts.items()}
    elif isinstance(data, Path) or (isinstance(data, str) and Path(data).is_file()):
        full_text = Path(data).read_text(encoding="utf-8")
        part_counts = extract_parts(full_text)
    else:
        full_text = str(data)
        part_counts = extract_parts(full_text)

    total_c = count_chars(full_text)
    errors: List[str] = []
    warnings: List[str] = []

    # 1. 総文字数判定 (ステップ20)
    if not check_range(total_c, MIN_CHARS, MAX_CHARS):
        if total_c < MIN_CHARS:
            errors.append(f"総文字数({total_c}字)が下限({MIN_CHARS}字)を下回っています（不足: {MIN_CHARS - total_c}字）。")
        else:
            errors.append(f"総文字数({total_c}字)が上限({MAX_CHARS}字)を超過しています（超過: {total_c - MAX_CHARS}字）。")

    # 2. 各パート文字数判定 (ステップ26: どのパートが短いか明示)
    for p, target in PART_TARGETS.items():
        if p in part_counts:
            cnt = part_counts[p]
            p_min = target - PART_TOLERANCE
            p_max = target + PART_TOLERANCE
            if cnt < p_min:
                errors.append(f"パート{p}の文字数({cnt}字)が許容下限({p_min}字)を下回っています（不足: {p_min - cnt}字）。")
            elif cnt > p_max:
                warnings.append(f"パート{p}の文字数({cnt}字)が許容上限({p_max}字)を超過しています（超過: {cnt - p_max}字）。")
        elif len(part_counts) == 7:
            errors.append(f"パート{p}のデータが存在しません。")

    # 3. 感情語判定 (ステップ22)
    em_count, matched_emotions = require_words(full_text)
    if em_count < 2:
        errors.append(f"感情語の出現数({em_count}個)が必須基準(2個以上)を満たしていません。")

    # 4. クリフハンガー判定 (ステップ23)
    p7_text = part_texts.get(7, full_text[-600:] if len(full_text) >= 600 else full_text)
    if part7_text_override:
        p7_text = part7_text_override
    has_cliff, matched_cliff = check_cliff(p7_text)
    if not has_cliff:
        errors.append("パート⑦にクリフハンガーパターンが検出されませんでした。")

    # 5. 重複判定 (ステップ24)
    dup_found, dup_details = detect_dup(full_text)
    if dup_found:
        errors.append(f"同一表現の連続重複が検出されました: {'; '.join(dup_details)}")

    # 6. 比喩テンプレ化判定 (ステップ27-29)
    metaphors = extract_metaphors(full_text)
    metaphor_count = len(metaphors)
    metaphor_types = count_metaphor_types(full_text)
    metaphor_dup_found, metaphor_dup_details = detect_metaphor_dup(full_text)
    metaphor_ratio = metaphor_count / max(1, len(full_text) / 100) if full_text else 0.0

    if metaphor_ratio > MAX_METAPHOR_RATIO:
        warnings.append(f"比喩率({metaphor_ratio:.1%})が閾値({MAX_METAPHOR_RATIO:.0%})を超過しています。")
    if metaphor_count > MAX_METAPHOR_PER_EP:
        warnings.append(f"比喩出現数({metaphor_count}個)が上限({MAX_METAPHOR_PER_EP}個)を超過しています。")
    if metaphor_dup_found:
        errors.append(f"比喩表現の核が重複しています: {'; '.join(metaphor_dup_details)}")

    is_valid = len(errors) == 0

    return ValidationResult(
        is_valid=is_valid,
        total_chars=total_c,
        part_chars=part_counts,
        emotion_count=em_count,
        matched_emotions=matched_emotions,
        has_cliff=has_cliff,
        matched_cliff=matched_cliff,
        dup_found=dup_found,
        dup_details=dup_details,
        metaphor_count=metaphor_count,
        metaphor_types=metaphor_types,
        metaphor_dup_found=metaphor_dup_found,
        metaphor_dup_details=metaphor_dup_details,
        metaphor_ratio=metaphor_ratio,
        errors=errors,
        warnings=warnings,
    )


def main():
    parser = argparse.ArgumentParser(description="50話×3000文字 小説エピソード文字数・品質チェッカー")
    parser.add_argument("file_path", type=str, help="検証するエピソードファイルパス (例: output/ep01.md)")
    parser.add_argument("--details", action="store_true", help="詳細ログを表示")
    parser.add_argument("--metaphor", action="store_true", help="比喩テンプレ化チェックのみ実行")
    args = parser.parse_args()

    target_path = Path(args.file_path)
    if not target_path.exists():
        print(f"エラー: ファイルが見つかりません: {target_path}")
        return

    if args.metaphor:
        text = target_path.read_text(encoding="utf-8")
        metaphors = extract_metaphors(text)
        types = count_metaphor_types(text)
        dup, dup_details = detect_metaphor_dup(text)
        ratio = len(metaphors) / max(1, len(text) / 100) if text else 0.0
        print(f"=== 比喩テンプレ化チェック ===")
        print(f"・総比喩数: {len(metaphors)}個")
        print(f"・比喩率: {ratio:.1%}")
        print(f"・タイプ別: {types}")
        print(f"・重複核: {dup_details if dup else 'なし'}")
        for m in metaphors:
            print(f"  - {m}")
        return

    result = validate_episode(target_path)
    print(result.summary())


if __name__ == "__main__":
    main()
