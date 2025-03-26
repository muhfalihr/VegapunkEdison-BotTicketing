import re
from typing import List, Dict, Any, Optional

from src.utility.utility import get_config_yaml
from src.utility.const import MESSAGE_PATTERN
from src.types.config import Config, DatabaseConfig, TelegramConfig


class ConfigValidator:
    """Base configuration validator with common validation methods."""
    def __init__(self):
        self.config: Dict[str, Any] = get_config_yaml()
        self._telegram_config: Optional[TelegramConfig] = None
        self._database: Optional[DatabaseConfig] = None

    @staticmethod
    def _matcher(s: str, p: str):
        pattern = re.compile(p)
        matches = pattern.match(s)
        return matches is not None

    def validate_telegram_config():
        ...

    def message_bot(self, text: str):
        if self._matcher(text, MESSAGE_PATTERN):
            return True
        return False