"""Blind Peer Review Gate.

Phase 2 / Guideline #1: Implements blind peer review feedback isolation.
When a feedback payload is being routed to a target agent, any keys whose
names map to "forbidden" agents (e.g. another proposal variant, another
agent's raw output) are either scrubbed (replaced with a deterministic
marker) or hashed (deterministic 8-char digest) depending on `mode`.

This module is LLM-free and pure-Python so it can be unit-tested
deterministically.
"""

from __future__ import annotations

import copy
import hashlib
import logging
from typing import Any, Iterable, Literal

logger = logging.getLogger(__name__)

ScrubMode = Literal["scrub", "hash"]

BLOCKED_TOKEN_FMT = "<BLOCKED:{source}>"
HASH_TOKEN_FMT = "<HASH:{digest}>"


def _hash_token(value: Any) -> str:
    """Stable 8-char SHA-256 digest for deterministic replacement."""
    h = hashlib.sha256()
    h.update(repr(value).encode("utf-8"))
    return h.hexdigest()[:8]


class BlindReviewGate:
    """Filter feedback payloads so that target agents cannot see forbidden
    agents' outputs.

    Parameters
    ----------
    forbidden_agents:
        List of agent names whose outputs MUST be hidden from the target
        when feedback is delivered.
    mode:
        ``"scrub"`` (default) replaces blocked values with a marker
        ``<BLOCKED:{source}>``. ``"hash"`` replaces them with a deterministic
        8-char digest so the test agent can still tell that "something was
        here" without learning its contents.
    blocked_keys:
        Optional explicit list of payload keys that map to forbidden outputs
        (e.g. ``["planning_output_a", "planning_output_b"]`` for the
        3-proposal gacha case). If empty, every key whose name contains
        one of the forbidden agent names (case-insensitive) is treated as
        blocked.
    """

    def __init__(
        self,
        forbidden_agents: Iterable[str],
        mode: ScrubMode = "scrub",
        blocked_keys: Iterable[str] | None = None,
    ) -> None:
        self.forbidden_agents: list[str] = [str(a).lower() for a in forbidden_agents]
        if not self.forbidden_agents:
            raise ValueError("forbidden_agents must be non-empty")
        if mode not in ("scrub", "hash"):
            raise ValueError(f"Invalid mode: {mode}")
        self.mode: ScrubMode = mode
        self.blocked_keys: set[str] = {k.lower() for k in (blocked_keys or [])}
        self._blocked_count: int = 0

    @property
    def blocked_count(self) -> int:
        """Total keys scrubbed/hashed since construction (for metrics)."""
        return self._blocked_count

    def is_blocked(self, source_agent: str, target_agent: str) -> bool:
        """Return True if ``source_agent`` outputs are forbidden for
        ``target_agent``. With the default gate construction, any source in
        ``forbidden_agents`` is blocked for every target.
        """
        return str(source_agent).lower() in self.forbidden_agents

    def _key_is_blocked(self, key: str) -> str | None:
        """Return the offending source-agent name if ``key`` matches a
        forbidden agent; otherwise ``None``.
        """
        key_l = key.lower()
        if key_l in self.blocked_keys:
            # When the key is explicitly listed we don't know which agent
            # produced it; report the first as a generic tag.
            return self.forbidden_agents[0]
        for agent in self.forbidden_agents:
            if agent and agent in key_l:
                return agent
        return None

    def scrub_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """Recursively scrub/hashed ``payload`` and return a new dict.

        Non-dict values pass through untouched. Dicts are deep-copied so the
        caller's structure is never mutated.
        """
        if payload is None:
            return {}
        return self._deep_scrub(copy.deepcopy(payload))

    def _deep_scrub(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            out: dict[str, Any] = {}
            for k, v in obj.items():
                source = self._key_is_blocked(str(k))
                if source is not None:
                    if self.mode == "scrub":
                        out[k] = BLOCKED_TOKEN_FMT.format(source=source)
                    else:
                        out[k] = HASH_TOKEN_FMT.format(digest=_hash_token(v))
                    self._blocked_count += 1
                    continue
                out[k] = self._deep_scrub(v)
            return out
        if isinstance(obj, list):
            return [self._deep_scrub(x) for x in obj]
        if isinstance(obj, tuple):
            return tuple(self._deep_scrub(x) for x in obj)
        return obj


__all__ = ["BlindReviewGate", "ScrubMode", "BLOCKED_TOKEN_FMT", "HASH_TOKEN_FMT"]