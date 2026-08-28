"""人手微調整・校正・最終化ツール (ステップ65〜68)"""

from __future__ import annotations
import argparse
import csv
from pathlib import Path
import re
import shutil
import sys
from typing import Dict, List, Optional, Tuple, Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from novel_50ep.batch_runner import clean_novel_text
    from novel_50ep.config import FINAL_DIR, OUTPUT_DIR, SCORES_FILE, TOTAL_EPISODES, WORLD_FILE, load_world_with_viewpoint, STYLE_GUIDE_DEFAULT
    from novel_50ep.count_chars import validate_episode, extract_metaphors, MAX_METAPHOR_RATIO, MAX_METAPHOR_PER_EP, calculate_style_stats
    from novel_50ep.score_reviewer import ScoreReviewer
    from novel_50ep.continuity_tracker import ContinuityTracker
except ImportError:
    from batch_runner import clean_novel_text
    from config import FINAL_DIR, OUTPUT_DIR, SCORES_FILE, TOTAL_EPISODES, WORLD_FILE, load_world_with_viewpoint, STYLE_GUIDE_DEFAULT
    from count_chars import validate_episode, extract_metaphors, MAX_METAPHOR_RATIO, MAX_METAPHOR_PER_EP, calculate_style_stats
    from score_reviewer import ScoreReviewer
    from continuity_tracker import ContinuityTracker


# 人称統一マップ (視点別)
PERSONA_NORMALIZE_MAP: Dict[str, Dict[str, str]] = {
    "third_person": {
        "私": "彼女", "僕": "彼女", "俺": "彼女", "あたし": "彼女", "わし": "彼女", "拙者": "彼女",
        "私の": "彼女の", "僕の": "彼女の", "俺の": "彼女の", "あたしの": "彼女の", "わしの": "彼女の", "拙者の": "彼女の",
        "私が": "彼女が", "僕が": "彼女が", "俺が": "彼女が", "あたしが": "彼女が", "わしが": "彼女が", "拙者が": "彼女が",
        "私を": "彼女を", "僕を": "彼女を", "俺を": "彼女を", "あたしを": "彼女を", "わしを": "彼女を", "拙者を": "彼女を",
        "私に": "彼女に", "僕に": "彼女に", "俺に": "彼女に", "あたしに": "彼女に", "わしに": "彼女に", "拙者に": "彼女に",
        "私には": "彼女には", "僕には": "彼女には", "俺には": "彼女には", "あたしには": "彼女には", "わしには": "彼女には", "拙者には": "彼女には",
        "私ほど": "彼女ほど", "僕ほど": "彼女ほど", "俺ほど": "彼女ほど",
        "私ら": "彼女ら", "僕ら": "彼女ら", "俺ら": "彼女ら",
    },
    "first_person_watashi": {
        "僕": "私", "俺": "私", "あたし": "私", "わし": "私", "拙者": "私",
        "僕の": "私の", "俺の": "私の", "あたしの": "私の", "わしの": "私の", "拙者の": "私の",
        "僕が": "私が", "俺が": "私が", "あたしが": "私が", "わしが": "私が", "拙者が": "私が",
        "僕を": "私を", "俺を": "私を", "あたしを": "私を", "わしを": "私を", "拙者を": "私を",
        "僕に": "私に", "俺に": "私に", "あたしに": "私に", "わしに": "私に", "拙者に": "私に",
        "僕には": "私には", "俺には": "私には", "あたしには": "私には", "わしには": "私には", "拙者には": "私には",
        "僕ら": "私ら", "俺ら": "私ら", "あたしら": "私ら",
    },
    "first_person_boku": {
        "私": "僕", "俺": "僕", "あたし": "僕", "わし": "僕", "拙者": "僕",
        "私の": "僕の", "俺の": "僕の", "あたしの": "僕の", "わしの": "僕の", "拙者の": "僕の",
        "私が": "僕が", "俺が": "僕が", "あたしが": "僕が", "わしが": "僕が", "拙者が": "僕が",
        "私を": "僕を", "俺を": "僕を", "あたしを": "僕を", "わしを": "僕を", "拙者を": "僕を",
        "私に": "僕に", "俺に": "僕に", "あたしに": "僕に", "わしに": "僕に", "拙者に": "僕に",
        "私には": "僕には", "俺には": "僕には", "あたしには": "僕には", "わしには": "僕には", "拙者には": "僕には",
        "私ら": "僕ら", "俺ら": "僕ら", "あたしら": "僕ら",
    },
    "first_person_ore": {
        "私": "俺", "僕": "俺", "あたし": "俺", "わし": "俺", "拙者": "俺",
        "私の": "俺の", "僕の": "俺の", "あたしの": "俺の", "わしの": "俺の", "拙者の": "俺の",
        "私が": "俺が", "僕が": "俺が", "あたしが": "俺が", "わしが": "俺が", "拙者が": "俺が",
        "私を": "俺を", "僕を": "俺を", "あたしを": "俺を", "わしを": "俺を", "拙者を": "俺を",
        "私に": "俺に", "僕に": "俺に", "あたしに": "俺に", "わしに": "俺に", "拙者に": "俺に",
        "私には": "俺には", "僕には": "俺には", "あたしには": "俺には", "わしには": "俺には", "拙者には": "俺には",
        "私ら": "俺ら", "僕ら": "俺ら", "あたしら": "俺ら",
    },
}


