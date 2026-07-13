import sys

# Add project root to path
sys.path.append(r'i:\claude2')

from backend.sanitizer import (
    PhysiologicalTranslator,
    PsychologicalNoiseGenerator,
    VocabularyOptimizer,
)
from config import PHYSIOLOGICAL_REPLACEMENTS


def test_sanitizer():
    print("--- Testing PhysiologicalTranslator ---")
    text = "彼は絶望し、怒りに震えた。"
    translated = PhysiologicalTranslator.translate(text)
    print(f"Original: {text}")
    print(f"Translated: {translated}")

    for emotion, replacement in PHYSIOLOGICAL_REPLACEMENTS.items():
        if emotion in text:
            if replacement in translated:
                print(f"[OK] Correctly replaced {emotion}")
            else:
                print(f"[FAIL] Failed to replace {emotion}")

    print("\n--- Testing PsychologicalNoiseGenerator (Infiltration) ---")
    text = "私たちは幸せな日常を過ごしていた。未来は明るいと信じていた。"
    # thinning_rate = 0.5 (Infiltration phase)
    noised = PsychologicalNoiseGenerator.apply(text, 0.5, False)
    print(f"Original: {text}")
    print(f"Noised (0.5): {noised}")
    if "（……おかしい……？）" in noised:
        print("✅ Infiltration noise detected")
    else:
        print("⚠️ No noise detected (this is probabilistic, but check if keywords match)")

    print("\n--- Testing PsychologicalNoiseGenerator (Collapse) ---")
    # thinning_rate = 0.8 (Collapse phase)
    collapsed = PsychologicalNoiseGenerator.apply(text, 0.8, False)
    print(f"Original: {text}")
    print(f"Collapsed (0.8): {collapsed}")

    found_dread = False
    for emotion, dread in PsychologicalNoiseGenerator.ONTOLOGICAL_DREAD_TRANSLATIONS.items():
        # Note: text doesn't have "自分" etc, let's add one
        pass

    text_with_dread = "私は自分を見失った。"
    collapsed_dread = PsychologicalNoiseGenerator.apply(text_with_dread, 0.8, False)
    print(f"Original: {text_with_dread}")
    print(f"Collapsed Dread: {collapsed_dread}")

    if "肉体と呼称される『器』" in collapsed_dread:
        print("✅ Ontological dread translation detected")
    else:
        print("❌ Ontological dread translation failed")

    print("\n--- Testing VocabularyOptimizer ---")
    text = "しかしながら、その結果として彼は驚愕した。"
    optimized = VocabularyOptimizer.deduplicate(text, genre="dark_fantasy")
    print(f"Original: {text}")
    print(f"Optimized: {optimized}")
    if "だが" in optimized and "ゆえに" in optimized:
        print("✅ Conjunction optimization detected")
    if any(v in optimized for v in PHYSIOLOGICAL_REPLACEMENTS.values()):
        print("✅ Physiological translation integrated in optimizer")

if __name__ == "__main__":
    test_sanitizer()

