"""
Token parser and BNF specification validator (PLAN_Y3 Step 1).
BNF:
  TOKEN    := "[" CATEGORY ":" KEY [":" MODIFIER]* "]"
  CATEGORY := "SUBTEXT" | "BEAT" | "ACTION" | "GLANCE" | "PAUSE" | "IRONY" | "INTERNAL"
  KEY      := [a-z0-9_]+
  MODIFIER := [a-z0-9_]+
"""

from __future__ import annotations

import re
from typing import List, Optional
from pydantic import BaseModel, Field

VALID_CATEGORIES = {
    "SUBTEXT",
    "BEAT",
    "ACTION",
    "GLANCE",
    "PAUSE",
    "IRONY",
    "INTERNAL",
}

TOKEN_REGEX = re.compile(r"\[([A-Z]+):([a-z0-9_]+(?:(?::[a-z0-9_]+)*))\]")


class TokenSpec(BaseModel):
    """Parsed representation of a control token."""
    category: str = Field(..., description="Token category in uppercase")
    key: str = Field(..., description="Primary token key")
    modifiers: List[str] = Field(default_factory=list, description="Sub-keys or modifiers")
    raw: str = Field(default="", description="Original raw token string")

    def full_path(self) -> List[str]:
        """Returns lowercase path hierarchy: [category, key, *modifiers]."""
        return [self.category.lower(), self.key] + self.modifiers


class TokenParser:
    """Parses and validates control tokens embedded in generated text."""

    @classmethod
    def is_valid_token(cls, token_str: str) -> bool:
        match = TOKEN_REGEX.fullmatch(token_str.strip())
        if not match:
            return False
        cat = match.group(1)
        return cat in VALID_CATEGORIES

    @classmethod
    def parse(cls, token_str: str) -> Optional[TokenSpec]:
        match = TOKEN_REGEX.fullmatch(token_str.strip())
        if not match:
            return None
        cat = match.group(1)
        if cat not in VALID_CATEGORIES:
            return None
        rest = match.group(2).split(":")
        key = rest[0]
        modifiers = rest[1:] if len(rest) > 1 else []
        return TokenSpec(
            category=cat,
            key=key,
            modifiers=modifiers,
            raw=token_str.strip(),
        )

    @classmethod
    def find_tokens(cls, text: str) -> List[TokenSpec]:
        tokens = []
        for match in TOKEN_REGEX.finditer(text):
            cat = match.group(1)
            if cat not in VALID_CATEGORIES:
                continue
            rest = match.group(2).split(":")
            tokens.append(
                TokenSpec(
                    category=cat,
                    key=rest[0],
                    modifiers=rest[1:] if len(rest) > 1 else [],
                    raw=match.group(0),
                )
            )
        return tokens
