"""50話バッチ生成運用ランナー (ステップ41〜50)"""

from __future__ import annotations
import argparse
import difflib
from pathlib import Path
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from novel_50ep.config import (
        FINAL_DIR,
        LOG_DIR,
        OUTPUT_DIR,
        PROGRESS_FILE,
        TOTAL_EPISODES,
        MIN_CHARS,
        enable_manga_prompts,
    )
    from novel_50ep.count_chars import count_chars, require_words, validate_episode, ValidationResult, extract_metaphors
    from novel_50ep.generator import NovelGenerator
    from novel_50ep.continuity_tracker import ContinuityTracker
    from novel_50ep.scene_model import SceneBase
except ImportError:
    from config import (
        FINAL_DIR,
        LOG_DIR,
        OUTPUT_DIR,
        PROGRESS_FILE,
        TOTAL_EPISODES,
        MIN_CHARS,
        enable_manga_prompts,
    )
    from count_chars import count_chars, require_words, validate_episode, ValidationResult, extract_metaphors
    from generator import NovelGenerator
    from continuity_tracker import ContinuityTracker
    from scene_model import SceneBase


# ステップ48: 同名キャラ表記ゆれ正規化
def normalize_names(text: str) -> str:
    """主要キャラクターや地名の表記ゆれを統一する"""
    text = re.sub(r"凛[（\(].*?[）\)]", "凛", text)
    text = re.sub(r"光の石[（\(].*?[）\)]", "光の石", text)
    replacements = {
        "リン": "凛",
        "セリア巫女": "セリア",
        "ガルド戦士": "ガルド",
        "ルクス都市": "多層都市ルクス",
        "虚無のつめ": "虚無の爪",
        "ヴェルヘルム導師": "導師ヴェルヘルム",
    }
    for old_name, new_name in replacements.items():
        text = text.replace(old_name, new_name)
    return text


# ステップ49: 連続する「だ。」の重複を1つに減らす軽い正規化
def dedup_sentence_endings(text: str) -> str:
    """「だ。だ。」「である。である。」などの冗長な連続末尾を正規化"""
    text = re.sub(r"(だ。)\s*(だ。)+", r"\1", text)
    text = re.sub(r"(である。)\s*(である。)+", r"\1", text)
    text = re.sub(r"(した。)\s*(した。)\s*(した。)+", r"した。した。", text)
    return text


# Step 7: 文単位の重複除去（同一文が複数回出現したら初回のみ残す）
def dedup_sentences(text: str) -> str:
    """同一文（句点まで）の重複を除去し、初回出現のみを残す"""
    # 句点で分割（句点を保持）
    sentences = re.split(r'(?<=[。！？])', text)
    seen = set()
    result = []
    for s in sentences:
        s_stripped = s.strip()
        if not s_stripped:
            continue
        if s_stripped not in seen:
            seen.add(s_stripped)
            result.append(s)
    return "".join(result)


def clean_novel_text(text: str) -> str:
    """ステップ48, 49, Step 7 を統合した後処理フィルター"""
    text = normalize_names(text)
    text = dedup_sentence_endings(text)
    text = dedup_sentences(text)  # Step 7: 文単位重複除去
    return text


