
import json
import os
import logging
from typing import Dict, Any
from ..utils.appdata import get_appdata_dir

logger = logging.getLogger(__name__)

class Configuration:
    def __init__(self, config_file: str | None = None):
        if config_file is None:
            base_dir = get_appdata_dir()
            config_file = os.path.join(base_dir, "config.json")
        self.config_file = config_file
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        if not os.path.exists(self.config_file):
            logger.info("Config file not found. Using defaults.")
            self.data = {}
            return

        try:
            with open(self.config_file, 'r') as f:
                self.data = json.load(f)
            logger.info("Configuration loaded.")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.data = {}

    def save(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=4)
            logger.info("Configuration saved.")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value
        self.save()

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.data.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in ["1", "true", "yes", "y", "on"]
        return bool(val)

# Global instance
config = Configuration()
