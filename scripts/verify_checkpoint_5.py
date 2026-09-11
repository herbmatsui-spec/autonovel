from src.services.exporters.epub_commercial_builder import CommercialEpubBuilder

b = CommercialEpubBuilder().build_commercial_epub(
    {'title': 'テスト作', 'author': 'AI'},
    [{'title': '第1話', 'content': '｜魔導《まどう》覚醒。'}]
)
assert len(b) > 1000
print("Part 5 Checkpoint PASS")