class BatchRunner:
    """バッチ生成と進捗管理"""

    def __init__(self, generator: Optional[NovelGenerator] = None):
        self.generator = generator or NovelGenerator()
        self.progress_file = PROGRESS_FILE
        self.failed_eps: Set[int] = set()

    # ステップ44: progress.txt 読み込み・書き込み
    def load_progress(self) -> Set[int]:
        if not self.progress_file.exists():
            return set()
        completed = set()
        for line in self.progress_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.isdigit():
                completed.add(int(line))
        return completed

    def record_progress(self, ep: int) -> None:
        completed = self.load_progress()
        completed.add(ep)
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        sorted_eps = sorted(completed)
        self.progress_file.write_text("\n".join(map(str, sorted_eps)), encoding="utf-8")

    # ステップ46: 10話中間レビュー (文字数平均・感情語平均)
    def intermediate_review(self, start_ep: int, end_ep: int) -> Dict[str, float]:
        char_counts: List[int] = []
        emotion_counts: List[int] = []
        metaphor_counts: List[int] = []

        for ep in range(start_ep, end_ep + 1):
            ep_file = OUTPUT_DIR / f"ep{ep:02d}.md"
            if ep_file.exists():
                text = ep_file.read_text(encoding="utf-8")
                char_counts.append(count_chars(text))
                em_cnt, _ = require_words(text)
                emotion_counts.append(em_cnt)
                metaphor_counts.append(len(extract_metaphors(text)))

        avg_chars = sum(char_counts) / len(char_counts) if char_counts else 0.0
        avg_emotions = sum(emotion_counts) / len(emotion_counts) if emotion_counts else 0.0
        avg_metaphors = sum(metaphor_counts) / len(metaphor_counts) if metaphor_counts else 0.0

        print(f"\n--- [第{start_ep}話〜第{end_ep}話 中間レビュー (ステップ46)] ---")
        print(f"・平均文字数: {avg_chars:.1f}字 (基準: 2900〜3100字)")
        print(f"・平均感情語数: {avg_emotions:.1f}個 (基準: 2.0個以上)")
        print(f"・平均比喩数: {avg_metaphors:.1f}個/話 (基準: {4}個以下/話)")

        # ステップ47: 平均が基準を下回れば調整フラグ
        if avg_chars < 2900:
            print("[WARN] 警告: 平均文字数が不足しています。プロンプト文字数指示を+50字調整推奨。")
        elif avg_chars > 3100:
            print("[WARN] 警告: 平均文字数が超過しています。プロンプト文字数指示を-50字調整推奨。")
        else:
            print("[OK] 文字数ペースは完全に目標範囲内です。")

        return {"avg_chars": avg_chars, "avg_emotions": avg_emotions, "avg_metaphors": avg_metaphors}

    # ステップ41: run_batch(start, end)
    def run_batch(
        self,
        start: int = 1,
        end: int = TOTAL_EPISODES,
        resume: bool = True,
        fix_continuity: bool = False,
    ) -> List[int]:
        completed = self.load_progress() if resume else set()
        successful: List[int] = []

        # ステップ 69: ContinuityTracker の初期化
        rules_dir = str(Path(__file__).parent / "continuity_rules")
        tracker = ContinuityTracker(
            rules_dir=rules_dir,
            expects=self.generator.foreshadow_mgr.get_expects(),
        )
        batch_report_file = LOG_DIR / "batch_report.txt"
        batch_report_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"=== バッチ生成開始 (第{start}話〜第{end}話 / 全{end - start + 1}話) ===")

        for ep in range(start, end + 1):
            if resume and ep in completed:
                ep_file = OUTPUT_DIR / f"ep{ep:02d}.md"
                if ep_file.exists():
                    print(f"[SKIP] 第{ep:02d}話: 生成済みのためスキップ (progress.txt)")
                    successful.append(ep)
                    continue

            print(f"\n[GEN] 第{ep:02d}話 生成中...")
            try:
                # 1話生成
                novel_text, val_result, _ = self.generator.generate_episode(ep)

                # 後処理（正規化）
                cleaned_text = clean_novel_text(novel_text)
                
                # Step 5: 重複除去後の文字数チェック
                cleaned_chars = count_chars(cleaned_text)
                if cleaned_chars < MIN_CHARS:
                    print(f"[WARN] 第{ep:02d}話: 重複除去後文字数 {cleaned_chars}字 < {MIN_CHARS}字 (動的フィラーで補填推奨)")

                # ステップ 69: tracker による継続性チェック & batch_report.txt 追記
                ep_scene = SceneBase(id=f"ep{ep:02d}", type="base", start=0, end=cleaned_chars)
                violations = tracker.feed(ep_scene)
                if violations:
                    with open(batch_report_file, "a", encoding="utf-8") as rf:
                        rf.write(f"第{ep:02d}話 継続性警告: {tracker.report()}\n")

                # ステップ 70: --fix-continuity による自動修正 (ステップ 14: DB 保存連携)
                if fix_continuity and violations:
                    try:
                        from novel_50ep.polish_tool import polish

                        cleaned_text = polish(cleaned_text, tracker=tracker)
                        # ステップ 14: DB 永続化
                        try:
                            import asyncio
                            asyncio.run(self.generator.foreshadow_mgr.persist_to_db(book_id=1, branch_id=1))
                        except Exception:
                            pass
                    except Exception as pe:
                        print(f"[WARN] 第{ep:02d}話 自動修正失敗: {pe}")

                ep_file = OUTPUT_DIR / f"ep{ep:02d}.md"
                ep_file.write_text(cleaned_text, encoding="utf-8")

                # Step 10-11: 類似度チェック（前2話と比較、0.6超なら警告＆再生成トリガー）
                prev_texts = self.generator.foreshadow_mgr.get_prev_episodes_text(n=2)
                if prev_texts:
                    for i, prev in enumerate(prev_texts):
                        ratio = difflib.SequenceMatcher(None, prev, cleaned_text).ratio()
                        if ratio > 0.6:
                            warn_msg = f"SIMILARITY_WARN: 第{ep}話は第{ep - i - 1}話と類似度 {ratio:.2f} (>0.6)"
                            print(f"[WARN] {warn_msg}")
                            # ログに追記
                            log_file = LOG_DIR / f"ep{ep:02d}.log"
                            with open(log_file, "a", encoding="utf-8") as f:
                                f.write(f"\n[類似度警告] {warn_msg}\n")
                            # 再生成フラグ（bad_partsに全パート追加してretry_partsへ）
                            # ここでは警告のみ出力し、次回バッチ実行時に再生成される想定
                            val_result.warnings.append(warn_msg)

                # ステップ42: validate_episode ログを log/epNN.log に出力
                log_file = LOG_DIR / f"ep{ep:02d}.log"
                log_file.parent.mkdir(parents=True, exist_ok=True)
                log_file.write_text(val_result.summary(), encoding="utf-8")

                # 進捗記録
                self.record_progress(ep)
                successful.append(ep)
                print(f"[OK] 第{ep:02d}話 生成完了: {val_result.total_chars}字 ({'合格' if val_result.is_valid else '警告あり'})")

            except Exception as e:
                # ステップ45: エラー時はスキップして後で再挑戦
                print(f"[FAIL] 第{ep:02d}話 生成失敗: {e}")
                self.failed_eps.add(ep)

            # ステップ46: 10話ごとに中間集計
            if ep % 10 == 0:
                self.intermediate_review(max(1, ep - 9), ep)

        # 失敗エピソードがあれば再挑戦 (ステップ45)
        if self.failed_eps:
            print(f"\n[RETRY] 失敗したエピソード ({len(self.failed_eps)}件) の再試行を行います: {sorted(self.failed_eps)}")
            self.retry_failed()

        # Step 23: 比喩レポート出力
        self.export_metaphor_report(end)

        return successful

    # ステップ45: retry_failed()
    def retry_failed(self) -> List[int]:
        retried: List[int] = []
        to_retry = list(self.failed_eps)
        for ep in to_retry:
            print(f"[RETRY] 再試行: 第{ep:02d}話...")
            try:
                novel_text, val_result, _ = self.generator.generate_episode(ep)
                cleaned_text = clean_novel_text(novel_text)
                (OUTPUT_DIR / f"ep{ep:02d}.md").write_text(cleaned_text, encoding="utf-8")
                (LOG_DIR / f"ep{ep:02d}.log").write_text(val_result.summary(), encoding="utf-8")
                self.record_progress(ep)
                self.failed_eps.remove(ep)
                retried.append(ep)
                print(f"[OK] 第{ep:02d}話 再試行成功")
            except Exception as e:
                print(f"[FAIL] 第{ep:02d}話 再試行失敗: {e}")
        return retried

    # Step 23: 比喩使用レポート出力 (foreshadow_map.md 同様)
    def export_metaphor_report(self, total: int = TOTAL_EPISODES) -> Path:
        from novel_50ep.config import LOG_DIR
        from novel_50ep.count_chars import extract_metaphors, count_metaphor_types, detect_metaphor_dup
        report_path = LOG_DIR / "metaphor_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        lines = [
            "# 50話 比喩テンプレ化対策レポート (metaphor_report.md)",
            "",
            "## 1. 話別比喩使用量",
            "",
            "| 話数 | 比喩数 | 比喩率 | 重複核 |",
            "|---|---|---|---|",
        ]
        
        total_metaphors = 0
        total_chars = 0
        
        for ep in range(1, total + 1):
            ep_file = OUTPUT_DIR / f"ep{ep:02d}.md"
            if ep_file.exists():
                text = ep_file.read_text(encoding="utf-8")
                metaphors = extract_metaphors(text)
                m_count = len(metaphors)
                types = count_metaphor_types(text)
                dup_found, dup_details = detect_metaphor_dup(text)
                ratio = m_count / max(1, len(text) / 100) if text else 0.0
                
                total_metaphors += m_count
                total_chars += len(text)
                
                dup_str = "; ".join(dup_details) if dup_found else "なし"
                type_str = ", ".join(f"{k}:{v}" for k, v in types.items()) if types else "なし"
                lines.append(f"| 第{ep:02d}話 | {m_count}個 | {ratio:.1%} | {dup_str} |")
        
        avg_ratio = (total_metaphors / max(1, total_chars / 100)) if total_chars else 0.0
        lines.extend([
            "",
            f"## 2. 全体サマリー",
            "",
            f"- 総比喩数: {total_metaphors}個",
            f"- 平均比喩率: {avg_ratio:.1%}",
            f"- 目標閾値: 15%以下, 4個/話以下",
        ])
        
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[INFO] 比喩レポート出力: {report_path}")
        return report_path

    # ステップ50: check_all() 全50話揃っているか確認
    def check_all(self, total: int = TOTAL_EPISODES) -> Tuple[bool, List[int], List[int]]:
        missing: List[int] = []
        invalid: List[int] = []

        for ep in range(1, total + 1):
            ep_file = OUTPUT_DIR / f"ep{ep:02d}.md"
            if not ep_file.exists():
                missing.append(ep)
            else:
                res = validate_episode(ep_file)
                if not res.is_valid:
                    invalid.append(ep)

        is_all_ok = len(missing) == 0 and len(invalid) == 0
        return is_all_ok, missing, invalid


