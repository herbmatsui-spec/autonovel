import yaml
from src.annotations.parser import parse_beats

data = yaml.safe_load(open('config/characters.yaml', encoding='utf-8'))
chars = set(data['characters'])
print('Set:', chars)
print('Contains 主人公:', '主人公' in chars)
print('Contains ヒロイン:', 'ヒロイン' in chars)

# Test parser with actual characters
text = 'A「行くぞ」\n[beat:fear+0.6 cause="ep14 betrayal"]\nB「待ちなさい」'
clean, beats = parse_beats(text, episode=15, scene=1, character_dict=chars)
print('Beats:', len(beats))
for b in beats:
    print(f'  {b.source}->{b.target} {b.emotion.value} {b.delta}')