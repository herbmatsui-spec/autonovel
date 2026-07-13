
from pydantic import AliasChoices, BaseModel, Field


class CharacterRegistry(BaseModel):
    name: str = Field(default="", validation_alias=AliasChoices("name", "char_name"))
    iron_constraint: str = Field(default="", validation_alias=AliasChoices("iron_constraint", "iron_const"))

try:
    obj = CharacterRegistry.model_validate({})
    print(f"Empty dict: {obj.iron_constraint=}")
except Exception as e:
    print(f"Empty dict failed: {e}")

try:
    obj = CharacterRegistry.model_validate({"name": "Hero"})
    print(f"Partial dict: {obj.iron_constraint=}")
except Exception as e:
    print(f"Partial dict failed: {e}")

try:
    obj = CharacterRegistry.model_validate({"iron_const": "No killing"})
    print(f"Alias dict: {obj.iron_constraint=}")
except Exception as e:
    print(f"Alias dict failed: {e}")

