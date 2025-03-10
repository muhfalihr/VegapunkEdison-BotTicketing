from typing import Dict, List, Any, Literal
from src.utility.bt_utility import arson, reltime
from src.types.messages import Messages
from src.types.tickets import OpenedTickets
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
    
    def open(self, opened_tickets: List[OpenedTickets], template1: str, template2: str) -> Messages:
        opened_tickets_messages = ""
        
        for ticket in opened_tickets:
            ticket = OpenedTickets(**ticket)

            chat_id = str(ticket.message_chat_id)[4:]
            
            link_message = f"https://t.me/c/{chat_id}/{ticket.message_id}"
            print(link_message)
            relative_time = reltime(ticket.created_at)
            
            opened_tickets_messages += template2.format(
                ticket_id=ticket.ticket_id,
                user_full_name=ticket.userfullname,
                user_id=ticket.user_id,
                relative_time=relative_time,
                link_message=link_message
            ) + "\n"
        
        content = template1.format(list_open_tickets=opened_tickets_messages)
        return self._create_message(content, "Markdown", "group")
    
    def open_ticket_not_found(self, content: str) -> Messages:
        return self._create_message(content, "Markdown", "group")

    def replay_message(self, text: str, **kwargs) -> Messages:
        content: str = text.format(**kwargs)
        return self._create_message(content, "Markdown", "private")
