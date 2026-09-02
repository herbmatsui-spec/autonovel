#!/usr/bin/env python3
"""PromptOps CLI commands for managing prompt templates and versions."""

import argparse
import sys
from pathlib import Path


def init_command(args):
    """Initialize PromptOps package structure."""
    project_root = Path.cwd()

    # Define directories to create
    dirs = [
        "src/promptops",
        "src/promptops/repositories",
        "src/promptops/services",
        "tests/promptops",
        "docs",
    ]

    print("Creating PromptOps package structure...")
    for d in dirs:
        path = project_root / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {d}")

    # Create __init__.py files
    init_files = [
        "src/promptops/__init__.py",
        "src/promptops/repositories/__init__.py",
        "src/promptops/services/__init__.py",
        "tests/promptops/__init__.py",
    ]

    for f in init_files:
        path = project_root / f
        if not path.exists():
            path.touch()
            print(f"  Created: {f}")

    # Create scaffold files
    scaffold_files = {
        "src/promptops/registry.py": '''"""PromptOps Registry - Dynamic template loading with versioning."""\n\n__version__ = "0.1.0"\n\nfrom .prompt_registry import PromptRegistry\nfrom .ab_test_router import ABTestRouter, ABTestConfig\n\n__all__ = ["PromptRegistry", "ABTestRouter", "ABTestConfig"]\n''',
        "src/promptops/prompt_registry.py": '''"""Prompt Registry with dynamic .j2 template loading and version management."""\n\nimport os\nfrom pathlib import Path\nfrom typing import Dict, Optional, Any\n\nfrom jinja2 import Environment, FileSystemLoader, select_autoescape\n\n\nclass PromptRegistry:\n    """Registry for managing prompt templates with versioning."""\n    \n    def __init__(self, templates_dir: Optional[str] = None):\n        if templates_dir:\n            self.templates_dir = Path(templates_dir)\n        else:\n            self.templates_dir = Path(__file__).parent.parent.parent / "prompts"\n        \n        self._env = Environment(\n            loader=FileSystemLoader(str(self.templates_dir)),\n            autoescape=select_autoescape(),\n        )\n        self._cache: Dict[str, str] = {}\n    \n    def get_template(self, name: str) -> str:\n        """Get template source by name."""\n        if name in self._cache:\n            return self._cache[name]\n        \n        template = self._env.get_template(name)\n        source = template.source if hasattr(template, 'source') else str(template)\n        self._cache[name] = source\n        return source\n    \n    def render(self, name: str, context: Dict[str, Any]) -> str:\n        """Render template with context."""\n        template = self._env.from_string(self.get_template(name))\n        return template.render(**context)\n    \n    def clear_cache(self):\n        """Clear template cache."""\n        self._cache.clear()\n''',
        "src/promptops/ab_test_router.py": '''"""A/B Test Router for deterministic variant assignment."""\n\nimport hashlib\nfrom dataclasses import dataclass\n\n\n@dataclass(frozen=True)\nclass ABTestConfig:\n    bucket_count: int = 100\n    rollout_percentage: float = 100.0\n\n\nclass ABTestRouter:\n    def __init__(self, config: ABTestConfig = None):\n        self.config = config or ABTestConfig()\n    \n    def get_bucket(self, user_id: str, request_id: str = None) -> int:\n        combined = f"{user_id}:{request_id or 'default'}"\n        hash_value = int(hashlib.sha256(combined.encode()).hexdigest(), 16)\n        return hash_value % self.config.bucket_count\n    \n    def get_version_tag(self, user_id: str, version_tags: list, request_id: str = None) -> str:\n        if not version_tags:\n            raise ValueError("No version tags provided")\n        if len(version_tags) == 1:\n            return version_tags[0]\n        bucket = self.get_bucket(user_id, request_id)\n        return version_tags[bucket % len(version_tags)]\n''',
        "tests/promptops/test_registry.py": '''"""Tests for PromptRegistry."""\n\nimport pytest\nfrom src.promptops.registry import PromptRegistry\n\n\ndef test_registry_creation():\n    registry = PromptRegistry()\n    assert registry is not None\n\n\ndef test_template_loading():\n    registry = PromptRegistry()\n    # This will fail if no templates exist - adjust as needed\n    # template = registry.get_template("example.j2")\n    # assert template is not None\n    pass\n\n\ndef test_template_rendering():\n    registry = PromptRegistry()\n    # result = registry.render("example.j2", {"var": "value"})\n    # assert "value" in result\n    pass\n''',
        "tests/promptops/test_ab_test_router.py": '''"""Tests for ABTestRouter."""\n\nimport pytest\nfrom src.promptops.ab_test_router import ABTestRouter, ABTestConfig\n\n\ndef test_deterministic_bucketing():\n    router = ABTestRouter(ABTestConfig(bucket_count=100))\n    bucket1 = router.get_bucket("user123", "req456")\n    bucket2 = router.get_bucket("user123", "req456")\n    assert bucket1 == bucket2\n\n\ndef test_different_users_different_buckets():\n    router = ABTestRouter(ABTestConfig(bucket_count=100))\n    buckets = {router.get_bucket(f"user{i}") for i in range(1000)}\n    # Should distribute across many buckets\n    assert len(buckets) > 50\n\n\ndef test_version_tag_selection():\n    router = ABTestRouter(ABTestConfig(bucket_count=100))\n    tags = ["v1", "v2", "v3"]\n    selected = router.get_version_tag("user123", tags)\n    assert selected in tags\n''',
    }

    for filepath, content in scaffold_files.items():
        path = project_root / filepath
        if not path.exists():
            path.write_text(content)
            print(f"  Created: {filepath}")

    print("\nPromptOps scaffold created successfully!")
    print("\nNext steps:")
    print("  1. Add your .j2 templates to the prompts/ directory")
    print("  2. Import PromptRegistry from src.promptops.registry")
    print("  3. Use ABTestRouter for A/B testing variants")


def list_templates_command(args):
    """List available prompt templates."""
    prompts_dir = Path.cwd() / "prompts"
    if not prompts_dir.exists():
        print("No prompts directory found.")
        return

    templates = list(prompts_dir.rglob("*.j2"))
    if not templates:
        print("No .j2 templates found in prompts/")
        return

    print("Available prompt templates:")
    for t in sorted(templates):
        rel = t.relative_to(prompts_dir)
        print(f"  {rel}")


def version_command(args):
    """Show PromptOps version."""
    from src.promptops.registry import __version__

    print(f"PromptOps {__version__}")


def main():
    parser = argparse.ArgumentParser(
        prog="kilo promptops",
        description="PromptOps - Prompt template management with versioning and A/B testing",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init command
    subparsers.add_parser("init", help="Initialize PromptOps package structure")

    # list-templates command
    subparsers.add_parser("list-templates", help="List available prompt templates")

    # version command
    subparsers.add_parser("version", help="Show PromptOps version")

    args = parser.parse_args()

    if args.command == "init":
        init_command(args)
    elif args.command == "list-templates":
        list_templates_command(args)
    elif args.command == "version":
        version_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
