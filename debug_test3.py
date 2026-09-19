from src.annotations.parser import parse_beats, _estimate_speaker, _estimate_target
import re

# Use the actual character set from the config
chars = {'A', 'B', 'C', '主人公', 'ヒロイン', '敵', '味方', '師匠', '弟子', 'ライバル'}

text = 'A「行くぞ」\n[beat:fear+0.6 cause="ep14 betrayal"]\nB「待ちなさい」'
print(f'Input text: {repr(text)}')

BEAT_PATTERN = re.compile(r'\[beat:(\w+)([+-]\d+\.?\d*)\s*(?:cause="([^"]*)")?\s*(hidden)?\]', re.IGNORECASE)

for m in BEAT_PATTERN.finditer(text):
    print(f'Match: {m.groups()} at {m.span()}')
    speaker = _estimate_speaker(text, m.start(), chars)
    target = _estimate_target(text, m.start(), chars, speaker)
    print(f'Speaker: {repr(speaker)}, Target: {repr(target)}')

clean, beats = parse_beats(text, episode=15, scene=1, character_dict=chars)
print(f'Beats: {len(beats)}')
for b in beats:
    print(f'  {repr(b.source)}->{repr(b.target)} {b.emotion.value} {b.delta}')