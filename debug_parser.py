from src.annotations.parser import parse_beats, _estimate_speaker, _estimate_target

char_dict = {"A", "B", "C", "主人公", "ヒロイン"}
text = 'A「行くぞ」\n[beat:fear+0.6 cause="ep14 betrayal"]\nB「待ちなさい」'

# 正規表現でマッチ位置を取得
import re
BEAT_PATTERN = re.compile(r'\[beat:(\w+)([+-]\d+\.?\d*)\s*(?:cause="([^"]*)")?\s*(?:hidden)?\]', re.IGNORECASE)

for m in BEAT_PATTERN.finditer(text):
    print(f'Match: {m.groups()} at {m.span()}')
    speaker = _estimate_speaker(text, m.start(), char_dict)
    target = _estimate_target(text, m.start(), char_dict, speaker)
    print(f'Speaker: {speaker}, Target: {target}')