
path = r"i:\claude2\backend\engine_prompts.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

print("Initial 'rd}' count:", content.count("rd}"))
# Let's also search for any other raw '}' or '{' that might cause syntax errors in f-strings.
new_content = content.replace("rd}", "rd}}")
print("After replace 'rd}' count:", new_content.count("rd}"))

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Replacement complete.")

