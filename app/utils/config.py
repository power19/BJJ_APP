# app/utils/config.py
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Config file path - stored in project root
CONFIG_FILE = Path(__file__).parent.parent.parent / "config.json"

class AppConfig:
    """Application configuration manager using JSON file storage."""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}")
                self._config = {}
        else:
            self._config = {}

    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """Save configuration to JSON file."""
        try:
            # Merge with existing config
            self._config.update(config_data)

            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._config, f, indent=2)

            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)

    def is_configured(self) -> bool:
        """Check if the application has been configured."""
        required_keys = ['erpnext_url', 'erpnext_api_key', 'erpnext_api_secret']
        return all(self._config.get(key) for key in required_keys)

    def get_erpnext_config(self) -> Dict[str, str]:
        """Get ERPNext configuration."""
        return {
            'url': self._config.get('erpnext_url', ''),
            'api_key': self._config.get('erpnext_api_key', ''),
            'api_secret': self._config.get('erpnext_api_secret', '')
        }

    def get_company(self) -> str:
        """Get the configured company for this gym."""
        return self._config.get('company', '')

    def get_currency(self) -> str:
        """Get the configured currency (default SRD for Suriname)."""
        return self._config.get('currency', 'SRD')

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()

    def clear(self) -> bool:
        """Clear all configuration."""
        try:
            self._config = {}
            if CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
            return True
        except IOError as e:
            print(f"Error clearing config: {e}")
            return False


def get_config() -> AppConfig:
    """Get the application configuration instance."""
    return AppConfig()
