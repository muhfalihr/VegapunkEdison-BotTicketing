from typing import Dict, List, Any, Literal
from src.utility.bt_utility import arson
from src.types.messages import Messages
from src.resources.words import URGENT_WORDS


class SetupMessage:
    def __init__(self):
        pass

    @staticmethod
    def _create_message(content: str, parse_mode: Literal["HTML", "Markdown"], mode: Literal["private", "group"]) -> Messages:
        """Create message for telegram bot ticketing"""
        return Messages(**arson(text=content, parse_mode=parse_mode))
    

    @staticmethod
    def _check_message(text: str):
        if any(word in text for word in URGENT_WORDS):
            ...

    
    def start(self, content: str) -> Messages:
        return self._create_message(content, "Markdown", "private")
    
    def open(self, content: str) -> Messages:
        return self._create_message(content, "Markdown", "group")
    
    def open_ticket_not_found(self, content: str) -> Messages:
        return self._create_message(content, "Markdown", "group")

    def replay_message(self, text: str, **kwargs) -> Messages:
        content: str = text.format(**kwargs)
        return self._create_message(content, "Markdown", "private")