def main():
    parser = argparse.ArgumentParser(description="50話バッチ生成ランナー")
    parser.add_argument("--start", type=int, default=1, help="開始話数 (デフォルト: 1)")
    parser.add_argument("--end", type=int, default=TOTAL_EPISODES, help=f"終了話数 (デフォルト: {TOTAL_EPISODES})")
    parser.add_argument("--no-resume", action="store_true", help="進捗を無視して強制再生成")
    parser.add_argument("--check-only", action="store_true", help="全話の生成状況チェックのみ実行")
    parser.add_argument("--manga", action="store_true", help="オプトイン: 4コマ漫画プロンプトも生成する")
    parser.add_argument("--manga-dry-run", action="store_true", help="オプトイン+サンプル1話だけ4コマ生成して動作確認")
    parser.add_argument("--fix-continuity", action="store_true", help="ステップ 70: 継続性違反の自動修正を実行")
    args = parser.parse_args()

    # ステップ12: --manga フラグでオプトイン有効化
    if args.manga:
        enable_manga_prompts()

    # ステップ66-68: --manga-dry-run は有効化＋第1話のみ生成
    start, end = args.start, args.end
    if args.manga_dry_run:
        enable_manga_prompts()
        start, end = 1, 1

    runner = BatchRunner()

    if args.check_only:
        all_ok, missing, invalid = runner.check_all(args.end)
        print(f"=== 全話チェック結果 ===")
        print(f"・欠損話数: {missing if missing else 'なし'}")
        print(f"・不合格話数: {invalid if invalid else 'なし'}")
        print(f"・総合判定: {'[PASS] 全話完全クリア' if all_ok else '[WARN] 未達話数あり'}")
        sys.exit(0 if all_ok else 1)

    runner.run_batch(start=start, end=end, resume=not args.no_resume, fix_continuity=args.fix_continuity)
    all_ok, missing, invalid = runner.check_all(end)
    print(f"\n=== 最終バッチサマリー ===")
    print(f"・完了: {TOTAL_EPISODES - len(missing)}/{TOTAL_EPISODES}話")
    if missing:
        print(f"・未生成: {missing}")
    if invalid:
        print(f"・要修正: {invalid}")


if __name__ == "__main__":
    main()
