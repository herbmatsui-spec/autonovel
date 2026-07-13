from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, Field, model_validator


class CharacterRegistry(BaseModel):
    name: Optional[str] = Field(default="", validation_alias=AliasChoices("name", "char_name"))
    iron_constraint: Optional[str] = Field(default="", validation_alias=AliasChoices("iron_constraint", "iron_const"))

    @model_validator(mode="before")
    @classmethod
    def unwrap_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            str_fields = ["name", "iron_constraint"]
            for f in str_fields:
                if f not in data:
                    data[f] = data.get(f, "")
        return data

class WorldBibleCore(BaseModel):
    mc_profile: CharacterRegistry = Field(default_factory=CharacterRegistry)

# Test 1: Empty dict
try:
    print("Testing empty dict...")
    res = WorldBibleCore.model_validate({"mc_profile": {}})
    print(f"Success: {res.mc_profile.iron_constraint=}")
except Exception as e:
    print(f"Failed: {e}")

# Test 2: Partial dict
try:
    print("\nTesting partial dict...")
    res = WorldBibleCore.model_validate({"mc_profile": {"name": "Hero"}})
    print(f"Success: {res.mc_profile.iron_constraint=}")
except Exception as e:
    print(f"Failed: {e}")

# Test 3: Dict with alias
try:
    print("\nTesting dict with alias...")
    res = WorldBibleCore.model_validate({"mc_profile": {"iron_const": "No killing"}})
    print(f"Success: {res.mc_profile.iron_constraint=}")
except Exception as e:
    print(f"Failed: {e}")

