from dataclasses import dataclass
from typing import Optional


@dataclass
class UserDetails:
    id: str
    first_name: str
    username: str
    last_name: str


@dataclass
class MessageFrom:
    admin: str = "admin"
    handler: str = "handler"
    user: str = "user"
