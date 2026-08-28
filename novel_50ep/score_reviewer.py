"""自動レビュー・商業スコアリングモジュール (ステップ59〜64)"""

from __future__ import annotations
import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple
import yaml

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from novel_50ep.config import (
        OUTPUT_DIR,
        PART_TARGETS,
        PART_TOLERANCE,
        SCORES_FILE,
        TOTAL_EPISODES,
        WORLD_FILE,
    )
    from novel_50ep.count_chars import check_cliff, count_chars, extract_parts, require_words, calculate_style_stats, StyleStats, extract_metaphors, detect_metaphor_dup, MAX_METAPHOR_RATIO, MAX_METAPHOR_PER_EP
except ImportError:
    from config import (
        OUTPUT_DIR,
        PART_TARGETS,
        PART_TOLERANCE,
        SCORES_FILE,
        TOTAL_EPISODES,
        WORLD_FILE,
    )
    from count_chars import check_cliff, count_chars, extract_parts, require_words, calculate_style_stats, StyleStats


@dataclass
class EpisodeScore:
    ep: int
    pacing_score: float  # ステップ59: テンポ得点 (0〜1)
    emotion_score: float  # ステップ60: 感情振幅得点 (0〜1)
    world_score: float  # ステップ61: 世界観深度得点 (0〜1)
    cliff_score: float  # ステップ62: フックスコア (0〜1)
    metaphor_score: float  # Step 18: 比喩多様性得点 (0〜1)
    style_score: float  # ステップ: 文体一貫性得点 (0〜1)
    total_score: float  # ステップ63: 総合商業スコア (0〜1)
    details: Dict[str, str]
    style_details: Dict[str, str]


