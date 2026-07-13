
legacy_path = r"i:\claude2\engine_prompts.py"
target_path = r"i:\claude2\backend\engine_prompts.py"

with open(legacy_path, "r", encoding="utf-8") as f:
    code = f.read()

# Replace Streamlit cache with functools lru_cache
code = code.replace("import streamlit as st", "")
code = code.replace("@st.cache_resource", "@functools.lru_cache(maxsize=None)")

# Ensure import functools is present
if "import functools" not in code:
    code = "import functools\n" + code

with open(target_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Restored clean base backend/engine_prompts.py")

