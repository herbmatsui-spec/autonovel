import os
import sys

# Add the root directory to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.sanitizer import PhysiologicalTranslator


def test_translator():
    text = "彼は激怒し、そして歓喜した。深い落胆の後、安堵の息をついた。"
    print("--- 翻訳前 ---")
    print(text)

    print("\n--- ライトジャンル (is_dark=False) ---")
    res_light = PhysiologicalTranslator.translate(text, is_dark=False)
    print(res_light)

    print("\n--- ダークジャンル (is_dark=True) ---")
    res_dark = PhysiologicalTranslator.translate(text, is_dark=True)
    print(res_dark)

    # Check if EXTENDED_REPLACEMENTS worked
    assert "激怒" in res_light, "Light genre should not translate '激怒' with extended map"
    assert "激怒" not in res_dark, "Dark genre should translate '激怒'"
    assert "血の色に染まり" in res_dark, "Dark genre should apply extended physiological replacement"
    print("\n[OK] PhysiologicalTranslator logic works perfectly!")

if __name__ == "__main__":
    test_translator()