def normalize_persona(text: str, viewpoint: str) -> Tuple[str, int]:
    """指定視点に合わせて一人称代名詞を統一する"""
    mapping = PERSONA_NORMALIZE_MAP.get(viewpoint, PERSONA_NORMALIZE_MAP["third_person"])
    corrected = text
    fix_count = 0
    for wrong, correct in mapping.items():
        if wrong in corrected:
            count = corrected.count(wrong)
            corrected = corrected.replace(wrong, correct)
            fix_count += count
    return corrected, fix_count


# Step 15: 比喩書き換えプロンプトテンプレート
METAPHOR_REWRITE_PROMPT = """以下の文章で比喩表現が過剰です（閾値超過）。比喩を別表現（直喩・隠喩の転換、または具体描写への置換）に書き換えてください。

元の文章:
{text}

制約:
- 比喩率を {ratio:.0%} 以下に抑える
- 同一核の重複を避ける
- 物語のトーンを崩さない
"""


# ステップ 61, 62: 校正関数 (trackerフック & 自動修正プロンプト付与, ステップ 13: src.prototype 委譲)
def polish(
    text: str,
    scene: Optional[Any] = None,
    tracker: Optional[ContinuityTracker] = None,
    viewpoint: str = "third_person",
) -> str:
    """校正処理および継続性違反時の修正プロンプト生成 (ステップ 61, 62, 13, 15)"""
    if tracker is not None and scene is not None:
        tracker.feed(scene)

    if tracker is not None and tracker.violations:
        report_text = tracker.report()
        return f"以下の矛盾を修正してください: {report_text}\n\n{text}"

    # Step 15: 比喩過剰時の書き換えプロンプト挿入
    metaphors = extract_metaphors(text)
    metaphor_count = len(metaphors)
    metaphor_ratio = metaphor_count / max(1, len(text) / 100) if text else 0.0
    
    if metaphor_ratio > MAX_METAPHOR_RATIO or metaphor_count > MAX_METAPHOR_PER_EP:
        prompt = METAPHOR_REWRITE_PROMPT.format(text=text, ratio=MAX_METAPHOR_RATIO)
        return prompt

    try:
        from src.prototype.polish_adapter import polish as proto_polish

        return proto_polish(text, scene=scene, hub=tracker)
    except Exception:
        polished, _ = proofread_text(text, viewpoint=viewpoint)
        return polished


# ステップ67: 表記ゆれ・文法ミスの一括校正フィルター
def proofread_text(text: str, viewpoint: str = "third_person") -> Tuple[str, int]:
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

    # 6. 人称統一フィルタ (指定視点に合わせて一人称代名詞を正規化)
    cleaned, persona_fixes = normalize_persona(cleaned, viewpoint)
    corrections_count += persona_fixes

    # 差分文字数カウント
    diff_chars = abs(len(text) - len(cleaned))
    corrections_count += diff_chars

    return cleaned, corrections_count


