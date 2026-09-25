"""
Regression tests for environment variable and secret security guardrails.
Verifies that sensitive files are ignored by git, not tracked, and templates do not leak credentials.
"""

import os
import re
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_env_file_not_tracked_by_git():
    """Verify that .env is NOT tracked in git index."""
    res = subprocess.run(
        ["git", "ls-files", ".env"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_files = res.stdout.strip()
    assert tracked_files == "", f".env file should NOT be tracked in git! Found: {tracked_files}"


def test_gitignore_contains_env():
    """Verify that .gitignore contains .env and .env.local rules."""
    gitignore_path = REPO_ROOT / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist"
    content = gitignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines()]
    
    assert ".env" in lines, ".gitignore must ignore '.env'"
    assert ".env.local" in lines, ".gitignore must ignore '.env.local'"


def test_env_example_has_no_real_secrets():
    """Verify that .env.example does not contain real secret tokens or real passwords."""
    env_example_path = REPO_ROOT / ".env.example"
    assert env_example_path.exists(), ".env.example must exist"
    content = env_example_path.read_text(encoding="utf-8")
    
    suspicious_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI API keys
        r"ghp_[a-zA-Z0-9]{20,}",  # GitHub personal access tokens
        r"(?:password|secret)\s*=\s*['\"]?(?!your_|change_me|autonovel_dev_password_change_me)[a-zA-Z0-9!@#$%^&*()_+]{8,}['\"]?",
    ]
    
    for pattern in suspicious_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        assert not match, f"Found suspicious secret pattern in .env.example: {match.group(0)}"


def test_docker_compose_no_hardcoded_passwords():
    """Verify that docker-compose.yml uses environment variable interpolation for passwords."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist"
    content = compose_path.read_text(encoding="utf-8")

    # POSTGRES_PASSWORD should be variable-interpolated: ${POSTGRES_PASSWORD...}
    # It must not be a bare string like POSTGRES_PASSWORD=autonovel
    match = re.search(r"POSTGRES_PASSWORD=([^\s$]+)", content)
    assert match is None, f"Found hardcoded POSTGRES_PASSWORD in docker-compose.yml: {match.group(0) if match else ''}"
