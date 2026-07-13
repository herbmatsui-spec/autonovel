import os
import re

config_dir = "config"
init_path = os.path.join(config_dir, "__init__.py")

def get_defined_constants(file_path):
    constants = set()
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Find lines like CONSTANT = ... or CONSTANT: type = ...
        matches = re.findall(r'^([A-Z][A-Z0-9_]+)\s*(?::.*?)?\s*=', content, re.MULTILINE)
        for m in matches:
            constants.add(m)
    return constants

def get_exported_constants(file_path):
    exports = set()
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Find items inside from .module import ( ... )
        matches = re.findall(r'from\s+\.\w+\s+import\s*\((.*?)\)', content, re.DOTALL)
        for m in matches:
            items = re.findall(r'([A-Z][A-Z0-9_]+)', m)
            for item in items:
                exports.add(item)
    return exports

submodules = ["base.py", "narrative.py", "styles.py", "archetypes.py"]
all_defined = {}
for sub in submodules:
    path = os.path.join(config_dir, sub)
    if os.path.exists(path):
        all_defined[sub] = get_defined_constants(path)

exported = get_exported_constants(init_path)

print("--- Missing Exports in config/__init__.py ---")
for sub, constants in all_defined.items():
    missing = constants - exported
    if missing:
        print(f"[{sub}]: {', '.join(sorted(missing))}")

