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
    from novel_50ep.count_chars import check_cliff, count_chars, extract_parts, require_words
except ImportError:
    from config import (
        OUTPUT_DIR,
        PART_TARGETS,
        PART_TOLERANCE,
        SCORES_FILE,
        TOTAL_EPISODES,
        WORLD_FILE,
    )
    from count_chars import check_cliff, count_chars, extract_parts, require_words


@dataclass
class EpisodeScore:
    ep: int
    pacing_score: float  # ステップ59: テンポ得点 (0〜1)
    emotion_score: float  # ステップ60: 感情振幅得点 (0〜1)
    world_score: float  # ステップ61: 世界観深度得点 (0〜1)
    cliff_score: float  # ステップ62: フックスコア (0〜1)
    total_score: float  # ステップ63: 総合商業スコア (0〜1)
    details: Dict[str, str]


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

    # ステップ63: score_total (上記4つの加重統合スコア 0〜1)
    def score_episode(
        self,
        ep: int,
        text: str,
        part_counts: Optional[Dict[int, int]] = None,
        tracker: Optional[Any] = None,
    ) -> EpisodeScore:
        if part_counts is None:
            part_counts = extract_parts(text)

        p_score, p_desc = self.score_pacing(part_counts)
        e_score, e_desc = self.score_emotion(text)
        w_score, w_desc = self.score_world(text)
        c_score, c_desc = self.score_cliff(text)

        # 加重平均: テンポ(30%), 感情(25%), 世界観(20%), クリフ(25%)
        # CONTINUITY_HOOK
        total = (p_score * 0.30) + (e_score * 0.25) + (w_score * 0.20) + (c_score * 0.25)
        # ステップ 65: 継続性ペナルティの反映
        if tracker is not None and hasattr(tracker, "violations") and tracker.violations:
            total -= len(tracker.violations) * 0.5

        total = round(min(1.0, max(0.0, total)), 3)

        details = {
            "pacing": p_desc,
            "emotion": e_desc,
            "world": w_desc,
            "cliff": c_desc,
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
            total_score=total,
            details=details,
        )

    # ステップ64: 全話スコア集計 (scores.csv) と目標平均0.9確認
    def score_all(self, total: int = TOTAL_EPISODES, output_csv: Path = SCORES_FILE) -> Tuple[List[EpisodeScore], float]:
        scores: List[EpisodeScore] = []
        for ep in range(1, total + 1):
            ep_file = OUTPUT_DIR / f"ep{ep:02d}.md"
            if ep_file.exists():
                text = ep_file.read_text(encoding="utf-8")
                sc = self.score_episode(ep, text)
                scores.append(sc)

        # CSV出力
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ep", "pacing", "emotion", "world", "cliff", "total_score", "evaluation"])
            for s in scores:
                eval_tag = "S (優良)" if s.total_score >= 0.90 else ("A (良好)" if s.total_score >= 0.80 else "B (要修正)")
                writer.writerow([s.ep, s.pacing_score, s.emotion_score, s.world_score, s.cliff_score, s.total_score, eval_tag])

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
        print(f"・総合スコア: {sc.total_score} (テンポ:{sc.pacing_score}, 感情:{sc.emotion_score}, 世界観:{sc.world_score}, クリフ:{sc.cliff_score})")
        for k, v in sc.details.items():
            print(f"  - {k}: {v}")
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
