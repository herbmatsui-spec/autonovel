
# 1. Refactor config/base.py
base_path = "d:/claude2/config/base.py"
with open(base_path, "r", encoding="utf-8") as f:
    content = f.read()

old_props = """    @property
    def tropes(self) -> List[str]:
        return self._config_data.get("tropes", [])

    @property
    def title_patterns(self) -> List[str]:
        return self._config_data.get("title_patterns", [])

    @property
    def forbidden_words_replacements(self) -> Dict[str, str]:
        return self._config_data.get("forbidden_words_replacements", {})"""

# normalize line endings to LF
content = content.replace("\r\n", "\n")
old_props = old_props.replace("\r\n", "\n")

new_props = """    @property
    def tropes(self) -> List[str]:
        from core.plugin_loader import PluginLoader
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.tropes is not None:
            return plugin.tropes
        return self._config_data.get("tropes", [])

    @property
    def title_patterns(self) -> List[str]:
        from core.plugin_loader import PluginLoader
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.title_patterns is not None:
            return plugin.title_patterns
        return self._config_data.get("title_patterns", [])

    @property
    def forbidden_words_replacements(self) -> Dict[str, str]:
        from core.plugin_loader import PluginLoader
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.forbidden_words_replacements is not None:
            return plugin.forbidden_words_replacements
        return self._config_data.get("forbidden_words_replacements", {})"""

new_props = new_props.replace("\r\n", "\n")

