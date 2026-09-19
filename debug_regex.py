import re
BEAT_PATTERN = re.compile(r'\[beat:(\w+)([+-]\d+\.?\d*)\s*(?:cause="([^"]*)")?\s*(?:hidden)?\]', re.IGNORECASE)
text = 'A「行くぞ」\n[beat:fear+0.6 cause="ep14 betrayal"]\nB「待ちなさい」'
for m in BEAT_PATTERN.finditer(text):
    print(f'Match: {m.groups()} at {m.span()}')

text2 = '[beat:aff+0.3][beat:ten-0.2] A「行く」'
for m in BEAT_PATTERN.finditer(text2):
    print(f'Match2: {m.groups()} at {m.span()}')

text3 = 'A「平気だ」[beat:fear+0.8 hidden]'
for m in BEAT_PATTERN.finditer(text3):
    print(f'Match3: {m.groups()} at {m.span()}')