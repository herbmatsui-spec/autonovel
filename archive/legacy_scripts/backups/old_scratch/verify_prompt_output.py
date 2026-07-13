import jinja2

from prompts.manager import PromptManager


def main():
    pm = PromptManager(jinja2.Environment())
    plot_data = {
        "scenes": [{"action": "Scene 1", "impact_score": 80}],
        "detailed_blueprint": "Blueprint content"
    }
    script_text = "Dialogue content"
    target_word_count = 1000

    prompt = pm.build_final_writing_prompt(
        ep_num=1,
        plot_data=plot_data,
        script_text=script_text,
        target_word_count=target_word_count,
        genre_str="dark_fantasy"
    )

    print("--- PROMPT START ---")
    print(prompt)
    print("--- PROMPT END ---")

if __name__ == "__main__":
    main()