if old_props in content:
    content = content.replace(old_props, new_props)
    with open(base_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("config/base.py refactored successfully.")
else:
    print("config/base.py target not found.")


# 2. Refactor config/narrative.py
narrative_path = "d:/claude2/config/narrative.py"
with open(narrative_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("\r\n", "\n")

# Remove global definitions of:
# FORBIDDEN_WORD_REPLACEMENTS, VILLAIN_STRATEGIES, DEBUFF_PROFILES, CHARACTER_EXPANSION_THEMES, ANTI_PATTERNS
# Let's locate each and remove/comment out or replace them with None/module attributes

to_remove = [
    'FORBIDDEN_WORD_REPLACEMENTS: Dict[str, str] = _data.get("FORBIDDEN_WORD_REPLACEMENTS", {})',
    'VILLAIN_STRATEGIES: Dict[str, str] = _data.get("VILLAIN_STRATEGIES", {})',
    'DEBUFF_PROFILES: Dict[str, str] = _data.get("DEBUFF_PROFILES", {})',
    'CHARACTER_EXPANSION_THEMES: Dict[str, List[str]] = _data.get("CHARACTER_EXPANSION_THEMES", {})',
    'ANTI_PATTERNS: Dict[str, List[str]] = _data.get("ANTI_PATTERNS", {})'
]

for s in to_remove:
    if s in content:
        content = content.replace(s, "# " + s)
        print(f"Commented out: {s}")
    else:
        print(f"Not found in narrative.py: {s}")

# Add __getattr__ at the end of narrative.py
narrative_getattr = """

def __getattr__(name: str) -> Any:
    from core.plugin_loader import PluginLoader

    if name == "VILLAIN_STRATEGIES":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.villain_strategies is not None:
            return plugin.villain_strategies
        return _data.get("VILLAIN_STRATEGIES", {})

    if name == "DEBUFF_PROFILES":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.debuff_profiles is not None:
            return plugin.debuff_profiles
        return _data.get("DEBUFF_PROFILES", {})

    if name == "CHARACTER_EXPANSION_THEMES":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.character_expansion_themes is not None:
            return plugin.character_expansion_themes
        return _data.get("CHARACTER_EXPANSION_THEMES", {})

    if name == "ANTI_PATTERNS":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.anti_patterns is not None:
            return plugin.anti_patterns
        return _data.get("ANTI_PATTERNS", {})

    if name == "FORBIDDEN_WORD_REPLACEMENTS":
        from .base import TrendConfigManager
        return TrendConfigManager.get_instance().forbidden_words_replacements

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
"""
narrative_getattr = narrative_getattr.replace("\r\n", "\n")
content += narrative_getattr

with open(narrative_path, "w", encoding="utf-8") as f:
    f.write(content)
print("config/narrative.py refactored successfully.")


# 3. Refactor config/styles.py
styles_path = "d:/claude2/config/styles.py"
with open(styles_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("\r\n", "\n")

# Comment out STYLE_DEFINITIONS building loop
style_defs_section = """# ==========================================
# MX^C`
# ==========================================
_raw_styles = _data.get("STYLE_DEFINITIONS", {})
STYLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {}

# Oigolden_rules  SHARED_RULES ̃L[Ȃuj
for key, val in _raw_styles.items():
    style = val.copy()
    gr = style.get("golden_rules")
    if gr in _shared:
        style["golden_rules"] = _shared[gr]
    STYLE_DEFINITIONS[key] = style"""

# Let's do a simpler match just on the loop to avoid Shift-JIS comment encoding mismatch
style_loop = """# ==========================================
# \xe6\x9b\xb8\xe3\x81\x8d\xe3\x82\xb9\xe3\x82\xbf\xe3\x82\xa4\xe3\x83\xab
# =========================================="""
# Actually let's just find STYLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {} and the loop.
# Let's replace the whole STYLE_DEFINITIONS setup loop block.
lines = content.split("\n")
new_lines = []
in_style_def = False
for line in lines:
    if "STYLE_DEFINITIONS: Dict[" in line or "STYLE_DEFINITIONS =" in line:
        in_style_def = True
        new_lines.append("# " + line)
        continue
    if in_style_def:
        if "STYLE_DEFINITIONS[key] = style" in line:
            new_lines.append("# " + line)
            in_style_def = False
            continue
        new_lines.append("# " + line)
    else:
        new_lines.append(line)

content = "\n".join(new_lines)

# Add __getattr__ at the end of styles.py
styles_getattr = """

def __getattr__(name: str) -> Any:
    from core.plugin_loader import PluginLoader

    if name == "STYLE_DEFINITIONS":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.style_definitions is not None:
            return {k: v.model_dump() for k, v in plugin.style_definitions.items()}
        
        # Original fallback
        _raw_styles = _data.get("STYLE_DEFINITIONS", {})
        _shared = _data.get("SHARED_RULES", {})
        style_defs = {}
        for key, val in _raw_styles.items():
            style = val.copy()
            gr = style.get("golden_rules")
            if gr in _shared:
                style["golden_rules"] = _shared[gr]
            style_defs[key] = style
        return style_defs

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
"""
styles_getattr = styles_getattr.replace("\r\n", "\n")
content += styles_getattr

with open(styles_path, "w", encoding="utf-8") as f:
    f.write(content)
print("config/styles.py refactored successfully.")


# 4. Refactor config/archetypes.py
archetypes_path = "d:/claude2/config/archetypes.py"
with open(archetypes_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("\r\n", "\n")

# Comment out PLOT_STRUCTURES
old_plot_struct = "PLOT_STRUCTURES: Dict[str, Dict[str, Any]] = _data.get(\"PLOT_STRUCTURES\", {})"
if old_plot_struct in content:
    content = content.replace(old_plot_struct, "# " + old_plot_struct)
    print("Commented out PLOT_STRUCTURES in archetypes.py")

# Add __getattr__ at the end of archetypes.py
archetypes_getattr = """

def __getattr__(name: str) -> Any:
    from core.plugin_loader import PluginLoader

    if name == "PLOT_STRUCTURES":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.plot_structures is not None:
            return {k: v.model_dump() for k, v in plugin.plot_structures.items()}
        return _data.get("PLOT_STRUCTURES", {})

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
"""
archetypes_getattr = archetypes_getattr.replace("\r\n", "\n")
content += archetypes_getattr

with open(archetypes_path, "w", encoding="utf-8") as f:
    f.write(content)
print("config/archetypes.py refactored successfully.")

