#!/usr/bin/env python3
"""
API ルート自動ドキュメント生成スクリプト.

FastAPI アプリから OpenAPI スキーマを取得し、
マークダウン形式の API ドキュメントを生成する。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backend.server import app


def _group_endpoints_by_tag(paths: dict) -> dict[str, list[dict]]:
    """エンドポイントをタグごとにグループ化"""
    from typing import Any
    tag_to_endpoints: dict[str, list[dict[str, Any]]] = {}
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                tags = details.get("tags", ["default"])
                for tag in tags:
                    tag_to_endpoints.setdefault(tag, []).append({
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "operation_id": details.get("operationId", ""),
                        "parameters": details.get("parameters", []),
                        "responses": details.get("responses", {}),
                        "request_body": details.get("requestBody", {}),
                    })
    return tag_to_endpoints


def _format_parameters(parameters: list[dict]) -> list[str]:
    """パラメータをマークダウン形式で整形"""
    lines = []
    for param in parameters:
        param_str = f"- `{param['name']}` ({param['in']})"
        if param.get("required"):
            param_str += " **必須**"
        if param.get("schema"):
            schema = param["schema"]
            param_str += f" - 型: {schema.get('type', 'unknown')}"
        if param.get("description"):
            param_str += f" - {param['description']}"
        lines.append(param_str)
    return lines


def _format_request_body(request_body: dict) -> list[str]:
    """リクエストボディをマークダウン形式で整形"""
    lines = []
    content = request_body.get("content", {})
    for media_type, schema_info in content.items():
        lines.append(f"- Content-Type: `{media_type}`")
        schema = schema_info.get("schema", {})
        if "$ref" in schema:
            lines.append(f"  - スキーマ: {schema['$ref']}")
    return lines


def _format_responses(responses: dict) -> list[str]:
    """レスポンスをマークダウン形式で整形"""
    lines = []
    for status_code, response in responses.items():
        lines.append(f"- `{status_code}`: {response.get('description', '')}")
        content = response.get("content", {})
        for media_type, schema_info in content.items():
            lines.append(f"  - Content-Type: `{media_type}`")
            schema = schema_info.get("schema", {})
            if "$ref" in schema:
                lines.append(f"  - スキーマ: {schema['$ref']}")
    return lines


def _format_endpoint(ep: dict) -> list[str]:
    """単一エンドポイントをマークダウン形式で整形"""
    lines = []
    lines.append(f"#### `{ep['method']} {ep['path']}`")
    lines.append("")

    if ep["summary"]:
        lines.append(f"**概要**: {ep['summary']}")
        lines.append("")

    if ep["description"]:
        lines.append(ep["description"])
        lines.append("")

    if ep["parameters"]:
        lines.append("**パラメータ**:")
        lines.append("")
        lines.extend(_format_parameters(ep["parameters"]))
        lines.append("")

    if ep["request_body"]:
        lines.append("**リクエストボディ**:")
        lines.append("")
        lines.extend(_format_request_body(ep["request_body"]))
        lines.append("")

    if ep["responses"]:
        lines.append("**レスポンス**:")
        lines.append("")
        lines.extend(_format_responses(ep["responses"]))
        lines.append("")

    return lines


def generate_markdown_docs() -> str:
    """OpenAPI スキーマからマークダウン文書を生成"""
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    lines = [
        "# AutoNovel API ドキュメント",
        "",
        f"**バージョン**: {openapi.get('info', {}).get('version', 'unknown')}",
        f"**タイトル**: {openapi.get('info', {}).get('title', 'AutoNovel API')}",
        f"**説明**: {openapi.get('info', {}).get('description', '')}",
        "",
        "---",
        "",
        "## エンドポイント一覧",
        ""
    ]

    # タグごとにグループ化
    tag_to_endpoints = _group_endpoints_by_tag(paths)

    # タグごとに出力
    for tag in sorted(tag_to_endpoints.keys()):
        endpoints = tag_to_endpoints[tag]
        lines.append(f"### {tag}")
        lines.append("")

        for ep in endpoints:
            lines.extend(_format_endpoint(ep))
            lines.append("---")
            lines.append("")

    return "\n".join(lines)
def main():
    """メイン実行"""
    output_path = Path(__file__).resolve().parent.parent / "docs" / "api" / "endpoints.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    markdown = generate_markdown_docs()
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Generated: {output_path}")

    # OpenAPI JSON も保存
    json_path = output_path.parent / "openapi.json"
    json_path.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False))
    print(f"Generated: {json_path}")


if __name__ == "__main__":
    main()
