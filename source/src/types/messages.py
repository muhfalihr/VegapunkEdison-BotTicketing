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
    message_thread_id: Optional[int] = None
    reply_to_message: Optional[Dict[str, Any]] = None
    text: str = "..."
    entities: Optional[List[Dict[str, Any]]] = None
    has_protected_content: Optional[bool] = False


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
class Thumbnail:
    file_id: str
    file_unique_id: str
    file_size: int
    width: int
    height: int


@dataclass
class Video:
    duration: int
    width: int
    height: int
    thumbnail: Thumbnail
    thumb: Thumbnail
    file_id: str
    file_unique_id: str
    file_size: int


@dataclass
class MessageJsonDoc:
    message_id: int
    _from: MessageJsonFrom
    chat: MessageJsonChat
    date: int
    document: Document
    message_thread_id: Optional[int] = None
    reply_to_message: Optional[Dict[str, Any]] = None
    caption: Optional[str] = None
    forward_origin: Optional[ForwardOrigin] = None
    forward_from: Optional[MessageJsonFrom] = None
    forward_date: Optional[int] = None
    media_group_id: Optional[str] = None
    caption_entities: Optional[List[Dict[str, Any]]] = None
    has_protected_content: Optional[bool] = False


@dataclass
class MessageJsonPhoto:
    message_id: int
    _from: MessageJsonFrom
    chat: MessageJsonChat
    date: int
    photo: List[Photo]
    message_thread_id: Optional[int] = None
    reply_to_message: Optional[Dict[str, Any]] = None
    caption: Optional[str] = None
    forward_origin: Optional[ForwardOrigin] = None
    forward_from: Optional[MessageJsonFrom] = None
    forward_date: Optional[int] = None
    media_group_id: Optional[str] = None
    caption_entities: Optional[List[Dict[str, Any]]] = None
    has_protected_content: Optional[bool] = False

@dataclass
class MessageJsonVideo:
    message_id: int
    _from: MessageJsonFrom
    chat: MessageJsonChat
    date: int
    video: Video
    message_thread_id: Optional[int] = None
    reply_to_message: Optional[Dict[str, Any]] = None
    caption: Optional[str] = None
    forward_origin: Optional[ForwardOrigin] = None
    forward_from: Optional[MessageJsonFrom] = None
    forward_date: Optional[int] = None
    media_group_id: Optional[str] = None
    caption_entities: Optional[List[Dict[str, Any]]] = None
    has_protected_content: Optional[bool] = False