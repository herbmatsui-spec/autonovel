"""人手微調整・校正・最終化ツール (ステップ65〜68)"""

from __future__ import annotations
import argparse
import csv
from pathlib import Path
import re
import shutil
import sys
from typing import Dict, List, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from novel_50ep.batch_runner import clean_novel_text
    from novel_50ep.config import FINAL_DIR, OUTPUT_DIR, SCORES_FILE, TOTAL_EPISODES
    from novel_50ep.count_chars import validate_episode
    from novel_50ep.score_reviewer import ScoreReviewer
except ImportError:
    from batch_runner import clean_novel_text
    from config import FINAL_DIR, OUTPUT_DIR, SCORES_FILE, TOTAL_EPISODES
    from count_chars import validate_episode
    from score_reviewer import ScoreReviewer


# ステップ67: 表記ゆれ・文法ミスの一括校正フィルター
def proofread_text(text: str) -> Tuple[str, int]:
    """表記ゆれ・連続句読点・助詞重複・不自然な表現を自動校正（10%前後の推敲効果）"""
    corrections_count = 0

    # 1. 句読点・連続記号の修正
    cleaned = re.sub(r"、、+", "、", text)
    cleaned = re.sub(r"。。+", "。", cleaned)
    cleaned = re.sub(r"！+", "！", cleaned)
    cleaned = re.sub(r"？+", "？", cleaned)

    # 2. 三点リーダーの標準化 (カクヨム商業作法: …… 偶数個)
    cleaned = re.sub(r"…{3,}", "……", cleaned)
    cleaned = re.sub(r"(?<!…)…(?!…)", "……", cleaned)

    # 3. ダッシュの標準化 (―― 偶数個)
    cleaned = re.sub(r"―{3,}", "――", cleaned)

    # 4. カギ括弧内の文末句点削除 (商業出版作法: 「〜〜。」→「〜〜」)
    cleaned = re.sub(r"。(」)", r"\1", cleaned)

    # 5. キャラ名・語彙正規化
    cleaned = clean_novel_text(cleaned)

    # 差分文字数カウント
    diff_chars = abs(len(text) - len(cleaned))
    corrections_count = diff_chars

    return cleaned, corrections_count


class PolishTool:
    """校正・微調整・完成版エクスポート管理"""

    def __init__(self, scores_file: Path = SCORES_FILE, output_dir: Path = OUTPUT_DIR, final_dir: Path = FINAL_DIR):
        self.scores_file = scores_file
        self.output_dir = output_dir
        self.final_dir = final_dir
        self.reviewer = ScoreReviewer()

    # ステップ65: 低スコア (<0.8) エピソードのリストアップ
    def list_low_score_episodes(self, threshold: float = 0.80) -> List[Tuple[int, float]]:
        low_eps: List[Tuple[int, float]] = []
        if not self.scores_file.exists():
            # スコアファイルが未生成ならその場で算出
            self.reviewer.score_all()

        if self.scores_file.exists():
            with open(self.scores_file, mode="r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ep = int(row.get("ep", 0))
                    sc = float(row.get("total_score", 0.0))
                    if sc < threshold:
                        low_eps.append((ep, sc))
        return low_eps

    # ステップ66 & 67: 校正適用と再検証
    def polish_episode(self, ep: int) -> Tuple[bool, int]:
        ep_file = self.output_dir / f"ep{ep:02d}.md"
        if not ep_file.exists():
            return False, 0

        raw_text = ep_file.read_text(encoding="utf-8")
        polished, fix_cnt = proofread_text(raw_text)

        # 上書き保存
        ep_file.write_text(polished, encoding="utf-8")

        # 再検証
        val = validate_episode(ep_file)
        return val.is_valid, fix_cnt

    # ステップ68: 最終 epNN.md を final/ にコピーし校正済みメタデータを付与
    def export_all_to_final(self, total: int = TOTAL_EPISODES) -> Tuple[int, List[int]]:
        self.final_dir.mkdir(parents=True, exist_ok=True)
        exported_count = 0
        failed_eps: List[int] = []

        for ep in range(1, total + 1):
            src_file = self.output_dir / f"ep{ep:02d}.md"
            if not src_file.exists():
                failed_eps.append(ep)
                continue

            # 校正を確実に適用
            text = src_file.read_text(encoding="utf-8")
            polished_text, _ = proofread_text(text)

            dest_file = self.final_dir / f"ep{ep:02d}.md"
            dest_file.write_text(polished_text, encoding="utf-8")
            exported_count += 1

        return exported_count, failed_eps


def main():
    parser = argparse.ArgumentParser(description="50話 小説人手微調整・校正・最終化ツール")
    parser.add_argument("--check-low", action="store_true", help="スコア0.80未満の話数をリストアップ")
    parser.add_argument("--polish-all", action="store_true", help="全話の表記ゆれ・文法・約物校正を一括実行")
    parser.add_argument("--export-final", action="store_true", help="校正済み原稿を final/ ディレクトリにコピー")
    args = parser.parse_args()

    tool = PolishTool()

    if args.check_low:
        lows = tool.list_low_score_episodes()
        print(f"=== 低スコア (<0.80) エピソード一覧 ===")
        if not lows:
            print("[PASS] 0.80未満のエピソードはありません（全話良好）。")
        else:
            for ep, sc in lows:
                print(f"・第{ep:02d}話: スコア {sc:.3f}")

    if args.polish_all:
        print("=== 全話自動校正・表記統一処理中 ===")
        for ep in range(1, TOTAL_EPISODES + 1):
            ok, cnt = tool.polish_episode(ep)
            if cnt > 0:
                print(f"・第{ep:02d}話: {cnt}文字の修正適用 (検証: {'合格' if ok else '要確認'})")
        print("[OK] 全話校正完了")

    if args.export_final:
        count, fails = tool.export_all_to_final()
        print(f"=== 最終原稿 final/ へのエクスポート完了 ===")
        print(f"・出力成功: {count}/{TOTAL_EPISODES}話")
        if fails:
            print(f"・未出力話数: {fails}")


if __name__ == "__main__":
    main()
