import os
import shutil

# カテゴリ定義
CATEGORIES = {
    "audit": ["audit", "analyze"],
    "persona": ["persona"],
    "polish": ["polish", "refinement"],
    "narrative": ["narrative", "plot", "creation", "bible", "script", "writing", "arc"],
}

source_dir = "prompts"
target_base = "prompts/templates"

# 対象ファイルリスト
files = [f for f in os.listdir(source_dir) if f.endswith(".j2")]

for file in files:
    # 移動先カテゴリの決定
    category = "utility"
    for cat, keywords in CATEGORIES.items():
        if any(k in file for k in keywords):
            category = cat
            break

    source_path = os.path.join(source_dir, file)
    dest_path = os.path.join(target_base, category, file)

    print(f"Moving {file} to {dest_path}")
    shutil.move(source_path, dest_path)

