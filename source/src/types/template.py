from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional


@dataclass
class MessagesTemplate:
    custom_welcome_message: str
    reply_message_private: str
    reply_additional_message_private: str
    urgent_issue_messagge: str
    template_ticket_message: str
    template_ticket_message_admin: str
    template_reply_bot_message: str
    template_warning_message: str
    template_invalid_message: str
    template_invalid_format_message: str
    template_reply_badwords: str
    template_not_conversation: str
    template_conversation: str
    template_content_conversation: str
    template_open_ticket_in_admin: str
    template_link_open_ticket: str
    template_open_ticket_not_found: str
    template_close_ticket_not_reply: str
    template_closed_ticket: str
    template_user_not_handler: str
    template_not_reply_bot: str
    template_reply_closed_ticket: str
    template_help_private: str
    template_help_group: str
    template_empty_history: str
    template_history: str
    template_list_history: str
    template_admin_only: str
    template_must_reply_ticket: str
    template_must_reply_to_message: str
    template_reply_message_text_none: str
    template_length_too_long_message: str
    template_typo_command: str
    template_added_new_handler: str
    template_delete_handler: str
    template_handlers: str
    template_handlers_content: str
    
@dataclass
class Template:
    messages: MessagesTemplate