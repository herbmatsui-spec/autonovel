from typing import Annotated, Any

from pydantic import AliasChoices, BaseModel, BeforeValidator, Field


def extract_int(v: Any) -> int:
    print(f"extract_int called with: {v!r}")
    if isinstance(v, int): return v
    return 99 # Dummy for testing

class PlotEpisode(BaseModel):
    stress: Annotated[int, BeforeValidator(extract_int)] = Field(default=0, validation_alias=AliasChoices("stress", "stress_delta"))

# Test 1: Alias present
print("Testing alias...")
obj = PlotEpisode.model_validate({"stress_delta": "High"})
print(f"Result: {obj.stress=}")

# Test 2: Missing
print("\nTesting missing...")
obj_empty = PlotEpisode.model_validate({})
print(f"Result: {obj_empty.stress=}")

