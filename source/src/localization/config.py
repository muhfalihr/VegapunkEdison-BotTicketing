from src.types.config import Config, TelegramConfig, DatabaseConfig
from src.utility.utility import get_config_yaml, arson


_main_config = get_config_yaml()

_telegram_config = TelegramConfig(**_main_config.get("telegram", {}))
_database_config = DatabaseConfig(**_main_config.get("database", {}))


config = Config(**arson(
    telegram=_telegram_config,
    database=_database_config,
    timezone=_main_config.get("timezone", "Asia/Jakarta")
))