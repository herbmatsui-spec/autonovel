from src.annotations.parser import parse_beats
from src.pipeline.character_dict import load_character_dict

chars = load_character_dict()

# Use Unicode escape sequences for Japanese text
text = "A\u300c\u884c\u3050\u305e\u300d\n[beat:fear+0.6 cause=\"ep14 betrayal\"]\nB\u300c\u5f85\u3061\u306a\u3055\u3044\u300d"

print("Input text:", repr(text))

clean, beats = parse_beats(text, episode=15, scene=1, character_dict=chars)
print("Beats:", len(beats))
for b in beats:
    print(f"  {repr(b.source)}->{repr(b.target)} {b.emotion.value} {b.delta}")