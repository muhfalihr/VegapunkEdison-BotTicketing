from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional


@dataclass
class TelegramConfig:
    token: str
    chat_id: int
    admin_ids: List[int]

@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    tables: List[str]

@dataclass
class Config:
    telegram: TelegramConfig
    database: DatabaseConfig
    timezone: str
