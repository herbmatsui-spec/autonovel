with open('E:/hhh/src/services/compression/layer3_abstraction.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add the entry after the 指輪 line
content = content.replace(
    '    "指輪": "魔力補助装飾品",',
    '    "指輪": "魔力補助装飾品",\n    "魔剣バルムンク": "伝説級",'
)

with open('E:/hhh/src/services/compression/layer3_abstraction.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added 魔剣バルムンク -> 伝説級 to CONCEPT_TAXONOMY')