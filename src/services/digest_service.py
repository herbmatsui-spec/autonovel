def process_chapter(chapter: str) -> str:
    """章の中身から主要テキストを抽出"""
    max_length = 1500
    return chapter[:max_length].rstrip() + "..." if len(chapter) > max_length else chapter

def generate_suggestions(chapter: str) -> list[str]:
    """章の文脈から意味的な提案を生成"""
    return [
        f"続行: {chapter[:100]}...",
        "調査が必要な未確認な要素を指摘"
    ]
