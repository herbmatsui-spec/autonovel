from src.services.illustration.prompt_generator import IllustrationPromptGenerator

def test_generate_prompt_from_scene():
    gen = IllustrationPromptGenerator()
    prompt = gen.build_prompt(
        character_desc="銀髪の少女、青いドレス",
        mood="緊迫した夜の森",
        style="anime"
    )
    assert "silver hair" in prompt.lower() or "anime" in prompt.lower()
