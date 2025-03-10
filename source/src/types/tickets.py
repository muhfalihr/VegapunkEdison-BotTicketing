from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Union, Optional


@dataclass
class UserTickets:
    ticket_id: str
    user_id: int
    message_id: int
    message_chat_id: int
    issue: str
    status: str
    created_at: Union[str, datetime]
    closed_at: Optional[Union[str, datetime]]
    handler_username: str


@dataclass
class OpenedTickets:
    ticket_id: str
    user_id: int
    message_id: int
    message_chat_id: int
    userfullname: str
    created_at: str