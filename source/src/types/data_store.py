from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal
from telebot.types import Message
from telebot.types import (
    InputMedia, 
    InputMediaAnimation, 
    InputMediaAudio, 
    InputMediaDocument, 
    InputMediaPhoto, 
    InputMediaVideo
)
from enum import Enum


@dataclass
class MessagesStore:
    messages: List[Message]
    processed: bool = False


@dataclass
class MediaStores:
    medias: List[InputMedia|InputMediaAnimation|InputMediaAudio|InputMediaDocument|InputMediaPhoto|InputMediaVideo]