class ScoreReviewer:
    """エピソードの商業品質自動スコアリング"""

    def __init__(self, world_path: Path = WORLD_FILE):
        self.world_path = world_path
        self.world_data = self._load_world()

    def _load_world(self) -> dict:
        if self.world_path.exists():
            return yaml.safe_load(self.world_path.read_text(encoding="utf-8")) or {}
        return {}

    # ステップ59: score_pacing (パート文字数のバランスからテンポ得点算出)
    def score_pacing(self, part_counts: Dict[int, int]) -> Tuple[float, str]:
        if not part_counts:
            return 0.0, "パートデータなし"

        penalties = 0.0
        total_parts = len(PART_TARGETS)

        for p, target in PART_TARGETS.items():
            cnt = part_counts.get(p, 0)
            diff = abs(cnt - target)
            if diff > PART_TOLERANCE:
                # 許容公差超過分に対するペナルティ
                penalties += min(1.0, (diff - PART_TOLERANCE) / 100.0)

        # 0.0〜1.0 に正規化
        score = max(0.0, 1.0 - (penalties / total_parts))
        return round(score, 3), f"パート偏差ペナルティ: {penalties:.2f}"

    # ステップ60: score_emotion (感情語出現密度から感情振幅得点算出)
    def score_emotion(self, text: str) -> Tuple[float, str]:
        count, matched = require_words(text)
        # 基準: 感情語2個で0.8、3個以上で1.0、0個なら0.2、1個なら0.5
        if count >= 3:
            score = 1.0
        elif count == 2:
            score = 0.85
        elif count == 1:
            score = 0.50
        else:
            score = 0.20
        return round(score, 3), f"感情語出現: {count}個 ({', '.join(matched[:3])})"

    # ステップ61: score_world (symbol語等の出現回数から世界観深度得点算出)
    def score_world(self, text: str) -> Tuple[float, str]:
        symbol_raw = self.world_data.get("symbol", "光の石")
        protagonist_raw = self.world_data.get("protagonist", {}).get("name", "凛")

        # 括弧注記を除去した基本識別名
        import re
        symbol = re.sub(r"[（\(].*?[）\)]", "", symbol_raw).strip() or "光の石"
        protagonist = re.sub(r"[（\(].*?[）\)]", "", protagonist_raw).strip() or "凛"

        sym_count = text.count(symbol)
        pro_count = text.count(protagonist)

        # シンボルが1回以上、主人公が3回以上出現していれば高得点
        score = 0.5
        if sym_count >= 1:
            score += 0.25
        if sym_count >= 2:
            score += 0.15
        if pro_count >= 3:
            score += 0.10

        score = min(1.0, score)
        return round(score, 3), f"シンボル語「{symbol}」: {sym_count}回, 主人公: {pro_count}回"

    # ステップ62: score_cliff (⑦のクリフ有無＋末尾緊張感からフックスコア算出)
    def score_cliff(self, text: str, part7_text: Optional[str] = None) -> Tuple[float, str]:
        p7 = part7_text or text[-600:]
        has_cliff, matched_pat = check_cliff(p7)

        if has_cliff:
            score = 1.0
            detail = f"クリフ検出: {matched_pat}"
        else:
            score = 0.3
            detail = "クリフ未検出"
        return round(score, 3), detail

    # Step 18: score_metaphor_diversity (比喩多様性得点)
    def score_metaphor_diversity(self, text: str) -> Tuple[float, str]:
        import re
        from novel_50ep.count_chars import extract_metaphors, detect_metaphor_dup
        metaphors = extract_metaphors(text)
        metaphor_count = len(metaphors)
        dup_found, dup_details = detect_metaphor_dup(text)
        type_counts = {}
        for m in metaphors:
            # パターン種類を判定
            if re.search(r"(ようだ|ような|のように)", m):
                type_counts["ようだ類"] = type_counts.get("ようだ類", 0) + 1
            elif re.search(r"(に似て|に酷似)", m):
                type_counts["に似て"] = type_counts.get("に似て", 0) + 1
            elif "といった" in m:
                type_counts["といった"] = type_counts.get("といった", 0) + 1
            elif "のごとく" in m:
                type_counts["のごとく"] = type_counts.get("のごとく", 0) + 1
        
        # 多様性スコア: 種類数 / max(種類数) * 比喩率適正度
        num_types = len(type_counts)
        ratio_score = 1.0
        if metaphor_count > 0:
            ratio = metaphor_count / max(1, len(text) / 100)
            if ratio > MAX_METAPHOR_RATIO:
                ratio_score = 0.5
            if metaphor_count > MAX_METAPHOR_PER_EP:
                ratio_score = 0.3
        
        # 種類数ボーナス（最大4種類で1.0）
        type_score = min(1.0, num_types / 4.0)
        
        # 重複ペナルティ
        dup_penalty = 0.0
        if dup_found:
            dup_penalty = 0.3
        
        score = (type_score * 0.6 + ratio_score * 0.4) * (1.0 - dup_penalty)
        detail = f"比喩:{metaphor_count}個, 種類:{num_types}, 重複:{'あり' if dup_found else 'なし'}"
        return round(score, 3), detail

    # ステップ: score_style_consistency (文体統計の移動平均から外れ値検出)
    def score_style_consistency(
        self,
        ep: int,
        text: str,
        prev_scores: List["EpisodeScore"],
    ) -> Tuple[float, Dict[str, str]]:
        """直前5話の移動平均から文体外れ値を検出しスコア化（0.0〜1.0）"""
        # 当該話の文体統計を計算
        curr_stats = calculate_style_stats(text)
        # 計算用の詳細情報（数値形式）
        details = {
            "avg_sentence_length": curr_stats.avg_sentence_length,
            "plain_form_ratio": curr_stats.plain_form_ratio,
            "unique_word_count": curr_stats.unique_word_count,
            "sentence_count": curr_stats.sentence_count,
        }
