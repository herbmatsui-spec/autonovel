import json

from models.audit import HegemonyAuditResult

print("Imported HegemonyAuditResult successfully.")

response_schema = HegemonyAuditResult

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
        return {k: _resolve_refs(v, defs) for k, v in schema_dict.items()}
    elif isinstance(schema_dict, list):
        return [_resolve_refs(item, defs) for item in schema_dict]
    return schema_dict

def _clean_schema(schema_dict: dict) -> dict:
    if isinstance(schema_dict, dict):
        if "additionalProperties" in schema_dict:
            del schema_dict["additionalProperties"]
        if "title" in schema_dict:
            del schema_dict["title"]
        if "default" in schema_dict:
            del schema_dict["default"]

        if "anyOf" in schema_dict:
            types = [t for t in schema_dict["anyOf"] if isinstance(t, dict) and t.get("type") != "null" and t.get("type") != "NULL"]
            if types:
                valid_type = types[0]
                del schema_dict["anyOf"]
                schema_dict.update(valid_type)

        if "type" in schema_dict and isinstance(schema_dict["type"], str):
            schema_dict["type"] = schema_dict["type"].upper()

        for k, v in list(schema_dict.items()):
            schema_dict[k] = _clean_schema(v)
    elif isinstance(schema_dict, list):
        schema_dict = [_clean_schema(item) for item in schema_dict]
    return schema_dict

print("Running _resolve_refs and _clean_schema...")
raw_schema = response_schema.model_json_schema()
defs = raw_schema.pop("$defs", {})
if defs:
    raw_schema = _resolve_refs(raw_schema, defs)
clean_schema = _clean_schema(raw_schema)
print("Finished successfully! Clean schema:")
print(json.dumps(clean_schema, indent=2, ensure_ascii=False))

