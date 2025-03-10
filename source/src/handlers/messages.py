import asyncio
from loguru import logger
from typing import List, Dict, Any, Optional, Union
from telebot.types import Message
from telebot.types import (
    InputMedia, 
    InputMediaAnimation, 
    InputMediaAudio, 
    InputMediaDocument, 
    InputMediaPhoto, 
    InputMediaVideo
)
from telebot.async_telebot import AsyncTeleBot

from src.types.config import Config
from src.types.tickets import UserTickets
from src.types.data_store import MessagesStore, MediaStores
from src.types.messages import Messages, MessageJson, MessageJsonDoc, MessageJsonPhoto
from src.utility.bt_formatter import MarkdownFormatter, FormattingEntity
from src.utility.bt_utility import generate_id, epodate, chakey, arson
from src.handlers.tickets import HandlerTickets
from src.controller.bt_issue_generator import IssueGenerator
from src.controller.bt_message import SetupMessage
from src.controller.bt_store import Store


class HandlerMessages:
    """
    Handles message processing and forwarding in the Telegram bot system.
    """
    def __init__(self):
        self.logger = logger
        self.config: Optional[Config] = None
        self.storage: Optional[Store] = None
        self.telebot: Optional[AsyncTeleBot] = None
        self.messages: Optional[SetupMessage] = None
        self.tickets: Optional[HandlerTickets] = None
        self.markdown: Optional[MarkdownFormatter] = None
        self.issue_generator: Optional[IssueGenerator] = None

    async def _send_message(self, chat_id: Union[int, str], message_obj: Messages, 
                           message_type: str = "text", media_id: str = None) -> None:
        """
        Unified method to send different message types to a specified chat.
        
        Args:
            chat_id: The chat ID to send the message to
            message_obj: Messages object containing text and parse mode
            message_type: Type of message to send (text, document, photo)
            media_id: File ID for media messages
        """
        try:
            if message_type == "text":
                await self.telebot.send_message(
                    chat_id=chat_id, 
                    text=message_obj.text, 
                    parse_mode=message_obj.parse_mode
                )
            elif message_type == "document":
                await self.telebot.send_document(
                    chat_id=chat_id,
                    document=media_id,
                    caption=message_obj.text,
                    parse_mode=message_obj.parse_mode
                )
            elif message_type == "photo":
                await self.telebot.send_photo(
                    chat_id=chat_id,
                    photo=media_id,
                    caption=message_obj.text,
                    parse_mode=message_obj.parse_mode
                )
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")

    async def _sender_message_reply(self, message: Message, initial_message: Messages) -> None:
        """
        Reply to a message based on its content type.
        """
        message_chat_id = self.config.telegram.chat_id
        
        try:
            if message.content_type == "text":
                await self._send_message(message_chat_id, initial_message)
            elif message.content_type == "document":
                await self._send_message(message_chat_id, initial_message, "document", message.document.file_id)
            elif message.content_type == "photo":
                await self._send_message(message_chat_id, initial_message, "photo", message.photo[-1].file_id)
        except Exception as e:
            self.logger.error(f"Error in sender_message_reply: {e}")

    async def _sender_message_media_group_reply(
            self, 
            medias: List[Union[InputMedia, InputMediaAnimation, InputMediaAudio, 
                              InputMediaDocument, InputMediaPhoto, InputMediaVideo]], 
            initial_message: Messages) -> None:
        """
        Reply with a media group message.
        """
        message_chat_id = self.config.telegram.chat_id

        try:
            if initial_message.text and medias:
                medias[0].caption = initial_message.text
                medias[0].parse_mode = initial_message.parse_mode

            await self.telebot.send_media_group(
                chat_id=message_chat_id,
                media=medias
            )
        except Exception as e:
            self.logger.error(f"Error sending media group: {e}")
    
    def _get_formatted_message_text(self, message: Message) -> str:
        """
        Extract and format message text from different message types.
        
        Args:
            message: The message to extract text from
        
        Returns:
            Formatted message text
        """
        if message.content_type == "text":
            message_json = MessageJson(**chakey(message.json, "from", "_from"))
            text = message.text or "..."
            entities = message_json.entities
            
            if not text:
                return "..."
            
            return (self.markdown.escape_undescores(text) if not entities else 
                    self.markdown.format_text(text, [FormattingEntity(**entity) for entity in entities]))
        
        elif message.content_type in ["document", "photo"]:
            if message.content_type == "document":
                message_json = MessageJsonDoc(**chakey(message.json, "from", "_from"))
            else:  
                message_json = MessageJsonPhoto(**chakey(message.json, "from", "_from"))
            
            caption = message.caption or "..."
            caption_entities = message_json.caption_entities
            
            if not caption:
                return "..."
            
            return (self.markdown.escape_undescores(caption) if not caption_entities else 
                    self.markdown.format_text(caption, [FormattingEntity(**entity) for entity in caption_entities]))
        
        return "..."
    
    async def _send_to_group(self, ticket_id: int, message: Message) -> None:
        """
        Forward a message to the support group.
        
        Args:
            ticket_id: The ticket ID associated with the message
            message: The message to forward
        """
        try:
            timestamp = epodate(message.date)
            message_text = self._get_formatted_message_text(message)
            
            initial_message = self.messages.replay_message(
                self.config.messages.template_ticket_message, 
                ticket_id=ticket_id,
                user_name=message.from_user.full_name,
                username=message.from_user.username,
                timestamp=timestamp,
                message=message_text,
            )
            
            if getattr(message, 'media_group_id', None):
                media_group_id = self.storage.temp.get("media_group_id")
                media_store = self.storage.temp.get(f"photo_{media_group_id}")
                if media_store and hasattr(media_store, 'medias'):
                    await self._sender_message_media_group_reply(media_store.medias, initial_message)
            else:
                await self._sender_message_reply(message, initial_message)
        except Exception as e:
            self.logger.error(f"Error sending to group: {e}")

    async def _process_media_group_after_delay(self, media_group_id: str) -> None:
        """
        Process a media group after a short delay to collect all media.
        
        Args:
            media_group_id: The ID of the media group to process
        """
        await asyncio.sleep(0.1)  

        try:
            group_data: MessagesStore = self.storage.temp.get(media_group_id)

            if group_data and not group_data.processed:
                ticket_id = group_data.ticket_id
                messages = group_data.messages

                if not messages:
                    self.logger.warning(f"No messages in media group {media_group_id}")
                    return

                
                group_data.processed = True
                self.storage.tempstore(media_group_id, group_data)

                await self._send_to_group(ticket_id=ticket_id, message=messages[0])
        except Exception as e:
            self.logger.error(f"Error processing media group {media_group_id}: {e}")

    async def handler_message_start(self, message: Message) -> Message:
        """
        Handle /start command.
        
        Args:
            message: The message containing the command
            
        Returns:
            The original message
        """
        try:
            initial_message = self.messages.start(self.config.messages.custom_welcome_message)
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            )
        except Exception as e:
            self.logger.error(f"Error handling start message: {e}")
            
        return message

    async def handler_message_private(self, message: Message) -> None:
        """
        Handle messages sent in private chats.
        
        Args:
            message (Message): The message to handle
        """
        try:
            user_tickets = await self.tickets.get_user_tickets(message.from_user.id)
            ticket_open = UserTickets(**next((ticket for ticket in user_tickets), None))

            if not ticket_open:
                ticket_id = generate_id(message.from_user.id)
                await self.tickets.create_ticket(
                    ticket_id=ticket_id,
                    user_id=message.from_user.id,
                    message_id=message.id,
                    message_chat_id=message.chat.id,
                    username=message.from_user.username,
                    userfullname=message.from_user.full_name,
                    issue=await self.issue_generator.issue_generator(message),
                    timestamp=message.date
                )
                await self.tickets.add_message_to_ticket(
                    ticket_id=ticket_id,
                    user_id=message.from_user.id,
                    message_id=message.id,
                    message_chat_id=message.chat.id,
                    username=message.from_user.username,
                    userfullname=message.from_user.full_name,
                    message=await self.issue_generator.issue_generator(message),
                    timestamp=message.date
                )

                initial_message = self.messages.replay_message(
                    self.config.messages.reply_message_private, 
                    ticket_id=ticket_id
                )

                media_group_id = getattr(message, 'media_group_id', None)
                
                if media_group_id:
                    await self._handle_media_group_message(message, media_group_id, ticket_id, initial_message)
                else:
                    await self.telebot.reply_to(
                        message=message,
                        text=initial_message.text,
                        parse_mode=initial_message.parse_mode
                    )
                    await self._send_to_group(ticket_id, message)
            
            else:
                ticket_id = ticket_open.ticket_id
                await self.tickets.add_message_to_ticket(
                    ticket_id=ticket_id,
                    user_id=message.from_user.id,
                    message_id=message.id,
                    message_chat_id=message.chat.id,
                    username=message.from_user.username,
                    userfullname=message.from_user.full_name,
                    message=await self.issue_generator.issue_generator(message),
                    timestamp=message.date
                )

                initial_message = self.messages.replay_message(
                    self.config.messages.reply_message_private, 
                    ticket_id=ticket_id
                )
                await self._send_to_group(ticket_id, message)

        except Exception as e:
            self.logger.error(f"Error handling private message: {e}")

    async def _handle_media_group_message(self, message: Message, media_group_id: str, 
                                         ticket_id: int, initial_message: Messages) -> None:
        """
        Handle messages that are part of a media group.
        
        Args:
            message: The message to handle
            media_group_id: The ID of the media group
            ticket_id: The ticket ID associated with the message
            initial_message: The initial response message
        """
        self.storage.tempstore("media_group_id", media_group_id)

        
        if media_group_id not in self.storage.temp.store:
            self.storage.tempstore(
                media_group_id, 
                MessagesStore(**arson(messages=[], ticket_id=ticket_id, processed=False))
            )
            self.storage.tempstore(f"photo_{media_group_id}", MediaStores(medias=[]))

        
        group_data: MessagesStore = self.storage.temp.get(media_group_id)
        group_data.messages.append(message)
        self.storage.tempstore(media_group_id, group_data)

        
        if hasattr(message, 'photo') and message.photo:
            group_media: MediaStores = self.storage.temp.get(f"photo_{media_group_id}")
            group_media.medias.append(InputMediaPhoto(media=message.photo[-1].file_id))
            self.storage.tempstore(f"photo_{media_group_id}", group_media)
        elif hasattr(message, 'document'):
            
            pass

        
        if len(group_data.messages) == 1:
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,  
                parse_mode=initial_message.parse_mode
            )
            
        
        asyncio.create_task(self._process_media_group_after_delay(media_group_id))
    
    async def handler_open_tickets(self, message: Message):
        opened_tickets = await self.tickets.get_opened_tickets()
        print(opened_tickets)

        if message.from_user.id not in self.config.telegram.admin_ids:
            initial_message: Messages = self.messages.open(self.config.messages.template_open_ticket_in_user)
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            )
        else:
            if not opened_tickets:
                initial_message: Messages = self.messages.open_ticket_not_found(
                    self.config.messages.template_open_ticket_not_found
                )
                await self.telebot.reply_to(
                    message=message,
                    text=initial_message.text,
                    parse_mode=initial_message.parse_mode
                )
            else:
                initial_message = self.messages.open(
                    opened_tickets=opened_tickets,
                    template1=self.config.messages.template_open_ticket_in_admin,
                    template2=self.config.messages.template_link_open_ticket
                )
                await self.telebot.reply_to(
                    message=message,
                    text=initial_message.text,
                    parse_mode=initial_message.parse_mode
                )