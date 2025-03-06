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
class MessagesConfig:
    custom_welcome_message: str
    reply_message_private: str
    urgent_issue_messagge: str
    template_ticket_message: str
    template_open_ticket_in_user: str
    template_open_ticket_in_admin: str
    template_open_ticket_not_found: str


@dataclass
class Config:
    telegram: TelegramConfig
    database: DatabaseConfig
    messages: MessagesConfig
    timezone: str