# 直前5話（ep-5 〜 ep-1）の統計を収集
        window_scores = [s for s in prev_scores if ep - 5 <= s.ep < ep]
        if len(window_scores) == 0:
            # 比較対象がない場合は満点
            raw_details = {
                "avg_sentence_length": curr_stats.avg_sentence_length,
                "plain_form_ratio": curr_stats.plain_form_ratio,
                "unique_word_count": curr_stats.unique_word_count,
                "sentence_count": curr_stats.sentence_count,
            }
            return 1.0, {
                "avg_sentence_length": f"{curr_stats.avg_sentence_length:.1f}",
                "plain_form_ratio": f"{curr_stats.plain_form_ratio:.1%}",
                "unique_word_count": str(curr_stats.unique_word_count),
                "sentence_count": str(curr_stats.sentence_count),
                "note": "No previous episodes for comparison",
            }, raw_details

        # 移動平均・標準偏差を計算（各指標ごと）
        import statistics

        def calc_mean_std(values: List[float]) -> Tuple[float, float]:
            if len(values) < 2:
                return values[0] if values else 0.0, 0.0
            return statistics.mean(values), statistics.stdev(values)

        prev_avg_len = [s.style_details.get("avg_sentence_length", 0.0) for s in window_scores]
        prev_plain_ratio = [s.style_details.get("plain_form_ratio", 0.0) for s in window_scores]
        prev_unique_words = [s.style_details.get("unique_word_count", 0) for s in window_scores]

        # デフォルト値でないことを確認（0.0 の場合は実際の値を取得しようとする）
        # ただし、まだ数値を格納していない過去のスコアがある場合のフォールバック
        if all(v == 0.0 for v in prev_avg_len):
            # フォールバック: 形式付き文字列から数値を抽出（後方互換性のため）
            prev_avg_len = []
            for s in window_scores:
                val = s.style_details.get("avg_sentence_length", 0.0)
                if isinstance(val, (int, float)):
                    prev_avg_len.append(float(val))
                else:
                    val_str = str(val)
                    # "35.2 (移動平均: 35.2±0.1)" などから最初の数値を抽出
                    import re
                    match = re.search(r"[\d.]+", val_str)
                    if match:
                        prev_avg_len.append(float(match.group()))
                    else:
                        prev_avg_len.append(0.0)
        
        if all(v == 0.0 for v in prev_plain_ratio):
            prev_plain_ratio = []
            for s in window_scores:
                val = s.style_details.get("plain_form_ratio", 0.0)
                if isinstance(val, (int, float)):
                    prev_plain_ratio.append(float(val))
                else:
                    val_str = str(val)
                    # "0.0%" や "85.0%" から数値を抽出
                    val_str = val_str.rstrip('%')
                    try:
                        prev_plain_ratio.append(float(val_str))
                    except ValueError:
                        prev_plain_ratio.append(0.0)
                    
        if all(v == 0 for v in prev_unique_words):
            prev_unique_words = []
            for s in window_scores:
                val = s.style_details.get("unique_word_count", 0)
                if isinstance(val, (int, float)):
                    prev_unique_words.append(int(val))
                else:
                    try:
                        prev_unique_words.append(int(val))
                    except ValueError:
                        prev_unique_words.append(0)

        mean_len, std_len = calc_mean_std(prev_avg_len)
        mean_plain, std_plain = calc_mean_std(prev_plain_ratio)
        mean_unique, std_unique = calc_mean_std(prev_unique_words)

        # フラグ初期化
        avg_len_outlier = False
        plain_ratio_outlier = False
        unique_count_outlier = False
        avg_len_target_dev = False
        plain_ratio_target_dev = False
        unique_count_target_dev = False

        # 外れ値判定（移動平均 ± 2σ）
        penalties = 0.0
        # 平均文長チェック
        if std_len > 0 and abs(curr_stats.avg_sentence_length - mean_len) > 2 * std_len:
            penalties += 0.3
            avg_len_outlier = True
        # 常体率チェック
        if std_plain > 0 and abs(curr_stats.plain_form_ratio - mean_plain) > 2 * std_plain:
            penalties += 0.3
            plain_ratio_outlier = True
        # ユニーク語数チェック
        if std_unique > 0 and abs(curr_stats.unique_word_count - mean_unique) > 2 * std_unique:
            penalties += 0.2
            unique_count_outlier = True

        # 基準値（style_guide）との乖離もチェック
        style_guide = self.world_data.get("style_guide", {})
        target_len = style_guide.get("avg_sentence_length", 45)
        target_plain = 1.0 if style_guide.get("tone") == "常体" else 0.0
        target_unique = style_guide.get("unique_words_target", 180)

        if abs(curr_stats.avg_sentence_length - target_len) > 15:
            penalties += 0.1
            avg_len_target_dev = True
        if target_plain == 1.0 and curr_stats.plain_form_ratio < 0.8:
            penalties += 0.1
            plain_ratio_target_dev = True
        if curr_stats.unique_word_count < target_unique * 0.7:
            penalties += 0.1
            unique_count_target_dev = True

        score = max(0.0, 1.0 - penalties)
        # 返却用詳細情報を構築（文字列形式）
        return_details = {
            "avg_sentence_length": f"{details['avg_sentence_length']:.1f}",
            "plain_form_ratio": f"{details['plain_form_ratio']:.1%}",
            "unique_word_count": str(details['unique_word_count']),
            "sentence_count": str(details['sentence_count']),
        }
        # サフィックスを適用
        if avg_len_outlier:
            return_details["avg_sentence_length"] += " [OUTLIER]"
        if plain_ratio_outlier:
            return_details["plain_form_ratio"] += " [OUTLIER]"
        if unique_count_outlier:
            return_details["unique_word_count"] += " [OUTLIER]"
        if avg_len_target_dev:
            return_details["avg_sentence_length"] += " [TARGET_DEV]"
        if plain_ratio_target_dev:
            return_details["plain_form_ratio"] += " [TARGET_DEV]"
        if unique_count_target_dev:
            return_details["unique_word_count"] += " [TARGET_DEV]"
        return round(score, 3), return_details, details

    # ステップ63: score_total (上記5つの加重統合スコア 0〜1)
    def score_episode(
        self,
        ep: int,
        text: str,
        part_counts: Optional[Dict[int, int]] = None,
        tracker: Optional[Any] = None,
        use_prototype_scorer: bool = False,
        prev_scores: Optional[List["EpisodeScore"]] = None,
    ) -> EpisodeScore:
        if use_prototype_scorer:
            try:
                from src.prototype.score_adapter import PrototypeScorer

                scorer = PrototypeScorer()
                return scorer.score_sync(ep, text)
            except Exception:
                pass

        if part_counts is None:
            part_counts = extract_parts(text)

        p_score, p_desc = self.score_pacing(part_counts)
        e_score, e_desc = self.score_emotion(text)
        w_score, w_desc = self.score_world(text)
        c_score, c_desc = self.score_cliff(text)
        m_score, m_desc = self.score_metaphor_diversity(text)

        # 文体一貫性スコア計算
        if prev_scores is None:
            prev_scores = []
        style_score, style_details, raw_style_details = self.score_style_consistency(ep, text, prev_scores)

        # 加重平均: テンポ(22%), 感情(18%), 世界観(14%), クリフ(18%), 文体(18%), 比喩(10%)
        # CONTINUITY_HOOK
        total = (
            p_score * 0.22
            + e_score * 0.18
            + w_score * 0.14
            + c_score * 0.18
            + style_score * 0.18
            + m_score * 0.10
        )
        # ステップ 65: 継続性ペナルティの反映
        if tracker is not None and hasattr(tracker, "violations") and tracker.violations:
            total -= len(tracker.violations) * 0.5

        total = round(min(1.0, max(0.0, total)), 3)

        details = {
            "pacing": p_desc,
            "emotion": e_desc,
            "world": w_desc,
            "cliff": c_desc,
            "metaphor": m_desc,
        }
        # ステップ 66: レポートにセクション追加
        if tracker is not None and hasattr(tracker, "report"):
            details["continuity_issues"] = tracker.report()

        return EpisodeScore(
            ep=ep,
            pacing_score=p_score,
            emotion_score=e_score,
            world_score=w_score,
            cliff_score=c_score,
            metaphor_score=m_score,
            style_score=style_score,
            total_score=total,
            details=details,
            style_details=raw_style_details,
        )

    score = score_episode

    # ステップ64: 全話スコア集計 (scores.csv) と目標平均0.9確認
    def score_all(self, total: int = TOTAL_EPISODES, output_csv: Path = SCORES_FILE) -> Tuple[List[EpisodeScore], float]:
        scores: List[EpisodeScore] = []
        for ep in range(1, total + 1):
            ep_file = OUTPUT_DIR / f"ep{ep:02d}.md"
            if ep_file.exists():
                text = ep_file.read_text(encoding="utf-8")
                sc = self.score_episode(ep, text, prev_scores=scores)
                scores.append(sc)

