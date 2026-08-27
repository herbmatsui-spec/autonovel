"""カクヨム公開準備・パッケージングモジュール (ステップ69〜72)"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import zipfile
from typing import Dict, List, Optional
import yaml

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from novel_50ep.config import (
        FINAL_DIR,
        METADATA_FILE,
        OUTPUT_DIR,
        TOTAL_EPISODES,
        WORLD_FILE,
    )
    from novel_50ep.count_chars import count_chars
except ImportError:
    from config import (
        FINAL_DIR,
        METADATA_FILE,
        OUTPUT_DIR,
        TOTAL_EPISODES,
        WORLD_FILE,
    )
    from count_chars import count_chars


class PublishPreparer:
    """カクヨム投稿フォーマット整形・メタデータ・パッケージング"""

    def __init__(self, world_path: Path = WORLD_FILE, final_dir: Path = FINAL_DIR, output_dir: Path = OUTPUT_DIR):
        self.world_path = world_path
        self.final_dir = final_dir
        self.output_dir = output_dir
        self.world_data = self._load_world()

    def _load_world(self) -> dict:
        if self.world_path.exists():
            return yaml.safe_load(self.world_path.read_text(encoding="utf-8")) or {}
        return {}

    # ステップ69: カクヨム形式タイトル付与 (第N話 サブタイトル)
    def generate_subtitles(self, total: int = TOTAL_EPISODES) -> Dict[int, str]:
        subtitles: Dict[int, str] = {}
        arc_themes = [
            ("序章：光脈の減衰", ["光の石の胎動", "蒼穹の回廊", "仮面の刺客", "神殿の巫女", "古代の光脈", "深淵への扉", "結界の綻び", "失われた刻印", "光と闇の交差点", "黎明の誓い"]),
            ("第2章：闇結社の蠢動", ["虚無の爪", "影の哨戒線", "鉄壁の戦士", "光核の共鳴", "地下迷宮の罠", "裏切りの影", "反撃の狼煙", "封印の鍵", "奪われた光", "嵐の前の静寂"]),
            ("第3章：多層都市の激震", ["崩落する外壁", "光導器の暴走", "覚醒の兆し", "古の守護者", "闇の進撃", "死線の突破", "巫女の祈り", "剣戟の閃光", "真実への手がかり", "反抗の光芒"]),
            ("第4章：深層の真実", ["第十三の紋章", "ヴェルヘルムの野望", "失われた血脈", "黒炎の猛威", "友との絆", "絶望の淵", "逆転の布石", "光層の心臓部", "最後の封印", "決戦前夜"]),
            ("終章：輝石の黎明", ["総力結集", "虚無の巨影", "光刃の覚醒", "仮面の崩落", "宿命の決着", "闇の霧散", "光脈の復活", "新時代の幕開け", "未来への旅立ち", "輝石の遺産"]),
        ]
        ep_idx = 1
        for arc_name, ep_titles in arc_themes:
            for title in ep_titles:
                if ep_idx <= total:
                    subtitles[ep_idx] = title
                    ep_idx += 1

        while ep_idx <= total:
            subtitles[ep_idx] = f"光層の戦い その{ep_idx}"
            ep_idx += 1

        return subtitles

    def apply_kakuyomu_titles(self, total: int = TOTAL_EPISODES) -> None:
        subtitles = self.generate_subtitles(total)
        self.final_dir.mkdir(parents=True, exist_ok=True)

        for ep in range(1, total + 1):
            file_path = self.final_dir / f"ep{ep:02d}.md"
            if not file_path.exists():
                # output_dir からフォールバック
                fallback = self.output_dir / f"ep{ep:02d}.md"
                if fallback.exists():
                    file_path.write_text(fallback.read_text(encoding="utf-8"), encoding="utf-8")

            if file_path.exists():
                text = file_path.read_text(encoding="utf-8")
                sub = subtitles.get(ep, f"第{ep}話")
                title_header = f"第{ep}話　{sub}\n\n"

                # 既にタイトルが付いているかチェック
                if not text.startswith(f"第{ep}話"):
                    new_text = title_header + text
                    file_path.write_text(new_text, encoding="utf-8")

    # ステップ70: metadata.json の生成（タグ・あらすじ・作品情報）
    def create_metadata_json(self, output_file: Path = METADATA_FILE) -> dict:
        title = self.world_data.get("title", "輝石の遺産 〜階層都市の黎明記〜")
        genre = self.world_data.get("genre", "ファンタジー")
        protagonist = self.world_data.get("protagonist", {}).get("name", "凛")

        synopsis = (
            f"天空へと聳える多層都市『光層ルクス』。世界の平和を支える【光の石】が突如減衰を始める。"
            f"18歳の青年・{protagonist}は、失われた家族の真相と都市の崩壊を食い止めるため、"
            f"神殿の巫女セリアや歴戦の戦士ガルドと共に、暗躍する闇結社『虚無の爪』との死闘に身を投じる。"
            f"全50話で紡がれる王道ハイ・ファンタジー巨編、堂々開幕！"
        )

        metadata = {
            "title": title,
            "genre": genre,
            "target_characters_per_episode": 3000,
            "total_episodes": TOTAL_EPISODES,
            "estimated_total_chars": TOTAL_EPISODES * 3000,
            "synopsis": synopsis,
            "synopsis_chars": count_chars(synopsis),
            "tags": [
                "カクヨムオンリー",
                "オリジナル",
                "ハイファンタジー",
                "異能バトル",
                "男主人公",
                "冒険",
                "魔法・光術",
                "シリアス",
                "完結保証",
                "連載",
            ],
            "characters": {
                "protagonist": self.world_data.get("protagonist", {}),
                "antagonist": self.world_data.get("antagonist", {}),
                "subcharacters": self.world_data.get("subcharacters", []),
            },
            "world_symbol": self.world_data.get("symbol", "光の石"),
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata

    # ステップ71: あらすじ(200字)と冒頭3話プレビュー生成
    def generate_synopsis_and_preview(self) -> str:
        meta = self.create_metadata_json()
        lines = [
            "# カクヨム公開用 あらすじ・冒頭3話プレビュー (ステップ71)",
            "",
            "## ■ 作品基本情報",
            f"- **タイトル**: {meta['title']}",
            f"- **ジャンル**: {meta['genre']}",
            f"- **タグ**: {', '.join(meta['tags'])}",
            "",
            "## ■ 公式あらすじ (約200字)",
            f"{meta['synopsis']}",
            f"(文字数: {meta['synopsis_chars']}字)",
            "",
            "---",
            "",
            "## ■ 冒頭3話プレビュー",
        ]

        for ep in range(1, 4):
            ep_file = self.final_dir / f"ep{ep:02d}.md"
            if not ep_file.exists():
                ep_file = self.output_dir / f"ep{ep:02d}.md"

            if ep_file.exists():
                text = ep_file.read_text(encoding="utf-8")
                # 冒頭400字を抜粋
                snippet = text[:400].replace("\n", "\n> ")
                lines.extend([
                    f"\n### 第{ep}話 冒頭抜粋",
                    f"> {snippet}……",
                ])

        preview_text = "\n".join(lines)
        (FINAL_DIR / "preview_and_synopsis.md").write_text(preview_text, encoding="utf-8")
        return preview_text

    # ステップ72: 公開用 ZIP および 本文結合ファイルの作成
    def export_publication_package(self, total: int = TOTAL_EPISODES) -> Tuple[Path, Path]:
        self.apply_kakuyomu_titles(total)
        self.create_metadata_json()
        self.generate_synopsis_and_preview()

        # 1. 全話結合テキストファイル (full_novel_kakuyomu.txt)
        full_novel_path = FINAL_DIR / "full_novel_kakuyomu.txt"
        full_lines = [f"# {self.world_data.get('title', '輝石の遺産')}\n\n"]

        for ep in range(1, total + 1):
            ep_file = self.final_dir / f"ep{ep:02d}.md"
            if ep_file.exists():
                full_lines.append(ep_file.read_text(encoding="utf-8"))
                full_lines.append("\n\n" + "=" * 40 + "\n\n")

        full_novel_path.write_text("\n".join(full_lines), encoding="utf-8")

        # 2. 公開用 ZIP アーカイブ (kakuyomu_package.zip)
        zip_path = FINAL_DIR / "kakuyomu_package.zip"
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(METADATA_FILE, arcname="metadata.json")
            zf.write(full_novel_path, arcname="full_novel_kakuyomu.txt")
            preview_file = FINAL_DIR / "preview_and_synopsis.md"
            if preview_file.exists():
                zf.write(preview_file, arcname="preview_and_synopsis.md")

            for ep in range(1, total + 1):
                ep_file = self.final_dir / f"ep{ep:02d}.md"
                if ep_file.exists():
                    zf.write(ep_file, arcname=f"episodes/ep{ep:02d}.md")

        return full_novel_path, zip_path


def main():
    parser = argparse.ArgumentParser(description="カクヨム公開準備・パッケージングツール")
    parser.add_argument("--package", action="store_true", help="全50話のタイトル付与、メタデータ作成、ZIP生成を実行")
    args = parser.parse_args()

    prep = PublishPreparer()
    full_path, zip_path = prep.export_publication_package()
    print("=== カクヨム公開パッケージング完了 ===")
    print(f"・結合原稿: {full_path}")
    print(f"・公開ZIP: {zip_path}")


if __name__ == "__main__":
    main()
