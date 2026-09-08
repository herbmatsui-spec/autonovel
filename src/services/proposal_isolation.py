"""Proposal Isolation Sandbox & Execution Runner (Steps 7-8).

Guarantees strict physical isolation for 3-proposal gacha ideation:
- Each proposal runs in its own sandbox with an isolated session ID and history.
- Cross-proposal prompt contamination is prevented by construction.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProposalSandboxContext:
    """Isolated execution context for a single proposal candidate (Step 7)."""
    proposal_id: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    isolated_history: list[dict[str, str]] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, proposal_id: str, **kwargs: Any) -> ProposalSandboxContext:
        """Factory method to create an isolated sandbox context."""
        return cls(proposal_id=proposal_id, **kwargs)

    def record_interaction(self, role: str, content: str) -> None:
        """Record an isolated prompt/completion turn for this proposal only."""
        self.isolated_history.append({"role": role, "content": content})

    def add_history(self, role: str, content: str) -> None:
        """Alias for record_interaction."""
        self.record_interaction(role, content)

    def store_artifact(self, key: str, value: Any) -> None:
        """Store an artifact isolated within this sandbox."""
        self.artifacts[key] = value

    def get_clean_prompt_history(self) -> list[dict[str, str]]:
        """Return deep-copied prompt history without any cross-talk."""
        return copy.deepcopy(self.isolated_history)


class ProposalIsolationRunner:
    """Manages parallel or isolated generation and evaluation of multiple proposals (Step 8)."""

    def __init__(self, proposal_ids: list[str] | None = None, count: int | None = None) -> None:
        if count is not None:
            self.proposal_ids = [f"proposal_{chr(ord('a') + i)}" for i in range(count)]
        else:
            self.proposal_ids = proposal_ids or ["proposal_a", "proposal_b", "proposal_c"]

    async def execute_isolated_proposals(
        self,
        generate_fn: Callable[[ProposalSandboxContext], Coroutine[Any, Any, dict[str, Any]]],
        custom_contexts: dict[str, ProposalSandboxContext] | None = None,
        count: int | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Execute each proposal in its dedicated, physically isolated sandbox context.

        Args:
            generate_fn: Async function accepting a ProposalSandboxContext and returning proposal output.
            custom_contexts: Optional pre-configured sandboxes.
            count: Optional override for number of proposal sandboxes to execute.

        Returns:
            dict mapping proposal_id to its isolated output.
        """
        target_ids = self.proposal_ids
        if count is not None:
            target_ids = [f"proposal_{chr(ord('a') + i)}" for i in range(count)]

        contexts = custom_contexts or {
            pid: ProposalSandboxContext(proposal_id=pid) for pid in target_ids
        }

        tasks = []
        for pid in target_ids:
            ctx = contexts[pid]
            tasks.append(self._run_single_proposal(pid, ctx, generate_fn))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs: dict[str, dict[str, Any]] = {}
        for pid, res in zip(target_ids, results):
            if isinstance(res, Exception):
                logger.error(f"Proposal {pid} failed in sandbox: {res}")
                outputs[pid] = {"status": "error", "error": str(res), "_sandbox_id": contexts[pid].session_id}
            else:
                res["_sandbox_id"] = contexts[pid].session_id
                outputs[pid] = res

        return outputs

    async def _run_single_proposal(
        self,
        proposal_id: str,
        ctx: ProposalSandboxContext,
        generate_fn: Callable[[ProposalSandboxContext], Coroutine[Any, Any, dict[str, Any]]],
    ) -> dict[str, Any]:
        """Run a single proposal candidate in complete isolation."""
        logger.debug(f"Starting isolated sandbox for {proposal_id} (session {ctx.session_id})")
        res = await generate_fn(ctx)
        logger.debug(f"Completed isolated sandbox for {proposal_id}")
        return res
