CHAPTER_MAX_LENGTH = 1500


def process_chapter(chapter: str) -> str:
    """章本文から主要テキストを抽出する。

    入力文字列が ``CHAPTER_MAX_LENGTH`` (既定1500文字) を超える場合は、
    先頭 ``CHAPTER_MAX_LENGTH`` 文字を取り出し、右端の空白を除去したうえで
    省略記号 "..." を付与して返す。超えない場合は入力をそのまま返す。

    Args:
        chapter: 対象章の本文文字列。空文字列の場合は空文字列を返す。

    Returns:
        加工後の章本文文字列。
    """
    return (
        (chapter[:CHAPTER_MAX_LENGTH].rstrip() + "...")
        if len(chapter) > CHAPTER_MAX_LENGTH
        else chapter
    )


async def generate_suggestions(chapter: str) -> list[str]:
    """章の文脈から意味的な提案を生成する。

    将来的に LLM 連携を想定し非同期関数として定義。
    空文字列入力時はデフォルト提案を返す。

    Args:
        chapter: 対象章の本文文字列。

    Returns:
        提案文字列のリスト。
    """
    if not chapter:
        return ["続行: (空章のため先頭から再開)", "調査が必要な未確認な要素を指摘"]
    return [
        f"続行: {chapter[:100]}...",
        "調査が必要な未確認な要素を指摘",
    ]
