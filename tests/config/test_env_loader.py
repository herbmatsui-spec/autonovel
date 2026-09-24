import os
from unittest.mock import patch
from src.config.env_loader import load_config

def test_loads_local_by_default():
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
        assert config["database"]["type"] == "sqlite"

def test_loads_production_when_set():
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        config = load_config()
        assert config["database"]["type"] == "postgresql"