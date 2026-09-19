from src.annotations.parser import parse_beats
from src.pipeline.character_dict import load_character_dict

char_dict = load_character_dict()
print(f"Char dict: {char_dict}")

text = 'A「行くぞ」\n[beat:fear+0.6 cause="ep14 betrayal"]\nB「待ちなさい」'
print(f"Text: {repr(text)}")

clean, beats = parse_beats(text, episode=15, scene=1, character_dict=char_dict)
print(f"Clean: {repr(clean)}")
print(f"Beats: {len(beats)}")
for b in beats:
    print(f"  Beat: {b.source}->{b.target} {b.emotion.value} {b.delta}")