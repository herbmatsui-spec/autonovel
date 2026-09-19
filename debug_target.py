from src.annotations.parser import _estimate_target

char_dict = {"A", "B", "C", "主人公", "ヒロイン"}
text = 'A「行くぞ」\n[beat:fear+0.6 cause="ep14 betrayal"]\nB「待ちなさい」'

import re
BEAT_PATTERN = re.compile(r'\[beat:(\w+)([+-]\d+\.?\d*)\s*(?:cause="([^"]*)")?\s*(?:hidden)?\]', re.IGNORECASE)

for m in BEAT_PATTERN.finditer(text):
    print(f'Match at {m.span()}')
    prefix = text[:m.start()]
    print(f'Prefix: {repr(prefix)}')
    print(f'Prefix[-500:]: {repr(prefix[-500:])}')
    
    speaker = "A"
    for char in char_dict:
        if char != speaker:
            if char in prefix[-500:]:
                print(f'Found in prefix: {repr(char)}')