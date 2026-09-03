#!/usr/bin/env python3
"""OpenAPI JSON (docs/openapi.json) から TypeScript 型定義 (frontend/src/types/api.generated.ts) を生成するスクリプト。

npm/npx環境に依存せず、CIやローカルで高速・決定論的にTypeScript型を生成する。
"""

from __future__ import annotations

import json
from pathlib import Path


def convert_schema_type(prop: dict) -> str:
    """JSON Schema のプロパティ定義を TypeScript の型文字列に変換する。"""
    if "$ref" in prop:
        ref_name = prop["$ref"].split("/")[-1]
        return ref_name

    if "anyOf" in prop or "oneOf" in prop:
        variants = prop.get("anyOf") or prop.get("oneOf", [])
        types = [convert_schema_type(v) for v in variants if v.get("type") != "null"]
        if any(v.get("type") == "null" for v in variants):
            types.append("null")
        return " | ".join(types) if types else "unknown"

    schema_type = prop.get("type")
    if schema_type == "string":
        if "enum" in prop:
            return " | ".join(f'"{v}"' for v in prop["enum"])
        return "string"
    elif schema_type in ("integer", "number"):
        return "number"
    elif schema_type == "boolean":
        return "boolean"
    elif schema_type == "array":
        items = prop.get("items", {})
        item_type = convert_schema_type(items)
        return f"{item_type}[]"
    elif schema_type == "object":
        if "properties" in prop:
            sub_props = prop["properties"]
            required = set(prop.get("required", []))
            lines = ["{"]
            for k, v in sub_props.items():
                optional = "" if k in required else "?"
                v_type = convert_schema_type(v)
                lines.append(f"    {k}{optional}: {v_type};")
            lines.append("  }")
            return "\n".join(lines)
        if "additionalProperties" in prop:
            add_type = convert_schema_type(prop["additionalProperties"])
            return f"Record<string, {add_type}>"
        return "Record<string, unknown>"
    return "unknown"


def generate_ts(openapi_path: Path, out_path: Path) -> None:
    spec = json.loads(openapi_path.read_text(encoding="utf-8"))
    schemas = spec.get("components", {}).get("schemas", {})

    lines: list[str] = [
        "/**",
        " * AutoNovel OpenAPI 自動生成 TypeScript 型定義",
        " * このファイルは scripts/generate_ts_types.py によって自動生成されています。",
        " * 手動での直接編集は行わないでください。",
        " */",
        "",
    ]

    for schema_name, schema_data in schemas.items():
        description = schema_data.get("description", "")
        if description:
            lines.append(f"/** {description} */")

        schema_type = schema_data.get("type", "object")
        if schema_type == "object" and "properties" in schema_data:
            props = schema_data.get("properties", {})
            required = set(schema_data.get("required", []))
            lines.append(f"export interface {schema_name} {{")
            for prop_name, prop_def in props.items():
                prop_desc = prop_def.get("description")
                if prop_desc:
                    lines.append(f"  /** {prop_desc} */")
                optional = "" if prop_name in required else "?"
                prop_type = convert_schema_type(prop_def)
                lines.append(f"  {prop_name}{optional}: {prop_type};")
            lines.append("}")
            lines.append("")
        elif "enum" in schema_data:
            enum_vals = " | ".join(f'"{v}"' for v in schema_data["enum"])
            lines.append(f"export type {schema_name} = {enum_vals};")
            lines.append("")
        else:
            ts_type = convert_schema_type(schema_data)
            lines.append(f"export type {schema_name} = {ts_type};")
            lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated TypeScript types at: {out_path}")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    openapi_file = root / "docs" / "openapi.json"
    out_file = root / "frontend" / "src" / "types" / "api.generated.ts"

    if not openapi_file.exists():
        print(f"Error: {openapi_file} not found. Run scripts/generate_openapi.py first.")
        return 1

    generate_ts(openapi_file, out_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
