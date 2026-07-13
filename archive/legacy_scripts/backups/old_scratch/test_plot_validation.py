
from models import PlotEpisode

# Test 1: Alias for complex field
input_data = {"ep": 10, "summary": "Big battle"}
try:
    obj = PlotEpisode.model_validate(input_data)
    print(f"Input: {input_data}")
    print(f"Result: {obj.ep_num=}, {obj.one_line_summary=}")
    if obj.ep_num == 10 and obj.one_line_summary == "Big battle":
        print("SUCCESS: Complex aliases were preserved.")
    else:
        print("FAIL: Complex aliases were lost.")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Injected defaults for int/str
input_data_empty = {}
try:
    obj_empty = PlotEpisode.model_validate(input_data_empty)
    print(f"\nInput: {input_data_empty}")
    print(f"Result: {obj_empty.tension=}, {obj_empty.resolution_style=}")
    if obj_empty.tension == 50 and obj_empty.resolution_style == "Cheat":
        print("SUCCESS: Defaults were injected correctly.")
    else:
        print("FAIL: Defaults were incorrect.")
except Exception as e:
    print(f"Error: {e}")

