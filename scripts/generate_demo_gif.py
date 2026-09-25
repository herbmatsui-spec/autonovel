import argparse
import os
import tomllib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1200, 720
BACKGROUND = "#101827"
PANEL = "#1b2940"
WHITE = "#f0f5ff"
MUTED = "#b4c3d9"
ACCENT = "#65dfca"
STEPS = (
    (
        "01",
        "モデルを設定する",
        "LLM設定 → 接続先と用途別モデルを確認",
        "入力例",
        (
            "まずは mock で操作・接続を確認",
            "実際の執筆にはプロバイダとAPIキーを設定",
            "プロット / 執筆 / 監査 / Embedding を使い分け",
        ),
        "確認すること",
        (
            "設定を変えたらAPIとワーカーを再起動",
            "APIキーは .env に保存し、Gitに含めない",
            "実APIの利用料金・生成時間はモデルに依存",
        ),
    ),
    (
        "02",
        "物語の種を用意する",
        "かんたんモード → ジャンル・主人公・冒頭を入力",
        "サンプル設定",
        (
            "ジャンル：ハイファンタジー",
            "主人公：アルト / 慎重な地図職人",
            "冒頭：消えた村が、古い地図にだけ残っていた。",
        ),
        "企画を広げる",
        (
            "3案ガチャで異なる方向のアイデアを比較",
            "逆算プロットでは結末から構成を考える",
            "設定と冒頭を確認してから執筆を始める",
        ),
    ),
    (
        "03",
        "本文を生成する",
        "かんたん執筆 → 進捗を確認 → 本文を読む",
        "物語のサンプル（手作業で用意）",
        (
            "雨に濡れた地図の上で、ひとつの村だけが乾いていた。",
            "アルトは指先でその名をなぞる。",
            "昨日まで空白だった場所に、母の筆跡があった。",
        ),
        "実際の操作",
        (
            "生成中はタスクやストリームの進捗を確認",
            "次話への提案を選び、続きを執筆",
            "待機したままならHueyワーカーの起動を確認",
        ),
    ),
    (
        "04",
        "設定を参照しながら推敲",
        "上級者 Studio → 本文編集・展開提案・設定確認",
        "推敲の例（説明用）",
        (
            "修正前：アルトは不安だった。",
            "修正後：地図を握る指が震えた。",
            "説明する文を、行動や五感の描写に置き換える。",
        ),
        "使い分け",
        (
            "選択範囲へのAI提案を確認して反映",
            "世界観や登場人物の設定と照らし合わせる",
            "監査は補助。最終的な整合性・品質は人が確認",
        ),
    ),
    (
        "05",
        "成果物を持ち出す",
        "本文を確認 → 納品パッケージをダウンロード",
        "ZIPにまとめる情報",
        (
            "本文テキスト",
            "キャラクター・世界観設定 / プロット概要",
            "構造化されたデータダンプ",
        ),
        "その他の出力",
        (
            "EPUB 3：縦書き・ルビ対応の電子書籍基盤",
            "投稿先向け整形：なろう / カクヨム / 汎用",
            "投稿先への公開操作は、ユーザーが内容を確認して実施",
        ),
    ),
)


def find_font(explicit: str | None) -> Path:
    candidates = [explicit, os.environ.get("DEMO_FONT")]
    candidates.extend(
        [
            "C:/Windows/Fonts/meiryo.ttc",
            "C:/Windows/Fonts/msgothic.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        ]
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise SystemExit("Japanese font not found. Pass --font PATH or set DEMO_FONT.")


def render_frame(
    step: tuple[str, str, str, str, tuple[str, ...], str, tuple[str, ...]], font_path: Path, version: str
) -> Image.Image:
    number, title, subtitle, left_title, left_lines, right_title, right_lines = step
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    def text(x: int, y: int, value: str, size: int, color: str = WHITE, max_width: int = 1080) -> None:
        font = ImageFont.truetype(str(font_path), size)
        while draw.textlength(value, font=font) > max_width and size > 14:
            size -= 1
            font = ImageFont.truetype(str(font_path), size)
        if draw.textlength(value, font=font) > max_width:
            raise ValueError(f"Text exceeds frame width: {value}")
        draw.text((x, y), value, font=font, fill=color)

    text(48, 28, f"AutoNovel  /  v{version}", 25, ACCENT)
    text(730, 34, "操作フローの説明デモ / 実画面録画ではありません", 17, MUTED, 430)
    draw.line((48, 85, 1152, 85), fill="#354963", width=2)
    text(48, 112, f"{number}  {title}", 40)
    text(48, 182, subtitle, 23, MUTED)
    for x, heading, lines in ((48, left_title, left_lines), (624, right_title, right_lines)):
        draw.rounded_rectangle((x, 254, x + 528, 548), radius=18, fill=PANEL)
        text(x + 24, 276, heading, 25, ACCENT, 480)
        for index, line in enumerate(lines):
            text(x + 24, 343 + index * 57, line, 21, WHITE, 480)
    for index, label in enumerate(("設定", "企画", "執筆", "推敲", "出力")):
        x = 48 + index * 224
        active = index + 1 == int(number)
        draw.rounded_rectangle((x, 592, x + 208, 634), radius=8, fill=ACCENT if active else PANEL)
        text(x + 64, 599, label, 21, BACKGROUND if active else MUTED, 140)
    text(
        48,
        665,
        "サンプルは説明用の固定データです。AI生成品質・所要時間・外部サービス接続を示すものではありません。",
        17,
        MUTED,
    )
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "demo.gif")
    args = parser.parse_args()
    if not args.output.parent.is_dir():
        parser.error("Output parent directory must already exist.")
    with (ROOT / "pyproject.toml").open("rb") as source:
        version = tomllib.load(source)["project"]["version"]
    font_path = find_font(args.font)
    frames = [render_frame(step, font_path, version) for step in STEPS]
    frames[0].save(
        args.output, save_all=True, append_images=frames[1:], duration=6000, loop=0, optimize=True, disposal=2
    )
    frames[2].save(args.output.with_suffix(".png"))
    print(f"Created {args.output} and {args.output.with_suffix('.png')}")


if __name__ == "__main__":
    main()
