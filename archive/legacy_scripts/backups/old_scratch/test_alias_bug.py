
from models import CharacterRegistry

# Input has alias but not primary name
input_data = {"iron_const": "No killing"}
try:
    obj = CharacterRegistry.model_validate(input_data)
    print(f"Input: {input_data}")
    print(f"Result: {obj.iron_constraint=}")
    if obj.iron_constraint == "No killing":
        print("SUCCESS: Alias value was preserved.")
    else:
        print(f"FAIL: Alias value was lost! Expected 'No killing', got '{obj.iron_constraint}'")
except Exception as e:
    print(f"Error: {e}")

# Input is empty
input_data_empty = {}
try:
    obj_empty = CharacterRegistry.model_validate(input_data_empty)
    print(f"\nInput: {input_data_empty}")
    print(f"Result: {obj_empty.name=}, {obj_empty.iron_constraint=}")
    if obj_empty.name == "" and obj_empty.iron_constraint == "":
        print("SUCCESS: Defaults were injected.")
    else:
        print("FAIL: Defaults were not injected.")
except Exception as e:
    print(f"Error: {e}")

