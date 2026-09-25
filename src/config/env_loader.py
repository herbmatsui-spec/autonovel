import os
import yaml
from typing import Any, Dict

def load_config() -> Dict[str, Any]:
    """
    Load configuration based on the ENVIRONMENT variable.
    Defaults to 'local' if not set.
    """
    env = os.environ.get("ENVIRONMENT", "local").lower()
    config_file = f"config/{env}.yaml"
    
    # Fallback to local if the specified file doesn't exist
    if not os.path.exists(config_file):
        config_file = "config/local.yaml"
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Validate and convert types (example validation)
    # In a real implementation, you would have a more thorough validation
    # For now, we just return the config as is.
    return config