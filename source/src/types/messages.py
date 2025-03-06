from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Literal


@dataclass
class Messages:
    text: str
    parse_mode: str


@dataclass
class MessageJsonFrom:
    id: int
    is_bot: bool
    first_name: str
    last_name: str
    username: str
    language_code: str


@dataclass
class ForwardOrigin:
    type: str
    sender_user: MessageJsonFrom
    date: int


@dataclass
class MessageJsonChat:
    id: int
    first_name: str
    last_name: str
    username: str
    type: str


@dataclass
class MessageJson:
    message_id: int
    _from: MessageJsonFrom
    chat: MessageJsonChat
    date: int
    text: str
    entities: Optional[List[Dict[str, Any]]] = None


@dataclass
class Document:
    file_name: str
    mime_type: str
    file_id: str
    file_unique_id: str
    file_size: str


@dataclass
class Photo:
    file_id: str
    file_unique_id: str
    file_size: int
    width: int
    height: int


@dataclass
class MessageJsonDoc:
    message_id: int
    _from: MessageJsonFrom
    chat: MessageJsonChat
    date: int
    document: Document
    caption: Optional[str] = None
    forward_origin: Optional[ForwardOrigin] = None
    forward_from: Optional[MessageJsonFrom] = None
    forward_date: Optional[int] = None
    media_group_id: Optional[str] = None
    caption_entities: Optional[List[Dict[str, Any]]] = None


@dataclass
class MessageJsonPhoto:
    message_id: int
    _from: MessageJsonFrom
    chat: MessageJsonChat
    date: int
    photo: List[Photo]
    caption: Optional[str] = None
    forward_origin: Optional[ForwardOrigin] = None
    forward_from: Optional[MessageJsonFrom] = None
    forward_date: Optional[int] = None
    media_group_id: Optional[str] = None
    caption_entities: Optional[List[Dict[str, Any]]] = None