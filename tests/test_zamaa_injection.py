import asyncio
import logging
from typing import Dict, Any
from prompts.manager import prompt_manager
from src.models.planning_config import PlanningConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_zamaa_prompt_injection():
    logger.info("Starting Step 10: Zamaa Prompt Variable Injection Test...")
    
    # 1. Mock PlanningConfig for Zamaa
    config = PlanningConfig(
        genre="追放ざまぁファンタジー",
        keywords="不当追放, 隠れた才能, 圧倒的報復, 絶望する元仲間",
        style_key="style_web_standard",
        concept="無能と言われ追放された主人公が、実は世界最強の能力者であり、元いたパーティが破滅する中で無双する物語",
        title="追放された俺が実は最強だった件",
        engine_key="zamaa"
    )
    
    # Verify Step 5: tension_threshold correction
    logger.info(f"Testing tension_threshold correction: Expected 80, Got {config.tension_threshold}")
    assert config.tension_threshold == 80, "Tension threshold should be corrected to 80 for zamaa engine"

    # 2. Test build_bible_creation_prompt template switching
    # Pass engine_key in kwargs as implemented in prompts/manager.py
    try:
        prompt = await prompt_manager.build_bible_creation_prompt(
            bible_core_schema=None, # Simplified for test
            world_rules_json="{}",
            concept=config.concept,
            target_eps=config.target_eps,
            engine_key="zamaa"
        )
        
        logger.info("Successfully rendered Zamaa bible prompt.")
        # Check if it's not empty and contains Zamaa-specific elements (if any in the template)
        assert len(prompt) > 0, "Rendered prompt should not be empty"
        logger.info("Prompt length: %d", len(prompt))
        
    except Exception as e:
        logger.error(f"Prompt rendering failed: {e}")
        raise e

    logger.info("Step 10: Zamaa Prompt Variable Injection Test PASSED")

if __name__ == "__main__":
    asyncio.run(test_zamaa_prompt_injection())
