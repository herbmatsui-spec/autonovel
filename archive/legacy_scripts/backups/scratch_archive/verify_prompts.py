import os
import sys

# Add current directory to sys.path
sys.path.append(os.getcwd())

try:
    from jinja2 import DictLoader, Environment

    from config import PROMPT_TEMPLATES
    from prompts.manager import PromptManager

    # Mocking Jinja environment
    jinja_env = Environment(loader=DictLoader(PROMPT_TEMPLATES))
    pm = PromptManager(jinja_env)

    print("Verifying build_character_concept_prompt...")
    p1 = pm.build_character_concept_prompt("fantasy", "magic")
    print("Success.")

    print("Verifying build_title_generation_prompt...")
    p2 = pm.build_title_generation_prompt("fantasy", "magic")
    print("Success.")

    print("Verifying build_hegemony_prediction_prompt...")
    p3 = pm.build_hegemony_prediction_prompt("fantasy", "Hegemony", "Concept")
    print("Success.")

    print("\nAll verifications passed!")

except Exception as e:
    print(f"\nVerification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

