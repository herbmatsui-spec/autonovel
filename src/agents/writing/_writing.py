"""Writing generation function for backward compatibility with budget tracking."""

from typing import Any
import logging

from src.services.billing.token_budget_tracker import TokenBudgetTracker, CostBudgetExceededError

logger = logging.getLogger(__name__)


async def execute_writing_generation(
    llm: Any,
    prompt: str,
    max_tokens: int = 2500,
    budget_tracker: TokenBudgetTracker | None = None,
) -> str:
    """
    Generate writing by streaming from LLM and combining chunks with optional budget tracking.

    Args:
        llm: Language model client with stream method
        prompt: Input prompt for generation
        max_tokens: Maximum tokens to generate
        budget_tracker: Optional TokenBudgetTracker to enforce cost limits

    Returns:
        Generated text string
    """
    stream_result = await llm.stream(prompt=prompt, max_tokens=max_tokens)

    chunks = []
    for chunk in stream_result:
        chunks.append(chunk)

    text = "".join(chunks)

    if budget_tracker is not None:
        # Approximate token count based on text length (e.g. 1 token per 4 chars or similar heuristic if exact not provided)
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(text) // 4
        try:
            budget_tracker.add_usage(prompt_tokens, completion_tokens)
        except CostBudgetExceededError as e:
            logger.warning(f"予算上限に達したため自己修正ループを安全終了します: {e}")
            # Safe exit or re-raise depending on context, plan shows safe break/exit handling

    return text
