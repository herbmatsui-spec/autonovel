from typing import List

from pydantic import BaseModel, Field


class Foreshadowing(BaseModel):
    clue: str = Field(description="Clue")
    resolution: str = Field(description="Resolution")

class NarrativeConstraint(BaseModel):
    name: str = Field(description="Constraint name")

class ClimaxScene(BaseModel):
    description: str = Field(description="Scene description")
    foreshadowing_refs: List[str] = Field(description="Refs")

class Output(BaseModel):
    foreshadowing_map: List[Foreshadowing]
    active_constraints: List[NarrativeConstraint]
    climax_scenes: List[ClimaxScene]

raw_schema = Output.model_json_schema()

def _resolve_refs(schema_dict: dict, defs: dict) -> dict:
    if isinstance(schema_dict, dict):
        if "$ref" in schema_dict:
            ref_path = schema_dict["$ref"]
            if ref_path.startswith("#/$defs/"):
                def_name = ref_path.split("/")[-1]
                if def_name in defs:
                    resolved = _resolve_refs(defs[def_name], defs)
                    new_dict = {k: v for k, v in schema_dict.items() if k != "$ref"}
                    new_dict.update(resolved)
                    return new_dict

        # Also handle anyOf with null for Optionals which Gemini might not like
        # But let's first just resolve refs
        return {k: _resolve_refs(v, defs) for k, v in schema_dict.items()}
    elif isinstance(schema_dict, list):
        return [_resolve_refs(item, defs) for item in schema_dict]
    return schema_dict

def _clean_schema(schema_dict: dict) -> dict:
    if isinstance(schema_dict, dict):
        if "additionalProperties" in schema_dict:
            del schema_dict["additionalProperties"]
        if "type" in schema_dict and isinstance(schema_dict["type"], str):
            schema_dict["type"] = schema_dict["type"].upper()

        if "title" in schema_dict:
            del schema_dict["title"]
        if "default" in schema_dict:
            del schema_dict["default"]

        for k, v in list(schema_dict.items()):
            schema_dict[k] = _clean_schema(v)
    elif isinstance(schema_dict, list):
        schema_dict = [_clean_schema(item) for item in schema_dict]
    return schema_dict

import json

defs = raw_schema.pop("$defs", {})
if defs:
    raw_schema = _resolve_refs(raw_schema, defs)
clean_schema = _clean_schema(raw_schema)
print(json.dumps(clean_schema, indent=2))

