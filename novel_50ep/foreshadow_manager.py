"""伏線・クリフハンガー管理モジュール (ステップ51〜58)"""

from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from novel_50ep.config import CLIFFS_FILE, FORESHADOW_FILE, FORESHADOW_MAP_FILE
except ImportError:
    from config import CLIFFS_FILE, FORESHADOW_FILE, FORESHADOW_MAP_FILE


@dataclass
class ForeshadowItem:
    ep: int
    type: str  # '伏線' または '回収'
    text: str
    status: str  # '未回収' または '回収'


class ForeshadowManager:
    """伏線台帳(foreshadow.csv)とクリフハンガーの管理クラス"""

    def __init__(self, csv_path: Path = FORESHADOW_FILE, cliffs_path: Path = CLIFFS_FILE):
        self.csv_path = csv_path
        self.cliffs_path = cliffs_path
        self.init_csv()

    # ステップ51: foreshadow.csv 作成
    def init_csv(self) -> None:
        if not self.csv_path.exists():
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ep", "type", "text", "status"])

    def load_all(self) -> List[ForeshadowItem]:
        items: List[ForeshadowItem] = []
        if not self.csv_path.exists():
            return items
        with open(self.csv_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(
                    ForeshadowItem(
                        ep=int(row.get("ep", 0)),
                        type=row.get("type", "伏線"),
                        text=row.get("text", ""),
                        status=row.get("status", "未回収"),
                    )
                )
        return items

    def save_all(self, items: List[ForeshadowItem]) -> None:
        with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ep", "type", "text", "status"])
            for item in items:
                writer.writerow([item.ep, item.type, item.text, item.status])

    # ステップ52: 各話クリフを foreshadow.csv に追記 (status=未回収)
    def add_foreshadow(self, ep: int, f_type: str, text: str, status: str = "未回収") -> None:
        items = self.load_all()
        items.append(ForeshadowItem(ep=ep, type=f_type, text=text, status=status))
        self.save_all(items)

    # ステップ53: 直近1件の未回収伏線を文脈に渡す
    def get_latest_unresolved(self, current_ep: int) -> Optional[ForeshadowItem]:
        items = self.load_all()
        # current_ep より前の未回収伏線を逆順探索
        for item in reversed(items):
            if item.ep < current_ep and item.status == "未回収" and item.type == "伏線":
                return item
        return None

    # Step 9: 直近 n 話分の本文を取得（類似度チェック用）
    def get_prev_episodes_text(self, n: int = 2) -> List[str]:
        """直近 n 話分の生成済みテキストを取得"""
        from novel_50ep.config import OUTPUT_DIR
        texts = []
        items = self.load_all()
        eps_with_content = sorted(set(item.ep for item in items if item.type == "伏線"))
        for ep in reversed(eps_with_content[-n:]):
            ep_file = OUTPUT_DIR / f"ep{ep:02d}.md"
            if ep_file.exists():
                texts.append(ep_file.read_text(encoding="utf-8"))
        return texts

    # ステップ54: 回収済み (status=回収) に更新
    def resolve_foreshadow(self, target_text: str, resolved_ep: int) -> bool:
        items = self.load_all()
        updated = False
        for item in items:
            if item.status == "未回収" and (target_text in item.text or item.text in target_text):
                item.status = "回収"
                updated = True
                break
        if updated:
            self.save_all(items)
            # 回収レコードも追記
            self.add_foreshadow(ep=resolved_ep, f_type="回収", text=f"第{item.ep}話の伏線回収: {target_text[:30]}...", status="回収")
        return updated

    # ステップ55: 50話最後の全伏線回収チェック
    def check_all_resolved(self) -> Tuple[bool, List[ForeshadowItem]]:
        items = self.load_all()
        unresolved = [item for item in items if item.status == "未回収" and item.type == "伏線"]
        return len(unresolved) == 0, unresolved

    def load_cliff_patterns(self) -> List[str]:
        """
        優先的に foreshadow_map.md のテーブルからクリフハンガーを読み込む。
        存在しない場合は CLIFFS_FILE を参照する。
        """
        # 1. foreshadow_map.md からの抽出を試みる
        try:
            if FORESHADOW_MAP_FILE.exists():
                lines = FORESHADOW_MAP_FILE.read_text(encoding="utf-8").splitlines()
                cliffs = []
                for line in lines:
                    if line.startswith("| 第") and "伏線" in line:
                        # テーブル形式: | 話数 | 種別 | 内容 | ステータス |
                        parts = line.split("|")
                        if len(parts) >= 4:
                            content = parts[3].strip()
                            # 「第NN話クリフ: 」などの接頭辞を除去して中身だけを抽出
                            if ":" in content:
                                content = content.split(":", 1)[1].strip()
                            cliffs.append(content)
                if cliffs:
                    return cliffs
        except Exception:
            pass

        # 2. フォールバック: 従来の CLIFFS_FILE
        if self.cliffs_path.exists():
            return [line.strip() for line in self.cliffs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        
        return ["胸元の光の石が突如として不吉な黒に染まり、脈打ち始めた。"]

    # ステップ56: クリフパターン使用頻度集計
    def cliff_usage(self) -> Dict[str, int]:
        patterns = self.load_cliff_patterns()
        usage: Dict[str, int] = {p: 0 for p in patterns}
        items = self.load_all()
        for item in items:
            for p in patterns:
                if p in item.text or (len(p) > 10 and p[:10] in item.text):
                    usage[p] = usage.get(p, 0) + 1
        return usage

    # ステップ57: 偏り回避（10回以上重複防止・最少使用パターン優先）
    def next_cliff(self) -> str:
        usage = self.cliff_usage()
        patterns = self.load_cliff_patterns()
        if not patterns:
            return "突如として光の石が激しく明滅し、不気味な気配が空間を満たした。"

        # 使用回数が10回未満かつ最少のパターンを選択
        valid_patterns = [(p, usage.get(p, 0)) for p in patterns if usage.get(p, 0) < 10]
        if not valid_patterns:
            valid_patterns = [(p, usage.get(p, 0)) for p in patterns]

        valid_patterns.sort(key=lambda x: x[1])
        return valid_patterns[0][0]

    # ステップ58: foreshadow_map.md 出力
    def export_foreshadow_map(self, output_path: Path = FORESHADOW_MAP_FILE) -> None:
        items = self.load_all()
        usage = self.cliff_usage()

        lines = [
            "# 50話 全体伏線・クリフハンガー管理マップ (foreshadow_map.md)",
            "",
            "## 1. 伏線ステータス一覧",
            "",
            "| 話数 | 種別 | 内容 | ステータス |",
            "|---|---|---|---|",
        ]
        if not items:
            lines.append("| - | なし | 登録された伏線はありません | - |")
        else:
            for it in items:
                status_badge = "✅ 回収済" if it.status == "回収" else "⏳ 未回収"
                safe_text = it.text.replace("|", "&#124;")
                lines.append(f"| 第{it.ep}話 | {it.type} | {safe_text} | {status_badge} |")

        lines.extend([
            "",
            "## 2. クリフハンガーパターン使用頻度 (ステップ56)",
            "",
            "| パターン | 使用回数 | 状態 |",
            "|---|---|---|",
        ])
        for pat, count in usage.items():
            state = "⚠️ 警告(10回以上)" if count >= 10 else "適正"
            lines.append(f"| {pat} | {count}回 | {state} |")

        all_res, unres = self.check_all_resolved()
        lines.extend([
            "",
            f"## 3. 完結時検証: {'全伏線回収完了' if all_res else f'未回収伏線あり ({len(unres)}件)'}",
        ])
        if unres:
            for u in unres:
                lines.append(f"- ❌ 第{u.ep}話: {u.text}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
