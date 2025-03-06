from typing import List, Dict, Any, Optional

from src.utility.bt_utility import get_config_yaml
from src.types.config import Config, DatabaseConfig, TelegramConfig


class ConfigValidator:
    """Base configuration validator with common validation methods."""
    def __init__(self):
        self.config: Dict[str, Any] = get_config_yaml()
        self._telegram_config: Optional[TelegramConfig] = None
        self._database: Optional[DatabaseConfig] = None

    def validate_telegram_config():
        ...