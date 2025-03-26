from typing import Dict, List, Any, Literal
from src.utility.utility import arson, reltime
from src.types.messages import Messages
from src.types.tickets import OpenedTickets, HistoryHandlerTickets
# from src.resources.words import URGENT_WORDS


class SetupMessage:
    def __init__(self):
        pass

    @staticmethod
    def _create_message(content: str, parse_mode: Literal["HTML", "Markdown"], mode: Literal["private", "group"]) -> Messages:
        """Create message for telegram bot ticketing"""
        return Messages(**arson(text=content, parse_mode=parse_mode))
    

    # @staticmethod
    # def _check_message(text: str):
    #     if any(word in text for word in URGENT_WORDS):
    #         ...

    
    def privcommon(self, content: str) -> Messages:
        return self._create_message(content, "Markdown", "private")
    
    def groupcommon(self, content: str) -> Messages:
        return self._create_message(content, "Markdown", "group")
    
    def open(self, opened_tickets: List[OpenedTickets], template1: str, template2: str) -> Messages:
        opened_tickets_messages = "\n"
        
        for ticket in opened_tickets:
            ticket = OpenedTickets(**ticket)
            chat_id = str(ticket.message_chat_id).replace("-100", "").replace("-", "")
            
            link_message = f"https://t.me/c/{chat_id}/{ticket.message_id}"
            relative_time = reltime(ticket.created_at)
            
            opened_tickets_messages += "\n" + template2.format(
                ticket_id=ticket.ticket_id,
                user_full_name=ticket.userfullname,
                username=ticket.username,
                relative_time=relative_time,
                link_message=link_message
            )
        
        content = template1.format(list_open_tickets=opened_tickets_messages)
        return self._create_message(content, "Markdown", "group")
    
    # def open_ticket_not_found(self, content: str) -> Messages:
    #     return self._create_message(content, "Markdown", "group")

    def replay_message(self, text: str, **kwargs) -> Messages:
        content: str = text.format(**kwargs)
        return self._create_message(content, "Markdown", "private")
    
    def reply_message_group(self, text: str, **kwargs) -> Messages:
        content: str = text.format(**kwargs)
        return self._create_message(content, "Markdown", "group")
    
    def conversation_message(self, template: str, content_template: str, **kwargs):
        contents = kwargs.get("contents")
        ticket_id = kwargs.get("ticket_id")
        
        conversation = "\n"
        space = (' ' * 4)

        for content in contents:
            conversation += "\n" + content_template.format(
                space=space,
                userfullname=content.userfullname,
                username=content.username,
                message=content.message,
                timestamp=content.timestamp
            )
        
        full_content = template.format(ticket_id=ticket_id, conversation=conversation)
        return self._create_message(full_content, "Markdown", "group")


    def history_message(self, template: str, content_template: str, contents: List[HistoryHandlerTickets]):
        histories = "\n"
        space = (' ' * 3)

        for content in contents:
            print(content.created_at)
            histories += "\n" + content_template.format(
                space=space,
                ticket_id=content.ticket_id,
                status=content.status.upper(),
                timestamp=content.created_at
            )
        
        full_content = template.format(history_handling_tickets=histories)
        return self._create_message(full_content, "Markdown", "group")

    # def reply_invalid_message(self, content: str) -> Messages:
    #     return self._create_message(content, "Markdown", "private")
    
    # def reply_badwords_message(self, content: str) -> Messages:
    #     return self._create_message(content, "Markdown", "private")