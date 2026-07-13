import sys

# Add project root to sys.path
sys.path.append(r'i:\claude2')

from pydantic import ValidationError

from models.audit import DogfeedingReport


def test_dogfeeding_validation():
    print("Testing DogfeedingReport validation with aliases and defaults...")

    # Case 1: Ideal case (all correct field names)
    data1 = {
        "critique_report": "Looks good",
        "habits": "None",
        "prompt_patch": "Patch A",
        "coding_ai_instruction": "Fix B",
        "scores": {"quality": 90}
    }
    try:
        m1 = DogfeedingReport.model_validate(data1)
        print("[OK] Case 1 (Exact): Success")
        assert m1.coding_ai_instruction == "Fix B"
    except ValidationError as e:
        print(f"[FAIL] Case 1 (Exact): Failed: {e}")

    # Case 2: Using alias 'refactor_instruction'
    data2 = {
        "critique_report": "Looks good",
        "prompt_patch": "Patch A",
        "refactor_instruction": "Fix C",
        "scores": {"quality": 80}
    }
    try:
        m2 = DogfeedingReport.model_validate(data2)
        print("[OK] Case 2 (Alias): Success")
        assert m2.coding_ai_instruction == "Fix C"
        assert m2.habits == "" # Default value applied
    except ValidationError as e:
        print(f"[FAIL] Case 2 (Alias): Failed: {e}")

    # Case 3: Using alias 'instructions' and missing non-critical fields (critique_report has default now)
    data3 = {
        "instructions": "Fix D",
        "scores": {"quality": 70}
    }
    try:
        m3 = DogfeedingReport.model_validate(data3)
        print("[OK] Case 3 (Minimal + Alias): Success")
        assert m3.coding_ai_instruction == "Fix D"
        assert m3.critique_report == ""
    except ValidationError as e:
        print(f"[FAIL] Case 3 (Minimal + Alias): Failed: {e}")

if __name__ == "__main__":
    test_dogfeeding_validation()

