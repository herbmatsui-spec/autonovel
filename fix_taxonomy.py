lines = []
with open('E:/hhh/src/services/compression/layer3_abstraction.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Replace lines 30-48 (the content of CONCEPT_TAXONOMY)
lines[30] = 'CONCEPT_TAXONOMY = {\n'
lines[31] = '    # 戦闘・武術\n'
lines[32] = '    "抜刀": "近接剣術スキル",\n'
lines[33] = '    "居合": "近接剣術スキル",\n'
lines[34] = '    "迅雷": "雷属性攻撃",\n'
lines[35] = '    "火球": "火炎魔術",\n'
lines[36] = '    "爆縮": "高密度破壊魔術",\n'
lines[37] = '    "治癒": "回復術式",\n'
lines[38] = '    # 政治・社会\n'
lines[39] = '    "関税": "経済統制政策",\n'
lines[40] = '    "同盟": "国家間外交協定",\n'
lines[41] = '    "宣戦": "軍事侵攻決定",\n'
lines[42] = '    "密定": "情報諜報網",\n'
lines[43] = '    "追放": "勢力追放・排斥",\n'
lines[44] = '    # アイテム・装備\n'
lines[45] = '    "聖剣": "伝説級武装",\n'
lines[46] = '    "魔導書": "古代遺物",\n'
lines[47] = '    "ポーション": "回復消耗品",\n'
lines[48] = '    "指輪": "魔力補助装飾品",\n'
lines[49] = '}\n'

with open('E:/hhh/src/services/compression/layer3_abstraction.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('File updated')