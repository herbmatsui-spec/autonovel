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
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import logging
import re
from collections.abc import Iterable
from typing import Any, Literal

logger = logging.getLogger(__name__)

ScrubMode = Literal["scrub", "hash", "deterministic_hash"]

BLOCKED_TOKEN_FMT = "<BLOCKED:{source}>"
HASH_TOKEN_FMT = "<HASH:{digest}>"


def _json_default(obj: Any) -> Any:
    """JSON serialization fallback for non-standard types."""
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    if hasattr(obj, "model_dump"):  # Pydantic models
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def _canonical_json(value: Any) -> str:
    """Deterministic JSON serialization for stable hashing.

    - sort_keys=True: consistent key ordering
    - separators=(",", ":"): no whitespace
    - allow_nan=False: reject NaN/Inf (strict JSON)
    - ensure_ascii=False: preserve Unicode
    - _json_default: handle sets, Pydantic, custom objects
    """
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
        default=_json_default,
    )


def _hash_token(value: Any, deterministic: bool = False) -> str:
    """Stable 8-char SHA-256 digest for deterministic replacement.

    Args:
        value: Value to hash.
        deterministic: If True, use canonical JSON (sort_keys, no whitespace).
                       If False, use repr() for backward compatibility.
    """
    h = hashlib.sha256()
    if deterministic:
        h.update(_canonical_json(value).encode("utf-8"))
    else:
        h.update(repr(value).encode("utf-8"))
    return h.hexdigest()[:8]


@dataclass
class PurifiedFeedback:
    """Represents text feedback purified of cross-proposal leaks (Step 1)."""
    original_critique: str
    purified_text: str
    removed_entities: list[str] = field(default_factory=list)
    is_purified: bool = True


PROPOSAL_LEAK_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?:[案プラン]|proposal|plan)\s*([A-Za-z0-9１-９一二三])(?:の|では|における|について|という|案)?", re.IGNORECASE),
    re.compile(r"([A-Za-z0-9１-９一二三])案(?:の|では|における|について|という)?", re.IGNORECASE),
    re.compile(r"(?:他案|別の案|対抗案|候補[0-9１-９一二三A-Za-z])(?:の|では|における)?", re.IGNORECASE),
]

BLIND_PURIFIER_SYSTEM_PROMPT = """あなたは小説企画のブラインドピアレビュー純化エンジンです。
レビュー文から特定の他案（A案、B案、C案など）に関する直接的な言及や比較、特定の他案のプロット展開・固有名詞を完全に除去し、
ターゲット企画に対する純粋で客観的な創作・作劇アドバイス（例：「冒頭の葛藤の提示をもっと早めるべき」「主人公の動機を明確にすべき」など）のみに純化して出力してください。
特定の案名（A案、B案など）は一切含めず、中立的なアドバイス文のみを返してください。"""


def detect_proposal_leaks(text: str) -> list[str]:
    """Detect references to other proposal variants or leaked entity patterns (Step 2)."""
    if not isinstance(text, str):
        return []
    leaks = []
    for pattern in PROPOSAL_LEAK_PATTERNS:
        for match in pattern.finditer(text):
            leaks.append(match.group(0))
    return leaks


