path = "d:/claude2/engine_prompts.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("\r\n", "\n")

old_block = """        # 視点・トーン
        phase = plot_data.get("current_chain_phase", "Hate")
        tone_inst = f"【フェーズトーン: {phase}】\\n"
        try:
            from core.plugin_loader import PluginLoader
            loader = PluginLoader()
            emotion_curve = loader.get_emotion_curve()
            phase_inst = next((item["instruction"] for item in emotion_curve if item["phase"] == phase), None)
            if phase_inst:
                tone_inst += f"{phase_inst}\\n"
            else:
                if phase == "Hate": tone_inst += "読者の『ざまぁ』欲求を最大化せよ。敵の傲慢さと不当な辱めを執拗に描写せよ。\\n"
                elif phase == "Payoff": tone_inst += "周囲の『絶望・後悔・畏怖』の反応描写に文字数の7割を割け。\\n"
        except Exception as e:
            print(f"Error loading tone from plugin: {e}")
            if phase == "Hate": tone_inst += "読者の『ざまぁ』欲求を最大化せよ。敵の傲慢さと不当な辱めを執拗に描写せよ。\\n"
            elif phase == "Payoff": tone_inst += "周囲の『絶望・後悔・畏怖』の反応描写に文字数の7割を割け。\\n\""""

# We should do standard string matching, but let's use exact substrings for robust find & replace.
old_target = """            phase_inst = next((item["instruction"] for item in emotion_curve if item["phase"] == phase), None)"""

new_replacement = """            phase_inst = None
            for item in emotion_curve:
                p = item.phase if hasattr(item, "phase") else item.get("phase")
                if p == phase:
                    phase_inst = item.instruction if hasattr(item, "instruction") else item.get("instruction")
                    break"""

if old_target in content:
    content = content.replace(old_target, new_replacement)
    print("Successfully replaced emotion curve lookup in engine_prompts.py")
else:
    print("Target text NOT found in engine_prompts.py")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("engine_prompts.py refactoring completed.")

