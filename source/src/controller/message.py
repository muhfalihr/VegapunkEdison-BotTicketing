from typing import Dict, List, Any, Literal
from src.utility.utility import arson, reltime
from src.types.messages import Messages
from src.types.tickets import OpenedTickets, HistoryHandlerTickets, Handlers


class SetupMessage:
    def __init__(self):
        pass

    @staticmethod
    def _create_message(content: str, parse_mode: Literal["HTML", "Markdown"], mode: Literal["private", "group"]) -> Messages:
        """Create message for telegram bot ticketing"""
        return Messages(**arson(text=content, parse_mode=parse_mode))
    
    def privcommon(self, content: str) -> Messages:
        return self._create_message(content, "Markdown", "private")
    
    def groupcommon(self, content: str, **kwargs) -> Messages:
        if not kwargs:
            return self._create_message(content, "Markdown", "group")
        return self._create_message(content.format(**kwargs), "Markdown", "group")
    
    def open(self, opened_tickets: List[OpenedTickets], template1: str, template2: str, **kwargs) -> Messages:
        func = kwargs.get("func")
        opened_tickets_messages = "\n"
        
        for ticket in opened_tickets:
            ticket = OpenedTickets(**ticket)
            chat_id = str(ticket.message_chat_id).replace("-100", "").replace("-", "")
            
            link_message = f"https://t.me/c/{chat_id}/{ticket.message_id}"
            relative_time = reltime(ticket.created_at)
            
            username = func(ticket.username)
            userfullname = func(ticket.userfullname)

            opened_tickets_messages += "\n" + template2.format(
                ticket_id=ticket.ticket_id,
                user_full_name=userfullname,
                username=username,
                relative_time=relative_time,
                link_message=link_message
            )
        
        content = template1.format(list_open_tickets=opened_tickets_messages)
        return self._create_message(content, "Markdown", "group")

    def replay_message(self, text: str, **kwargs) -> Messages:
        content: str = text.format(**kwargs)
        return self._create_message(content, "Markdown", "private")
    
    def reply_message_group(self, text: str, **kwargs) -> Messages:
        content: str = text.format(**kwargs)
        return self._create_message(content, "Markdown", "group")
    
    def conversation_message(self, template: str, content_template: str, **kwargs):
        contents = kwargs.get("contents")
        ticket_id = kwargs.get("ticket_id")
        func = kwargs.get("func")
        
        conversation = "\n"
        space = (' ' * 4)

        for content in contents:
            content_message = content.message if len(content.message) < 100 \
                else content.message[:100] + "..."
            
            conversation += "\n" + content_template.format(
                space=space,
                userfullname=func(content.userfullname),
                username=func(content.username),
                message=func(content_message),
                timestamp=content.timestamp
            )
        
        full_content = template.format(ticket_id=ticket_id, conversation=conversation)
        return self._create_message(full_content, "Markdown", "group")


    def history_message(self, template: str, content_template: str, contents: List[HistoryHandlerTickets]):
        histories = "\n"
        space = (' ' * 3)

        for content in contents:
            histories += "\n" + content_template.format(
                space=space,
                ticket_id=content.ticket_id,
                status=content.status.upper(),
                timestamp=content.closed_at
            )
        
        full_content = template.format(history_handling_tickets=histories)
        return self._create_message(full_content, "Markdown", "group")

    def handlers_message(self, template: str, content_template: str, contents: List[Handlers], **kwargs):
        func = kwargs.get("func")
        handlers = "\n"
        space = (' ' * 3)
        
        for content in contents:
            username = func(content.username)
            handlers += content_template.format(
                space=space,
                username=username,
                user_id=content.user_id
            )
        
        full_content = template.format(user_handlers=handlers)
        return self._create_message(full_content, "Markdown", "group")