
# Create a dummy file to satisfy the import
with open("src/backend/engine_prompts.py", "w", encoding="utf-8") as f:
    f.write("from prompts.manager import PromptManager\n\n")
    f.write("class PromptManager(PromptManager):\n")
    f.write("    pass\n\n")
    f.write("def get_rule_set(rule_type: str) -> str:\n")
    f.write("    return ''\n")

