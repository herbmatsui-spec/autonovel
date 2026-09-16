with open('E:/hhh/tests/unit/test_compression_consistency_metrics.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Replace lines 6-10 (0-indexed indices 5-9)
lines[5] = '    text = "勇者アレンは聖剣バルムンクを構えた。背後には魔法使いエレナが控えている。古の予言『月が紅く染まる時』の謎が迫る。"\n'
lines[6] = '    protected = ProtectedContext(\n'
lines[7] = '        active_characters=["アレン", "エレナ"],\n'
lines[8] = '        pending_foreshadowing_ids=["月が紅く染まる時"],\n'
lines[9] = '    )\n'

with open('E:/hhh/tests/unit/test_compression_consistency_metrics.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("File updated successfully")