import pytest
from src.config.cost_optimization import MODEL_PRICING, ROUTING_TIERS
from src.services.llm.prompt_cache_builder import PromptCacheBuilder
from src.services.narrative.scene_tier_evaluator import SceneTierEvaluator
from src.services.observability.token_cost_tracker import TokenCostTracker
from src.llm.model_router import resolve_optimized_model

def test_cost_optimization_config():
    """Test that the cost optimization config is defined."""
    assert "gemini-2.0-flash" in MODEL_PRICING
    assert "claude-3-5-haiku" in MODEL_PRICING
    assert "claude-3-5-sonnet" in MODEL_PRICING
    assert "gpt-4o-mini" in MODEL_PRICING

    assert ROUTING_TIERS["tier1_light"] == "gemini-2.0-flash"
    assert ROUTING_TIERS["tier2_standard"] == "claude-3-5-haiku"
    assert ROUTING_TIERS["tier3_premium"] == "claude-3-5-sonnet"

def test_prompt_cache_builder():
    """Test that the prompt cache builder can be instantiated."""
    builder = PromptCacheBuilder()
    assert builder is not None

def test_scene_tier_evaluator():
    """Test that the scene tier evaluator can be instantiated."""
    evaluator = SceneTierEvaluator()
    assert evaluator is not None

def test_token_cost_tracker():
    """Test that the token cost tracker can be instantiated and calculate cost."""
    tracker = TokenCostTracker()
    cost_info = tracker.calculate_cost(
        model="gemini-2.0-flash",
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=0,
        cache_creation_tokens=0
    )
    assert "jpy" in cost_info
    assert "usd" in cost_info
    assert cost_info["jpy"] >= 0
    assert cost_info["usd"] >= 0

def test_model_router():
    """Test the 3-layer router."""
    # Test tier 1
    assert resolve_optimized_model("planning", False, "free") == ROUTING_TIERS["tier1_light"]
    assert resolve_optimized_model("audit", False, "free") == ROUTING_TIERS["tier1_light"]
    assert resolve_optimized_model("screening", False, "free") == ROUTING_TIERS["tier1_light"]

    # Test tier 2 (default)
    assert resolve_optimized_model("writing", False, "free") == ROUTING_TIERS["tier2_standard"]
    assert resolve_optimized_model("plot_expansion", False, "free") == ROUTING_TIERS["tier2_standard"]

    # Test tier 3 (climax or pro plan)
    assert resolve_optimized_model("writing", True, "free") == ROUTING_TIERS["tier3_premium"]
    assert resolve_optimized_model("writing", False, "pro") == ROUTING_TIERS["tier3_premium"]
    assert resolve_optimized_model("writing", False, "enterprise") == ROUTING_TIERS["tier3_premium"]

    # Test that non-existent purpose falls back to tier 2? Actually, our function uses purpose as task_type.
    # We'll just test that it returns something.
    assert resolve_optimized_model("unknown", False, "free") == ROUTING_TIERS["tier2_standard"]  # Because task_type="unknown" is not in the special cases, so it returns tier2_standard

if __name__ == "__main__":
    pytest.main([__file__])