# CSV出力
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ep", "pacing", "emotion", "world", "cliff", "metaphor", "style", "total_score", "evaluation"])
            for s in scores:
                eval_tag = "S (優良)" if s.total_score >= 0.90 else ("A (良好)" if s.total_score >= 0.80 else "B (要修正)")
                writer.writerow([s.ep, s.pacing_score, s.emotion_score, s.world_score, s.cliff_score, s.metaphor_score, s.style_score, s.total_score, eval_tag])

        avg_total = sum(s.total_score for s in scores) / len(scores) if scores else 0.0
        return scores, round(avg_total, 3)


def main():
    parser = argparse.ArgumentParser(description="50話 自動レビュー・商業スコアリングツール")
    parser.add_argument("--ep", type=int, default=None, help="特定話数のスコアのみ表示")
    parser.add_argument("--all", action="store_true", help="全50話のスコアを集計し scores.csv を出力")
    args = parser.parse_args()

    reviewer = ScoreReviewer()

    if args.ep is not None:
        ep_file = OUTPUT_DIR / f"ep{args.ep:02d}.md"
        if not ep_file.exists():
            print(f"エラー: 第{args.ep}話のファイルが見つかりません。")
            return
        text = ep_file.read_text(encoding="utf-8")
        sc = reviewer.score_episode(args.ep, text)
        print(f"=== 第{args.ep}話 商業レビュースコア ===")
        print(f"・総合スコア: {sc.total_score} (テンポ:{sc.pacing_score}, 感情:{sc.emotion_score}, 世界観:{sc.world_score}, クリフ:{sc.cliff_score}, 文体:{sc.style_score})")
        for k, v in sc.details.items():
            print(f"  - {k}: {v}")
        if sc.style_details:
            print("・文体詳細:")
            # 生の数値を整形して表示
            sd = sc.style_details
            print(f"  - avg_sentence_length: {sd.get('avg_sentence_length', 0.0):.1f}")
            print(f"  - plain_form_ratio: {sd.get('plain_form_ratio', 0.0):.1%}")
            print(f"  - unique_word_count: {sd.get('unique_word_count', 0)}")
            print(f"  - sentence_count: {sd.get('sentence_count', 0)}")
    else:
        scores, avg_score = reviewer.score_all()
        print(f"=== 全話スコアリング完了 (集計: {len(scores)}話) ===")
        print(f"・平均総合スコア: {avg_score} (目標基準: 0.90以上)")
        if avg_score >= 0.90:
            print("[PASS] 目標商業スコア 0.90 以上を達成しました！")
        else:
            print("[WARN] 平均スコアが0.90未満です。低スコア話の推敲・微調整を推奨します。")
        print(f"・詳細結果を {SCORES_FILE} に書き出しました。")


if __name__ == "__main__":
    main()
