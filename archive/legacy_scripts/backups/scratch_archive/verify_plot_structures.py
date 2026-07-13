import os
import sys

# Append the project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from config import PLOT_STRUCTURES
    print("Successfully imported config.py!")
    print(f"Number of plot structures: {len(PLOT_STRUCTURES)}")

    # Check that all keys have the required fields
    required_keys = {"name", "hook", "mid_crisis", "climax_type", "ending", "key_tropes"}
    valid = True
    for key, structure in PLOT_STRUCTURES.items():
        missing = required_keys - set(structure.keys())
        if missing:
            print(f"Error: structure '{key}' is missing keys: {missing}")
            valid = False

    if valid:
        print("All plot structures are valid and have correct schemas!")
    else:
        sys.exit(1)

except Exception as e:
    print(f"Import/Validation failed with error: {e}")
    sys.exit(1)

# Debug details
from config.data_loader import ConfigDataLoader

data = ConfigDataLoader.get_archetypes()
print("Raw PLOT_STRUCTURES in archetypes.json count:", len(data.get("PLOT_STRUCTURES", {})))

from core.plugin_loader import PluginLoader

plugin = PluginLoader.get_instance().get_active_plugin()
print("Active plugin:", plugin.__class__.__name__ if plugin else None)
if plugin and plugin.plot_structures is not None:
    print("Plugin plot_structures count:", len(plugin.plot_structures))
else:
    print("Plugin plot_structures is None")