class BlindFeedbackPurifier:
    """Purifies critique text by removing cross-proposal leaks and generalizing specific advice (Step 4)."""

    def __init__(self, llm_adapter: Any = None) -> None:
        self.llm_adapter = llm_adapter

    def purify_critique(
        self,
        critique: str,
        forbidden_terms: Iterable[str] | None = None,
    ) -> PurifiedFeedback:
        """Synchronously or rule-based purify critique text."""
        if not critique or not str(critique).strip():
            return PurifiedFeedback(original_critique="", purified_text="", is_purified=False)

        leaks = detect_proposal_leaks(critique)
        if forbidden_terms:
            for term in forbidden_terms:
                if term and term in critique and term not in leaks:
                    leaks.append(term)

        purified = critique
        # ルールベース純化: 案参照や比較句を汎用表現に置換
        for pattern in PROPOSAL_LEAK_PATTERNS:
            purified = pattern.sub("本作", purified)

        if forbidden_terms:
            for term in forbidden_terms:
                if term:
                    purified = purified.replace(term, "設定")

        # 連続した冗長表現の整形
        purified = re.sub(r"本作の本作の", "本作の", purified)
        purified = re.sub(r"本作と比べて", "", purified)

        return PurifiedFeedback(
            original_critique=critique,
            purified_text=purified.strip(),
            removed_entities=leaks,
            is_purified=bool(leaks),
        )

    async def purify_critique_async(
        self,
        critique: str,
        forbidden_terms: Iterable[str] | None = None,
    ) -> PurifiedFeedback:
        """Purify critique text using LLM if available, falling back to rule-based."""
        if not critique or not str(critique).strip():
            return PurifiedFeedback(original_critique="", purified_text="", is_purified=False)

        leaks = detect_proposal_leaks(critique)
        if not self.llm_adapter:
            return self.purify_critique(critique, forbidden_terms)

        try:
            prompt = (
                f"{BLIND_PURIFIER_SYSTEM_PROMPT}\n\n"
                f"【元のレビュー】\n{critique}\n\n"
                f"【純化後レビュー】"
            )
            res = await self.llm_adapter.generate(prompt, max_tokens=500)
            cleaned_text = res.strip() if isinstance(res, str) else str(res).strip()
            return PurifiedFeedback(
                original_critique=critique,
                purified_text=cleaned_text,
                removed_entities=leaks,
                is_purified=True,
            )
        except Exception as e:
            logger.warning(f"LLM purification failed, falling back to rule-based: {e}")
            return self.purify_critique(critique, forbidden_terms)


@dataclass
class IsolationViolation:
    """Represents a single isolation violation detected during verification."""
    path: str
    violation_type: str  # "marker_leak" | "unscrubbed_key" | "cross_round_contamination"
    detail: str


@dataclass
class VerificationResult:
    """Result of verify_isolation() check."""
    passed: bool
    violations: list[IsolationViolation]
    checked_at: datetime = field(default_factory=datetime.now)

    def __bool__(self) -> bool:
        return self.passed


