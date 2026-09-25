"""
TokenExpander: Expands embedded control tokens deterministically (PLAN_Y3 Step 4, 5, 6, 18, 19, 22).
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import yaml

from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_tokens.parser import TOKEN_REGEX, TokenParser, TokenSpec

logger = logging.getLogger("narrative.subtext_tokens.expander")


class TokenExpander:
    """Expands control tokens into stage directions, beats, or ironic subtext phrases."""

    def __init__(
        self,
        dict_path: Optional[str | Path] = None,
        lang: str = "ja",
    ) -> None:
        self.lang = lang
        self.dict_path = self._resolve_dict_path(dict_path, lang)
        self._dict: Dict[str, Any] = {}
        self.load_dictionary()

    def _resolve_dict_path(self, dict_path: Optional[str | Path], lang: str) -> Path:
        if dict_path:
            return Path(dict_path)
        base_dir = Path("data/subtext")
        if lang == "en":
            return base_dir / "tokens.en.yaml"
        elif lang == "zh":
            return base_dir / "tokens.zh.yaml"
        return base_dir / "tokens.yaml"

    def load_dictionary(self) -> None:
        """Loads token dictionary from YAML file with fallback to minimal built-in dict."""
        if self.dict_path.exists():
            try:
                self._dict = yaml.safe_load(self.dict_path.read_text(encoding="utf-8")) or {}
                return
            except Exception as e:
                logger.error(f"Failed to read token dictionary from {self.dict_path}: {e}")

        # Built-in minimal dictionary fallback (Step 19)
        self._dict = {
            "subtext": {
                "irony": {"templates": ["「……{phrase}」"], "phrases": ["好きにすればいい"]},
                "cold_acceptance": {"templates": ["「……{phrase}」——{action}。"], "phrases": ["それでいい"], "actions": ["目を伏せる"]},
            },
            "beat": {"pause": {"short": ["……"], "long": ["沈黙が流れる"]}},
            "glance": {"away": ["視線を逸らす"]},
            "pause": {"breath": ["深く息を吐く"]},
        }

    def resolve_token(
        self,
        spec: TokenSpec,
        rnd: Optional[random.Random] = None,
        context: Optional[SubtextContext] = None,
    ) -> Optional[str]:
        """Public method checking if a token resolves in the dictionary."""
        r = rnd or random.Random(42)
        return self._resolve_token_value(spec, r, context)

    def _resolve_token_value(
        self, spec: TokenSpec, rnd: random.Random, context: Optional[SubtextContext]
    ) -> Optional[str]:
        """Traverses the dictionary using the token spec path and selects a value."""
        cur = self._dict
        for step in spec.full_path():
            if isinstance(cur, dict) and step in cur:
                cur = cur[step]
            else:
                cur = None
                break

        if cur is None:
            return None

        # Case 1: List of strings
        if isinstance(cur, list):
            if not cur:
                return ""
            return rnd.choice(cur)

        # Case 2: Dict containing 'templates' and 'phrases' / 'actions'
        if isinstance(cur, dict) and "templates" in cur:
            templates = cur.get("templates", [])
            phrases = cur.get("phrases", ["……"])
            actions = cur.get("actions", ["視線を逸らす"])
            beats = cur.get("beats", ["沈黙が流れる"])
            weights = cur.get("weights")

            if not templates:
                return ""

            if weights and len(weights) == len(templates):
                tmpl_str = rnd.choices(templates, weights=weights, k=1)[0]
            else:
                tmpl_str = rnd.choice(templates)

            phrase = rnd.choice(phrases) if phrases else ""
            action = rnd.choice(actions) if actions else ""
            beat = rnd.choice(beats) if beats else ""

            rendered = tmpl_str.format(
                phrase=phrase,
                action=action,
                beat=beat,
                speaker=context.speaker if context else "",
                target=context.target_speaker if context else "",
            )
            return rendered

        # Case 3: Dict with sub-keys (fallback: pick any sublist)
        if isinstance(cur, dict):
            for v in cur.values():
                if isinstance(v, list) and v:
                    return rnd.choice(v)

        return None

    def expand(
        self,
        text: str,
        context: Optional[SubtextContext] = None,
        seed: Optional[int] = None,
        max_depth: int = 3,
    ) -> str:
        """Step 4, 5, 6: Expands control tokens recursively up to max_depth with seed-fixed determinism."""
        if not text:
            return ""

        # Deterministic seed calculation (Step 5)
        if seed is None:
            if context:
                seed = hash(f"{context.scene_id}_{context.turn_index}_{context.speaker}") & 0xFFFFFFFF
            else:
                seed = 42

        rnd = random.Random(seed)
        current_text = text
        seen_states: Set[str] = set()

        for _ in range(max_depth):
            tokens = TokenParser.find_tokens(current_text)
            if not tokens:
                break

            if current_text in seen_states:
                # Cycle detected (Step 6)
                logger.warning(f"Cycle detected during token expansion of: {current_text}")
                break
            seen_states.add(current_text)

            def repl(match: Any) -> str:
                raw_token = match.group(0)
                spec = TokenParser.parse(raw_token)
                if not spec:
                    return raw_token
                val = self._resolve_token_value(spec, rnd, context)
                if val is not None:
                    return val
                # Unresolved token: fallback to subtle pause or strip (Step 19)
                return "……"

            current_text = TOKEN_REGEX.sub(repl, current_text)

        return current_text
