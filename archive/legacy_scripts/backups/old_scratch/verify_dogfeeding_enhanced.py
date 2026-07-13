import sys

# Add project root to sys.path
sys.path.append(r'i:\claude2')

from pydantic import ValidationError

from models.audit import DogfeedingReport


def test_enhanced_dogfeeding_validation():
    print("Testing Enhanced DogfeedingReport validation...")

    data = {
        "critique_report": "AI is being too verbose.",
        "bias_direction": "Shifted towards high-fantasy metaphors.",
        "phenomenon_logic_map": [
            {
                "symptom": "Repeated use of 'the air was thick with...'",
                "cause_logic": "engine_prompts.py: Atmosphere template is too rigid.",
                "patch_target": "engine_prompts.py"
            }
        ],
        "engine_code_patch": "def fix_logic(): pass",
        "narrative_config_patch": "Modify prompt A",
        "improvement_milestones": ["Refactor narrative engine", "Add emotion caching"],
        "scores": {"consistency": 85}
    }

    try:
        m = DogfeedingReport.model_validate(data)
        print("[OK] Enhanced fields validation: Success")
        print(f"Symptoms mapped: {len(m.phenomenon_logic_map)}")
        print(f"Milestones count: {len(m.improvement_milestones)}")

        # Verify mapping content
        mapping = m.phenomenon_logic_map[0]
        assert mapping["symptom"] == "Repeated use of 'the air was thick with...'"
        assert mapping["patch_target"] == "engine_prompts.py"

    except ValidationError as e:
        print(f"[FAIL] Enhanced fields validation: Failed: {e}")
    except AssertionError:
        print("[FAIL] Content assertion failed")

if __name__ == "__main__":
    test_enhanced_dogfeeding_validation()

