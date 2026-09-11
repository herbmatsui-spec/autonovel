from __future__ import annotations

from copy import deepcopy


DEFAULT_FALLBACK_CHAINS: dict[str, list[str]] = {
    "claude": ["openai", "gemini", "mock"],
    "openai": ["gemini", "claude", "mock"],
    "gemini": ["openai", "claude", "mock"],
    "ollama": ["mock"],
    "vllm": ["ollama", "mock"],
    "mock": [],
}


class FallbackPolicy:
    def __init__(
        self,
        fallback_chains: dict[str, list[str]] | None = None,
    ) -> None:
        self.fallback_chains = deepcopy(
            fallback_chains or DEFAULT_FALLBACK_CHAINS
        )

    def get_fallback_sequence(self, primary_provider: str) -> list[str]:
        provider = primary_provider.strip().lower()
        seen = {provider}
        sequence: list[str] = []
        pending = list(self.fallback_chains.get(provider, []))
        while pending:
            candidate = pending.pop(0).strip().lower()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            sequence.append(candidate)
            pending.extend(self.fallback_chains.get(candidate, []))
        return sequence

    def get_next_provider(self, primary_provider: str) -> str | None:
        sequence = self.get_fallback_sequence(primary_provider)
        return sequence[0] if sequence else None
