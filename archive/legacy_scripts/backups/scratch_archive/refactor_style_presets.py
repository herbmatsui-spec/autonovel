path = "d:/claude2/config_style_presets.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace AUTHOR_STYLE_PRESETS definition
if "AUTHOR_STYLE_PRESETS = [" in content:
    content = content.replace("AUTHOR_STYLE_PRESETS = [", "_DEFAULT_AUTHOR_STYLE_PRESETS = [")
    print("AUTHOR_STYLE_PRESETS replaced in memory.")

# Add __getattr__
getattr_code = """

from typing import Any
def __getattr__(name: str) -> Any:
    if name == "AUTHOR_STYLE_PRESETS":
        from core.plugin_loader import PluginLoader
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.style_presets:
            return [p.model_dump() for p in plugin.style_presets]
        return _DEFAULT_AUTHOR_STYLE_PRESETS
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
"""

content += getattr_code

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("config_style_presets.py refactored successfully.")