@dataclass
class IsolationSchema:
    """Explicit isolation rules for blind review feedback.

    Replaces the legacy substring-matching logic with explicit,
    declarative rules that can be audited and tested.
    """

    # Exact key matches (case-insensitive)
    exact_keys: set[str] = field(default_factory=set)
    # Prefix rules: keys starting with any of these are blocked
    prefix_rules: list[str] = field(default_factory=list)
    # Suffix rules: keys ending with any of these are blocked
    suffix_rules: list[str] = field(default_factory=list)
    # Nested path rules: "parent.child.forbidden" blocks that path
    nested_paths: list[str] = field(default_factory=list)
    # Regex patterns for complex matching
    regex_patterns: list[re.Pattern] = field(default_factory=list)
    # Strict blind routing: enforce no cross-proposal leak or unscrubbed feedback
    strict_blind_routing: bool = False

    @classmethod
    def from_legacy(cls, forbidden_agents: list[str], blocked_keys: set[str]) -> IsolationSchema:
        """Create schema from legacy BlindReviewGate configuration.

        Args:
            forbidden_agents: List of forbidden agent names (lowercase).
            blocked_keys: Set of explicitly blocked key names (lowercase).

        Returns:
            IsolationSchema with prefix/suffix rules derived from agents.
        """
        schema = cls()
        schema.exact_keys = {k.lower() for k in blocked_keys}
        for agent in forbidden_agents:
            if agent:
                # Add agent name as exact key match (legacy: substring match included exact)
                schema.exact_keys.add(agent)
                schema.prefix_rules.append(f"{agent}_")
                schema.suffix_rules.append(f"_{agent}")
        return schema

    def is_blocked(self, key: str, path: str = "") -> bool:
        """Check if a key at the given path should be blocked.

        Args:
            key: The dictionary key to check.
            path: Dot-separated path to parent (e.g., "outer.inner").

        Returns:
            True if the key matches any blocking rule.
        """
        key_l = key.lower()
        full_path = f"{path}.{key_l}" if path else key_l

        # 1. Exact key match
        if key_l in self.exact_keys or full_path in self.exact_keys:
            return True

        # 2. Prefix match
        if any(key_l.startswith(p) for p in self.prefix_rules):
            return True

        # 3. Suffix match
        if any(key_l.endswith(s) for s in self.suffix_rules):
            return True

        # 4. Nested path match
        if any(full_path == p or full_path.startswith(p + ".") for p in self.nested_paths):
            return True

        # 5. Regex match
        return any(p.search(key_l) for p in self.regex_patterns)

    def add_exact_key(self, key: str) -> IsolationSchema:
        """Add an exact key to block (fluent API)."""
        self.exact_keys.add(key.lower())
        return self

    def add_prefix(self, prefix: str) -> IsolationSchema:
        """Add a prefix rule (fluent API)."""
        self.prefix_rules.append(prefix.lower())
        return self

    def add_suffix(self, suffix: str) -> IsolationSchema:
        """Add a suffix rule (fluent API)."""
        self.suffix_rules.append(suffix.lower())
        return self

    def add_nested_path(self, path: str) -> IsolationSchema:
        """Add a nested path rule (fluent API)."""
        self.nested_paths.append(path.lower())
        return self

    def add_regex(self, pattern: str) -> IsolationSchema:
        """Add a regex pattern (fluent API)."""
        self.regex_patterns.append(re.compile(pattern, re.IGNORECASE))
        return self


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
        here" without learning its contents. ``"deterministic_hash"`` uses
        canonical JSON serialization for fully deterministic hashing
        (key order independent, set order independent).
    blocked_keys:
        Optional explicit list of payload keys that map to forbidden outputs
        (e.g. ``["planning_output_a", "planning_output_b"]`` for the
        3-proposal gacha case). If empty, every key whose name contains
        one of the forbidden agent names (case-insensitive) is treated as
        blocked.
    deterministic:
        If True, use canonical JSON serialization for hash mode (sort_keys,
        no whitespace, sets sorted). This ensures identical hashes for
        semantically equivalent data regardless of key/set iteration order.
        Can also be enabled via mode="deterministic_hash".
    schema:
        Optional explicit IsolationSchema. If not provided, one is created
        from forbidden_agents and blocked_keys using legacy-compatible rules.
    """

    def __init__(
        self,
        forbidden_agents: Iterable[str],
        mode: ScrubMode = "scrub",
        blocked_keys: Iterable[str] | None = None,
        deterministic: bool = False,
        schema: IsolationSchema | None = None,
        current_round_id: str | None = None,
        purify_text: bool = False,
        purifier: BlindFeedbackPurifier | None = None,
    ) -> None:
        self.forbidden_agents: list[str] = [str(a).lower() for a in forbidden_agents]
        if not self.forbidden_agents:
            raise ValueError("forbidden_agents must be non-empty")
        if mode not in ("scrub", "hash", "deterministic_hash"):
            raise ValueError(f"Invalid mode: {mode}")
        self.mode: ScrubMode = mode
        # deterministic_hash モード指定時、または明示的 deterministic=True で有効化
        self.deterministic: bool = deterministic or (mode == "deterministic_hash")
        self.blocked_keys: set[str] = {k.lower() for k in (blocked_keys or [])}
        # Build or use provided isolation schema
        self.schema: IsolationSchema = schema or IsolationSchema.from_legacy(
            self.forbidden_agents, self.blocked_keys
        )
        # Current round ID for cross-round contamination detection
        self.current_round_id: str | None = current_round_id
        self._blocked_count: int = 0
        self.purify_text: bool = purify_text
        self.purifier: BlindFeedbackPurifier | None = purifier or (BlindFeedbackPurifier() if purify_text else None)

    @property
    def blocked_count(self) -> int:
        """Total keys scrubbed/hashed since construction (for metrics)."""
        return self._blocked_count

    @property
    def config_hash(self) -> str:
        """Deterministic hash of gate configuration for audit/reproducibility."""
        import hashlib
        import json
        config = {
            "forbidden_agents": sorted(self.forbidden_agents),
            "mode": self.mode,
            "blocked_keys": sorted(self.blocked_keys),
            "deterministic": self.deterministic,
        }
        h = hashlib.sha256()
        h.update(json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        return h.hexdigest()[:16]

    def is_blocked(self, source_agent: str, target_agent: str) -> bool:
        """Return True if ``source_agent`` outputs are forbidden for
        ``target_agent``. With the default gate construction, any source in
        ``forbidden_agents`` is blocked for every target.
        """
        return str(source_agent).lower() in self.forbidden_agents

    def _key_is_blocked(self, key: str, path: str = "") -> str | None:
        """Return the offending source-agent name if ``key`` matches a
        forbidden agent; otherwise ``None``.

        Uses IsolationSchema for precise matching with path context.
        """
        if self.schema.is_blocked(key, path):
            # Find which agent matched for reporting
            key_l = key.lower()
            full_path = f"{path}.{key_l}" if path else key_l
            # Check exact keys first
            if key_l in self.schema.exact_keys or full_path in self.schema.exact_keys:
                return self.forbidden_agents[0] if self.forbidden_agents else "unknown"
            # Check prefix/suffix for agent match
            for agent in self.forbidden_agents:
                if agent and (key_l.startswith(f"{agent}_") or key_l.endswith(f"_{agent}")):
                    return agent
            return self.forbidden_agents[0] if self.forbidden_agents else "unknown"
        return None

    def scrub_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """Recursively scrub/hashed ``payload`` and return a new dict.

        Non-dict values pass through untouched. Dicts are deep-copied so the
        caller's structure is never mutated.
        """
        if payload is None:
            return {}
        scrubbed = self._deep_scrub(copy.deepcopy(payload))
        if self.schema.strict_blind_routing:
            v_res = self.verify_isolation(scrubbed)
            if not v_res.passed:
                raise ValueError(
                    f"Strict blind routing failed with {len(v_res.violations)} violations: "
                    f"{[v.detail for v in v_res.violations]}"
                )
        return scrubbed

    def _deep_scrub(self, obj: Any, path: str = "") -> Any:
        if isinstance(obj, dict):
            out: dict[str, Any] = {}
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k

                # Cross-round contamination detection:
                # If a value is a scrub marker from a DIFFERENT round, treat as contamination
                if isinstance(v, str) and v.startswith(("<BLOCKED:", "<HASH:")):
                    # Check if this marker is in _blind_meta (allowed) or elsewhere
                    # Allow markers anywhere under _blind_meta path
                    if new_path == "_blind_meta" or new_path.startswith("_blind_meta."):
                        # Metadata is preserved as-is
                        out[k] = v
                        continue
                    # If we have a current_round_id, check if marker contains round info
                    # For now, any marker outside _blind_meta that we didn't just create
                    # is treated as potential cross-round contamination
                    if self.current_round_id is not None:
                        logger.warning(
                            f"Cross-round contamination detected at {new_path}: "
                            f"marker from previous round found, re-scrubbing"
                        )
                        # Re-scrub with current round's marker
                        if self.mode == "scrub":
                            out[k] = BLOCKED_TOKEN_FMT.format(source="cross_round_contamination")
                        else:
                            out[k] = HASH_TOKEN_FMT.format(
                                digest=_hash_token(v, deterministic=self.deterministic)
                            )
                        self._blocked_count += 1
                        continue

                source = self._key_is_blocked(str(k), path)
                if source is not None:
                    if self.mode == "scrub":
                        out[k] = BLOCKED_TOKEN_FMT.format(source=source)
                    else:
                        out[k] = HASH_TOKEN_FMT.format(
                            digest=_hash_token(v, deterministic=self.deterministic)
                        )
                    self._blocked_count += 1
                    continue
                out[k] = self._deep_scrub(v, new_path)
            return out
        if isinstance(obj, list):
            return [self._deep_scrub(item, f"{path}[{i}]") for i, item in enumerate(obj)]
        if isinstance(obj, str) and self.purify_text and self.purifier:
            purified_res = self.purifier.purify_critique(obj)
            return purified_res.purified_text
        if isinstance(obj, tuple):
            return tuple(self._deep_scrub(x, f"{path}[{i}]") for i, x in enumerate(obj))
        return obj

    def verify_isolation(self, payload: dict[str, Any]) -> VerificationResult:
        """Verify that a scrubbed payload contains no isolation violations.

        Checks for:
        1. Scrub markers (<BLOCKED:...>, <HASH:...>) leaked into non-blocked fields
        2. Blocked keys that were not properly scrubbed (missing markers)
        3. Cross-round contamination markers (handled separately in _deep_scrub)

        Args:
            payload: The scrubbed payload to verify.

        Returns:
            VerificationResult with passed=True if no violations found.
        """
        violations: list[IsolationViolation] = []

        def check(obj: Any, current_path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_path = f"{current_path}.{k}" if current_path else k
                    is_blocked = self.schema.is_blocked(k, current_path)

                    # Check for leaked scrub markers in NON-blocked fields
                    if isinstance(v, str) and v.startswith(("<BLOCKED:", "<HASH:")):
                        # Allow markers in _blind_meta (cross-round metadata)
                        if not current_path.endswith("_blind_meta") and not is_blocked:
                            violations.append(IsolationViolation(
                                path=new_path,
                                violation_type="marker_leak",
                                detail=f"Scrub marker leaked in public field: {v[:50]}",
                            ))

                    # Check for unscrubbed blocked keys (blocked key should have marker)
                    if is_blocked and not (isinstance(v, str) and v.startswith(("<BLOCKED:", "<HASH:"))):
                        violations.append(IsolationViolation(
                            path=new_path,
                            violation_type="unscrubbed_key",
                            detail=f"Blocked key not scrubbed: {k}",
                        ))

                    check(v, new_path)
            elif isinstance(obj, (list, tuple)):
                for i, v in enumerate(obj):
                    check(v, f"{current_path}[{i}]")

        check(payload)
        return VerificationResult(
            passed=len(violations) == 0,
            violations=violations,
        )


def verify_no_cross_proposal_contamination(
    proposals: dict[str, Any] | list[dict[str, Any]]
) -> VerificationResult:
    """Verify that candidate proposals have no mutual context leaks or cross-contamination (Step 10).

    Args:
        proposals: Either a mapping of proposal keys to proposal dicts (e.g. {'proposal_a': {...}}),
                   or a list of proposal dicts.

    Returns:
        VerificationResult containing any detected leaks or contamination violations.
    """
    violations: list[IsolationViolation] = []

    # 1. Normalize proposals into {label: dict}
    norm_proposals: dict[str, dict[str, Any]] = {}
    if isinstance(proposals, list):
        for idx, item in enumerate(proposals):
            label = f"proposal_{chr(ord('a') + idx) if idx < 26 else idx}"
            if isinstance(item, dict):
                norm_proposals[label] = item
    elif isinstance(proposals, dict):
        for k, v in proposals.items():
            if isinstance(v, dict):
                norm_proposals[str(k)] = v

    # 2. Extract distinctive entities / titles from each proposal
    proposal_entities: dict[str, set[str]] = {}
    for label, p_dict in norm_proposals.items():
        entities: set[str] = set()
        # Direct identifiers
        entities.add(label.lower())
        short_id = label.split("_")[-1].lower()
        if len(short_id) == 1:
            entities.add(f"{short_id}案")

        # Titles and names (if explicit)
        for key in ("title", "theme", "project_name", "codename"):
            val = p_dict.get(key)
            if isinstance(val, str) and len(val.strip()) >= 2:
                entities.add(val.strip())
        proposal_entities[label] = entities

    # 3. Helper to recursively extract all text from a proposal
    def extract_texts(data: Any, path: str) -> list[tuple[str, str]]:
        texts = []
        if isinstance(data, str):
            texts.append((path, data))
        elif isinstance(data, dict):
            for k, v in data.items():
                texts.extend(extract_texts(v, f"{path}.{k}" if path else str(k)))
        elif isinstance(data, (list, tuple)):
            for i, v in enumerate(data):
                texts.extend(extract_texts(v, f"{path}[{i}]"))
        return texts

    # 4. Check for leaks in each proposal
    for label, p_dict in norm_proposals.items():
        texts = extract_texts(p_dict, label)

        for text_path, text_val in texts:
            # Check 4.1: Explicit leak phrases (e.g., "A案では", "他案")
            leaks = detect_proposal_leaks(text_val)
            for leak in leaks:
                violations.append(IsolationViolation(
                    path=text_path,
                    violation_type="cross_proposal_leak_pattern",
                    detail=f"Detected leak phrase '{leak}' in {label}",
                ))

            # Check 4.2: Entities from OTHER proposals
            for other_label, other_ents in proposal_entities.items():
                if other_label == label:
                    continue
                for ent in other_ents:
                    # Ignore very generic or short words
                    if len(ent) < 2:
                        continue
                    if ent in text_val:
                        violations.append(IsolationViolation(
                            path=text_path,
                            violation_type="cross_proposal_contamination",
                            detail=f"Detected entity '{ent}' from {other_label} leaked into {label}",
                        ))

    return VerificationResult(
        passed=len(violations) == 0,
        violations=violations,
    )


__all__ = [
    "BLOCKED_TOKEN_FMT",
    "HASH_TOKEN_FMT",
    "BLIND_PURIFIER_SYSTEM_PROMPT",
    "PROPOSAL_LEAK_PATTERNS",
    "PurifiedFeedback",
    "detect_proposal_leaks",
    "BlindFeedbackPurifier",
    "BlindReviewGate",
    "IsolationSchema",
    "IsolationViolation",
    "ScrubMode",
    "VerificationResult",
    "verify_no_cross_proposal_contamination",
]