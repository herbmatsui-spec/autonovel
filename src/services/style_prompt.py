"""services/style_prompt.py - 学習済み文体をプロンプト注入用文字列に整形"""

from pathlib import Path
from typing import Optional

from src.filesystem_memory.paths import get_workspace_path
from src.filesystem_memory.writer import read_file_safe


def _extract_section(content: str, section_name: str) -> str:
    """content から "## {section_name}" 行以降、次の ## 行または末尾までのテキストを抽出。
    見つからない場合は空文字列を返す。
    """
    lines = content.splitlines()
    in_section = False
    extracted: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") and stripped[3:] == section_name:
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## "):
                # 次のセクションへ
                break
            extracted.append(line)
    # 改行で結合し、先頭・末尾の空白を削除
    return "\n".join(extracted).strip()


def build_style_injection(book_id: int, branch_id: int = 1) -> str:
    """STYLE_LEARNED.md を読み込み、[学習済み文体] ブロックを生成。
    ファイルが存在しないか、セクションが空の場合は空文字列を返す。
    """
    style_path = get_workspace_path(book_id, branch_id) / "STYLE_LEARNED.md"
    content = read_file_safe(style_path)
    if not content:
        return ""

    # 各セクションを抽出
    top_words = _extract_section(content, "頻出語（上位N）")
    avg_len = _extract_section(content, "平均文長")
    particles = _extract_section(content, "助詞傾向")
    banned = _extract_section(content, "禁則語（検出履歴）")
    sample = _extract_section(content, "直近サンプル文")

    # すべてが空なら何もしない
    if not any([top_words, avg_len, particles, banned, sample]):
        return ""

    # ブロックを整形
    lines = [
        "[学習済み文体]",
        "以下はこれまでの章から学習した文体特徴です。参考にしてください：",
        "",
    ]
    if top_words:
        lines.append(f"・頻出語: {top_words}")
    if avg_len:
        lines.append(f"・平均文長: {avg_len}")
    if particles:
        lines.append(f"・助詞傾向: {particles}")
    if banned:
        lines.append(f"・禁則語: {banned}")
    if sample:
        lines.append(f"・直近サンプル: {sample}")
    lines.append("")  # 終端の空行
    return "\n".join(lines)