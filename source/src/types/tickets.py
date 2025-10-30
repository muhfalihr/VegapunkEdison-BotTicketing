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
    username: str
    message_id: int
    message_chat_id: int
    userfullname: str
    created_at: str


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


@dataclass
class TicketMessages:
    username: str
    userfullname: str
    message: str
    timestamp: Optional[Union[str, datetime]]


@dataclass
class Handlers:
    user_id: int
    username: str
    added_at: Optional[Union[str, datetime]]
    is_active: int


@dataclass
class HistoryHandlerTickets:
    ticket_id: str
    issue: str
    status: str
    created_at: str
    closed_at: str
    handler_username: str


@dataclass
class ClosedTicket:
    ticket_id: str
    handler_username: str
    closed_at: Optional[Union[str, datetime]]