class PolishTool:
    """校正・微調整・完成版エクスポート管理"""

    def __init__(self, scores_file: Path = SCORES_FILE, output_dir: Path = OUTPUT_DIR, final_dir: Path = FINAL_DIR):
        self.scores_file = scores_file
        self.output_dir = output_dir
        self.final_dir = final_dir
        self.reviewer = ScoreReviewer()
        # world.yaml から視点設定を読み込み
        world_data = load_world_with_viewpoint()
        self.viewpoint = world_data.get("viewpoint", "third_person")

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
        polished, fix_cnt = proofread_text(raw_text, viewpoint=self.viewpoint)

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
            polished_text, _ = proofread_text(text, viewpoint=self.viewpoint)

            dest_file = self.final_dir / f"ep{ep:02d}.md"
            dest_file.write_text(polished_text, encoding="utf-8")
            exported_count += 1

        return exported_count, failed_eps

    # ステップ: 文体外れ値の検出 (style_score < 0.7)
    def list_style_outlier_episodes(self, threshold: float = 0.70) -> List[Tuple[int, float]]:
        """style_score が閾値未満の話数をリストアップ"""
        outliers: List[Tuple[int, float]] = []
        if not self.scores_file.exists():
            self.reviewer.score_all()

        if self.scores_file.exists():
            with open(self.scores_file, mode="r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ep = int(row.get("ep", 0))
                    sc = float(row.get("style", 0.0))
                    if sc < threshold:
                        outliers.append((ep, sc))
        return outliers

    # 基準話を特定（直前5話の中央値に最も近い話、または ep-1）
    def _find_baseline_episode(self, target_ep: int, scores: List[Any]) -> int:
        """ターゲット話の基準となる話数を特定"""
        # 直前5話のスコアから中央値を計算
        recent_scores = [s for s in scores if target_ep - 5 <= s.ep < target_ep]
        if not recent_scores:
            return target_ep - 1 if target_ep > 1 else 1
        
        # style_score の中央値に最も近い話を選択
        style_scores = [s.style_score for s in recent_scores]
        median_style = sorted(style_scores)[len(style_scores) // 2]
        
        closest = min(recent_scores, key=lambda s: abs(s.style_score - median_style))
        return closest.ep

    # 基準話の文体統計を取得
    def _get_baseline_stats(self, baseline_ep: int) -> Optional[Dict]:
        """基準話の文体統計を取得（style_details から raw 値を取得）"""
        ep_file = self.output_dir / f"ep{baseline_ep:02d}.md"
        if not ep_file.exists():
            return None
        
        # score_reviewer から再取得
        self.reviewer.score_all()
        
        # スコアから該当話を探す
        if self.scores_file.exists():
            with open(self.scores_file, mode="r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if int(row.get("ep", 0)) == baseline_ep:
                        # style_details は生成時に再計算する必要がある
                        return None
        return None

    # 文体外れ値話数を基準話に合わせてリライト
    def polish_style_outlier(self, ep: int, baseline_ep: Optional[int] = None) -> Tuple[bool, int]:
        """文体外れ値話数を基準話に合わせてリライト"""
        ep_file = self.output_dir / f"ep{ep:02d}.md"
        if not ep_file.exists():
            return False, 0

        raw_text = ep_file.read_text(encoding="utf-8")
        
        # 基準話が未指定なら自動選定
        if baseline_ep is None:
            self.reviewer.score_all()
            scores = []
            if self.scores_file.exists():
                with open(self.scores_file, mode="r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # EpisodeScore オブジェクトを再構築
                        from dataclasses import make_dataclass
                        EpisodeScore = make_dataclass('EpisodeScore', 
                            ['ep', 'pacing_score', 'emotion_score', 'world_score', 'cliff_score', 
                             'metaphor_score', 'style_score', 'total_score', 'details', 'style_details'])
                        scores.append(EpisodeScore(
                            ep=int(row.get("ep", 0)),
                            pacing_score=float(row.get("pacing", 0)),
                            emotion_score=float(row.get("emotion", 0)),
                            world_score=float(row.get("world", 0)),
                            cliff_score=float(row.get("cliff", 0)),
                            metaphor_score=float(row.get("metaphor", 0)),
                            style_score=float(row.get("style", 0)),
                            total_score=float(row.get("total_score", 0)),
                            details={},
                            style_details={}
                        ))
            baseline_ep = self._find_baseline_episode(ep, scores)
        
        # 基準話の文体統計を計算
        baseline_file = self.output_dir / f"ep{baseline_ep:02d}.md"
        if not baseline_file.exists():
            print(f"[WARN] 基準話第{baseline_ep}話のファイルが見つかりません")
            return False, 0
        
        baseline_text = baseline_file.read_text(encoding="utf-8")
        baseline_stats = calculate_style_stats(baseline_text)
        
        # リライトプロンプト生成
        prompt = self._build_rewrite_prompt(raw_text, baseline_stats, baseline_ep)
        
        # LLM でリライト (mock_generator で代替)
        rewritten = self._mock_rewrite(raw_text, baseline_stats, prompt)
        
        # リライト後の検証
        rewritten_stats = calculate_style_stats(rewritten)
        
        # 基準話の ±1σ 以内なら成功とみなす（簡易判定）
        avg_len_ok = abs(rewritten_stats.avg_sentence_length - baseline_stats.avg_sentence_length) <= max(5, baseline_stats.avg_sentence_length * 0.2)
        plain_ratio_ok = abs(rewritten_stats.plain_form_ratio - baseline_stats.plain_form_ratio) <= 0.15
        unique_ok = abs(rewritten_stats.unique_word_count - baseline_stats.unique_word_count) <= max(20, baseline_stats.unique_word_count * 0.2)
        
        if avg_len_ok and plain_ratio_ok and unique_ok:
            ep_file.write_text(rewritten, encoding="utf-8")
            print(f"・第{ep:02d}話: 文体リライト成功 (基準: 第{baseline_ep}話)")
            return True, 1
        else:
            print(f"[WARN] 第{ep:02d}話: リライト後の文体が基準話に近づきませんでした")
            return False, 0

    def _build_rewrite_prompt(self, text: str, baseline_stats: Any, baseline_ep: int) -> str:
        """リライト用プロンプトを構築"""
        return f"""以下の文章を、基準話（第{baseline_ep}話）の文体に合わせてリライトしてください。

【基準話の文体統計】
- 平均文長: {baseline_stats.avg_sentence_length:.1f}文字
- 常体率: {baseline_stats.plain_form_ratio:.1%}
- ユニーク語数: {baseline_stats.unique_word_count}語

【リライト指示】
- 文末をすべて常体（だ/である/た）に統一
- 文長を基準話の平均±10%に収める
- 語彙レベルを基準話に合わせる
- 物語の内容・展開は変更しない

【元の文章】
{text}"""

    def _mock_rewrite(self, text: str, baseline_stats: Any, prompt: str) -> str:
        """モックリライト（簡易版：文末を常体に統一、文長調整など）"""
        # 簡易的な文末統一
        import re
        # 敬体を常体に変換
        rewritten = re.sub(r"です。", "だ。", text)
        rewritten = re.sub(r"ます。", "だ。", rewritten)
        rewritten = re.sub(r"です、", "だ、", rewritten)
        rewritten = re.sub(r"ます、", "だ、", rewritten)
        # 簡易的な文長調整（長すぎる文を分割）
        sentences = re.split(r"(。)", rewritten)
        result = []
        for i in range(0, len(sentences), 2):
            s = sentences[i]
            if i + 1 < len(sentences):
                s += sentences[i+1]
            if len(s) > baseline_stats.avg_sentence_length * 1.5 and "、" in s:
                # 長い文を「、」で分割
                parts = s.split("、")
                if len(parts) > 1:
                    for j, p in enumerate(parts):
                        if j < len(parts) - 1:
                            result.append(p + "、")
                        else:
                            result.append(p)
            else:
                result.append(s)
        return "".join(result) if 'result' in locals() else rewritten


def main():
    parser = argparse.ArgumentParser(description="50話 小説人手微調整・校正・最終化ツール")
    parser.add_argument("--check-low", action="store_true", help="スコア0.80未満の話数をリストアップ")
    parser.add_argument("--polish-all", action="store_true", help="全話の表記ゆれ・文法・約物校正を一括実行")
    parser.add_argument("--export-final", action="store_true", help="校正済み原稿を final/ ディレクトリにコピー")
    parser.add_argument("--check-style", action="store_true", help="文体外れ値 (style_score<0.70) の話数をリストアップ")
    parser.add_argument("--fix-style", type=int, nargs="*", metavar="EP", help="文体外れ値話数を基準話に合わせてリライト (話数指定なしで全外れ値対象)")
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

    if args.check_style:
        outliers = tool.list_style_outlier_episodes()
        print(f"=== 文体外れ値 (style_score<0.70) エピソード一覧 ===")
        if not outliers:
            print("[PASS] 文体外れ値のエピソードはありません。")
        else:
            for ep, sc in outliers:
                print(f"・第{ep:02d}話: 文体スコア {sc:.3f}")

    if args.fix_style is not None:
        if len(args.fix_style) == 0:
            # 全外れ値対象
            outliers = tool.list_style_outlier_episodes()
            target_eps = [ep for ep, _ in outliers]
        else:
            target_eps = args.fix_style
        
        print(f"=== 文体リライト実行 (対象: {target_eps}) ===")
        for ep in target_eps:
            ok, _ = tool.polish_style_outlier(ep)
            if not ok:
                print(f"[FAIL] 第{ep:02d}話のリライトに失敗しました")

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
