import asyncio

from loguru import logger
from typing import List, Dict, Any, Optional, Union
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery
from telebot.types import (
    InputMedia, 
    InputMediaAnimation, 
    InputMediaAudio, 
    InputMediaDocument, 
    InputMediaPhoto, 
    InputMediaVideo
)

from src.utility.const import (
    INVALID_MESSAGE_IN_USER, 
    BAD_WORDS, 
    MESSAGE_PATTERN,
    MESSAGE_PATTERN_DETAILS,
    TIME_RANGES
)

from src.types.config import Config
from src.types.template import Template
from src.types.tickets import UserTickets, MessageFrom, UserDetails
from src.types.data_store import MessagesStore, MediaStores
from src.types.messages import (
    Messages, 
    MessageJson, 
    MessageJsonDoc, 
    MessageJsonPhoto, 
    MessageJsonVideo
)
from src.utility.formatter import MarkdownFormatter, FormattingEntity
from src.utility.utility import generate_id, epodate, chakey, arson, search
from src.utility.markup import keyboard_markup
from src.handlers.tickets import HandlerTickets
from src.controller.issue_generator import IssueGenerator
from src.controller.message import SetupMessage
from src.controller.store import Store


class HandlerMessages:
    """
    Handles message processing and forwarding in the Telegram bot system.
    """
    def __init__(self):
        self.logger = logger
        self.config: Optional[Config] = None
        self.storage: Optional[Store] = None
        self.template: Optional[Template] = None
        self.telebot: Optional[AsyncTeleBot] = None
        self.messages: Optional[SetupMessage] = None
        self.tickets: Optional[HandlerTickets] = None
        self.markdown: Optional[MarkdownFormatter] = None
        self.issue_generator: Optional[IssueGenerator] = None
        self.message_from: Optional[MessageFrom] = None
        self.handler_admin_ids: Optional[List[str]] = []


    async def _ids_user_admin_handler(self):
        self.handler_admin_ids = (
            self.config.telegram.admin_ids + 
            [handler.user_id for handler in await self.tickets.get_all_handlers()]
        )

    async def _send_message(self, chat_id: Union[int, str], message_obj: Messages, 
                           message_type: str = "text", media_id: str = None) -> Message:
        """
        Unified method to send different message types to a specified chat.
        
        Args:
            chat_id: The chat ID to send the message to
            message_obj: Messages object containing text and parse mode
            message_type: Type of message to send (text, document, photo)
            media_id: File ID for media messages
        """
        if message_type == "text":
            msg: Message = await self.telebot.send_message(
                chat_id=chat_id, 
                text=message_obj.text, 
                parse_mode=message_obj.parse_mode
            )
        elif message_type == "document":
            msg: Message = await self.telebot.send_document(
                chat_id=chat_id,
                document=media_id,
                caption=message_obj.text,
                parse_mode=message_obj.parse_mode
            )
        elif message_type == "photo":
            msg: Message = await self.telebot.send_photo(
                chat_id=chat_id,
                photo=media_id,
                caption=message_obj.text,
                parse_mode=message_obj.parse_mode
            )
        elif message_type == "video":
            msg: Message = await self.telebot.send_video(
                chat_id=chat_id,
                video=media_id,
                caption=message_obj.text,
                parse_mode=message_obj.parse_mode
            )
        
        return msg

    async def _sender_message_reply(self, chat_id: int,  message: Message, initial_message: Messages) -> None:
        """
        Sends a reply message based on the content type of the original message.

        Args:
            chat_id (int): The unique identifier of the target chat.
            message (Message): The original message to determine the content type.
            initial_message (Messages): The message object containing the content to reply with.

        Returns:
            None
        """
        if message.content_type == "text":
            msg: Message = await self._send_message(chat_id, initial_message)
        elif message.content_type == "document":
            msg: Message = await self._send_message(chat_id, initial_message, "document", message.document.file_id)
        elif message.content_type == "photo":
            msg: Message = await self._send_message(chat_id, initial_message, "photo", message.photo[-1].file_id)
        elif message.content_type == "video":
            msg: Message = await self._send_message(chat_id, initial_message, "video", message.video.file_id)
        return msg

    async def _sender_message_media_group_reply(
            self, 
            chat_id: int,
            medias: List[Union[InputMedia, InputMediaAnimation, InputMediaAudio, 
                              InputMediaDocument, InputMediaPhoto, InputMediaVideo]], 
            initial_message: Messages) -> None:
        """
        Sends a media group message as a reply.

        Args:
            chat_id (int): The unique identifier of the target chat.
            medias (List[Union[InputMedia, ...]]): A list of media items to be sent as a group.
            initial_message (Messages): The reference message containing optional caption text and parse mode.

        Returns:
            None
        """
        try:
            if initial_message.text and medias:
                medias[0].caption = initial_message.text
                medias[0].parse_mode = initial_message.parse_mode
            
            msg: Message = await self.telebot.send_media_group(
                chat_id=chat_id,
                media=medias
            )
            return msg
        except Exception as e:
            self.logger.error(f"Error sending media group: {e}")
    
    def _safe_format_markdown(self, text: str, entities: list) -> str:
        """
        Safely format text using markdown. Fallback to escaped markdown if error occurs.
        
        Args:
            text: The raw text to format
            entities: List of formatting entities
        
        Returns:
            Formatted markdown text or fallback text
        """
        try:
            return self.markdown.format_text(text, [FormattingEntity(**entity) for entity in entities])
        except Exception as e:
            self.logger.error(f"Error Formatting Markdown: {e}")
            return self.markdown.escape_markdown(text)

    
    def _get_formatted_message_text(self, message: Message) -> str:
        """
        Extract and format message text from different message types.
        
        Args:
            message: The message to extract text from
        
        Returns:
            Formatted message text (str).
        """
        if message.content_type == "text":
            message_json = MessageJson(**chakey(message.json, "from", "_from"))
            text = message.text or "..."
            entities = message_json.entities
            
            if not text:
                return "..."
            
            return (self.markdown.escape_markdown(text) if not entities else 
                    self._safe_format_markdown(text, entities))
        
        elif message.content_type in ["document", "photo", "video"]:
            if message.content_type == "document":
                message_json = MessageJsonDoc(**chakey(message.json, "from", "_from"))
            elif message.content_type == "photo":
                message_json = MessageJsonPhoto(**chakey(message.json, "from", "_from"))
            else:
                message_json = MessageJsonVideo(**chakey(message.json, "from", "_from"))
            
            caption = message.caption or "..."
            caption_entities = message_json.caption_entities
            
            if not caption:
                return "..."
            
            return (self.markdown.escape_markdown(caption) if not caption_entities else 
                    self._safe_format_markdown(caption, caption_entities))
        
        return "..."

    def _get_formatted_reply_to_message_text(self, message: Message) -> str:
        """
        Extract and format reply to message text from different message types.
        
        Args:
            message: The message to extract text from
        
        Returns:
            Formatted message text (str).
        """
        if message.reply_to_message.content_type == "text":
            message_json = MessageJson(**chakey(message.reply_to_message.json, "from", "_from"))
            text = message.reply_to_message.text or "..."
            entities = message_json.entities
            
            if not text:
                return "..."
            
            return (self.markdown.escape_markdown(text) if not entities else 
                    self._safe_format_markdown(text, entities))
        
        elif message.reply_to_message.content_type in ["document", "photo", "video"]:
            if message.reply_to_message.content_type == "document":
                message_json = MessageJsonDoc(**chakey(message.reply_to_message.json, "from", "_from"))
            elif message.reply_to_message.content_type == "photo":
                message_json = MessageJsonPhoto(**chakey(message.reply_to_message.json, "from", "_from"))
            else:
                message_json = MessageJsonVideo(**chakey(message.reply_to_message.json, "from", "_from"))
            
            caption = message.reply_to_message.caption or "..."
            caption_entities = message_json.caption_entities
            
            if not caption:
                return "..."
            
            return (self.markdown.escape_markdown(caption) if not caption_entities else 
                    self._safe_format_markdown(caption, caption_entities))
        
        return "..."
    
    async def _send_to_group(self, ticket_id: int, message: Message) -> None:
        """
        Forward a message to the support group.
        
        Args:
            ticket_id: The ticket ID associated with the message
            message: The message to forward
        
        Returns:
            None
        """
        try:
            timestamp = epodate(message.date)
            message_text = self._get_formatted_message_text(message)
            message_text_non_format = self.markdown.escape_markdown(message.text or message.caption or "...")

            reply_to_message_text = None
            reply_to_message_text_non_format = None

            if message.reply_to_message:
                reply_to_message_text_raw = (message.reply_to_message.text or message.reply_to_message.caption or "...")

                matches = search(reply_to_message_text_raw, MESSAGE_PATTERN_DETAILS)
                if matches:
                    details_message = matches.group(1)
                    message.reply_to_message.text = details_message

                reply_to_message_text = self._get_formatted_reply_to_message_text(message)
                reply_to_message_text_non_format = self.markdown.escape_markdown(details_message)

            full_name = message.from_user.full_name
            username = self.markdown.escape_markdown(message.from_user.username)
            
            if not message.reply_to_message:
                initial_message_format = self.messages.replay_message(
                    self.template.messages.template_ticket_message, 
                    ticket_id=ticket_id,
                    user_name=full_name,
                    username=username,
                    timestamp=timestamp,
                    message=message_text,
                )

                initial_message_non_format = self.messages.replay_message(
                    self.template.messages.template_ticket_message, 
                    ticket_id=ticket_id,
                    user_name=full_name,
                    username=username,
                    timestamp=timestamp,
                    message=message_text_non_format,
                )
            else:
                initial_message_format = self.messages.replay_message(
                    self.template.messages.template_ticket_reply_to_message, 
                    ticket_id=ticket_id,
                    user_name=full_name,
                    username=username,
                    timestamp=timestamp,
                    message=message_text,
                    reply_to_message=reply_to_message_text
                )

                initial_message_non_format = self.messages.replay_message(
                    self.template.messages.template_ticket_reply_to_message, 
                    ticket_id=ticket_id,
                    user_name=full_name,
                    username=username,
                    timestamp=timestamp,
                    message=message_text_non_format,
                    reply_to_message=reply_to_message_text_non_format
                )
            
            if getattr(message, 'media_group_id', None):
                media_group_id = self.storage.temp.get("media_group_id")

                if hasattr(message, 'photo') and message.photo:
                    media_store = self.storage.temp.get(f"photo_{media_group_id}")
                    
                    if media_store and hasattr(media_store, 'medias'):
                        try:
                            msg: Message = await self._sender_message_media_group_reply(
                                chat_id=self.config.telegram.chat_id, 
                                medias=media_store.medias, 
                                initial_message=initial_message_format
                            )
                        except:
                            msg: Message = await self._sender_message_media_group_reply(
                                chat_id=self.config.telegram.chat_id, 
                                medias=media_store.medias, 
                                initial_message=initial_message_non_format
                            )
                
                elif hasattr(message, 'video') and message.video:
                    media_store = self.storage.temp.get(f"video_{media_group_id}")
                    
                    if media_store and hasattr(media_store, 'medias'):
                        try:
                            msg: Message = await self._sender_message_media_group_reply(
                                chat_id=self.config.telegram.chat_id, 
                                medias=media_store.medias, 
                                initial_message=initial_message_format
                            )
                        except:
                            msg: Message = await self._sender_message_media_group_reply(
                                chat_id=self.config.telegram.chat_id, 
                                medias=media_store.medias, 
                                initial_message=initial_message_non_format
                            )

                elif hasattr(message, 'document') and message.document:
                    media_store = self.storage.temp.get(f"document_{media_group_id}")
                    
                    if media_store and hasattr(media_store, 'medias'):
                        try:
                            msg: Message = await self._sender_message_media_group_reply(
                                chat_id=self.config.telegram.chat_id, 
                                medias=media_store.medias, 
                                initial_message=initial_message_format
                            )
                        except:
                            msg: Message = await self._sender_message_media_group_reply(
                                chat_id=self.config.telegram.chat_id, 
                                medias=media_store.medias, 
                                initial_message=initial_message_non_format
                            )
                        
            else:
                try:
                    msg: Message = await self._sender_message_reply(
                        chat_id=self.config.telegram.chat_id, 
                        message=message, 
                        initial_message=initial_message_format
                    )
                except:
                    msg: Message = await self._sender_message_reply(
                        chat_id=self.config.telegram.chat_id, 
                        message=message, 
                        initial_message=initial_message_non_format
                    )
            return msg
        except Exception as e:
            self.logger.error(f"Error sending to group: {e}")
    

    async def _send_to_private(self, message: Message, ticket_id: str, from_group: bool = False, username: str = None) -> Message:
        """
        Send a message to a private chat.

        Args:
            message (Message): The message object to send.
            from_group (bool, optional): Whether the message is from a group. Defaults to False.
            username (str, optional): The target username. Defaults to None.

        Returns:
            Message: The sent message object.
        """
        message_text = self._get_formatted_message_text(message)
        
        timestamp = epodate(message.date)
        full_name = message.from_user.full_name
        username_ = self.markdown.escape_markdown(message.from_user.username)
        
        initial_message = self.messages.replay_message(
            text=self.template.messages.template_ticket_message_admin,
            ticket_id=ticket_id,
            user_name=full_name,
            username=username_,
            message=message_text,
            timestamp=timestamp
        )
        message_from_user_id = message.from_user.id
        if from_group:
            message_from_user_id = await self.tickets.get_userid_by_username(username)
            message_from_user_id = message_from_user_id.get("id") if message_from_user_id else None

        if getattr(message, 'media_group_id', None):
            media_group_id = self.storage.temp.get("media_group_id")

            if hasattr(message, 'photo') and message.photo:
                media_store = self.storage.temp.get(f"photo_{media_group_id}")
                if media_store and hasattr(media_store, 'medias'):
                    msg: Message = await self._sender_message_media_group_reply(
                        chat_id=message_from_user_id, 
                        medias=media_store.medias, 
                        initial_message=initial_message
                    )
            
            elif hasattr(message, 'video') and message.video:
                media_store = self.storage.temp.get(f"video_{media_group_id}")
                if media_store and hasattr(media_store, 'medias'):
                    msg: Message = await self._sender_message_media_group_reply(
                        chat_id=message_from_user_id, 
                        medias=media_store.medias, 
                        initial_message=initial_message
                    )
                
            elif hasattr(message, 'document') and message.document:
                media_store = self.storage.temp.get(f"document_{media_group_id}")
                if media_store and hasattr(media_store, 'medias'):
                    msg: Message = await self._sender_message_media_group_reply(
                        chat_id=message_from_user_id, 
                        medias=media_store.medias, 
                        initial_message=initial_message
                    )

        else:
            msg: Message = await self._sender_message_reply(message_from_user_id, message, initial_message)
        return msg
    

    async def _send_closed_private(self, chat_id: str, message: Message, **kwargs) -> None:
        """
        Send a closed ticket message to a private chat.

        Args:
            chat_id (str): The ID of the chat to send the message to.
            message (Message): The original message object.
            **kwargs: Additional arguments to format the message template.

        Returns:
            None
        """
        initial_message = self.messages.replay_message(
            self.template.messages.template_closed_ticket,
            **kwargs
        )
        await self._sender_message_reply(
            chat_id, message, initial_message
        )

    async def _process_media_groups_after_delay(self, message_origin: Message, media_group_id: str) -> None:
        """
        Process a media group after a short delay to collect all media.
        
        Args:
            media_group_id: The ID of the media group to process
        
        Returns:
            None
        
        Raises:
            Exception: If there is an error during message processing or sending.
        """
        await asyncio.sleep(0.01)

        try:
            group_data: MessagesStore = self.storage.temp.get(media_group_id)

            if group_data and not group_data.processed:
                messages = group_data.messages

                if not messages:
                    self.logger.warning(f"No messages in media group {media_group_id}")
                    return
                
                group_data.processed = True
                self.storage.tempstore(media_group_id, group_data)
                
                _message = messages[-1]
                
                for message in messages:
                    message_text = (message.text or message.caption)
                    if message_text:
                        _message = message
                        break

                ticket_id = generate_id(_message.from_user.id)
                initial_message = self.messages.replay_message(
                    self.template.messages.reply_message_private, 
                    ticket_id=ticket_id,
                    bot_name=self.config.bot.name
                )

                user_tickets = await self.tickets.get_user_tickets(_message.from_user.id)
                ticket_open = next(iter(user_tickets), None)

                if not ticket_open:
                    await self.telebot.reply_to(
                        message=message_origin,
                        text=initial_message.text,  
                        parse_mode=initial_message.parse_mode
                    )

                    msg: Union[Message,List[Message]] = await self._send_to_group(ticket_id=ticket_id, message=_message)
                    
                    issue = await self.issue_generator.issue_generator(_message)
                    await self.tickets.create_ticket(
                        ticket_id=ticket_id,
                        user_id=_message.from_user.id,
                        message_id=msg[-1].id,
                        message_chat_id=msg[-1].chat.id,
                        username=_message.from_user.username,
                        userfullname=_message.from_user.full_name,
                        issue=issue,
                        timestamp=_message.date
                    )

                    if isinstance(msg, list):
                        for m in msg:
                            await self.tickets.add_message_to_ticket(
                                ticket_id=ticket_id,
                                user_id=_message.from_user.id,
                                message_id=m.id,
                                message_chat_id=m.chat.id,
                                username=_message.from_user.username,
                                userfullname=_message.from_user.full_name,
                                message=await self.issue_generator.issue_generator(_message),
                                message_from=self.message_from.user,
                                timestamp=_message.date
                            )
                        return

                    await self.tickets.add_message_to_ticket(
                        ticket_id=ticket_id,
                        user_id=_message.from_user.id,
                        message_id=msg.id,
                        message_chat_id=msg.chat.id,
                        username=_message.from_user.username,
                        userfullname=_message.from_user.full_name,
                        message=await self.issue_generator.issue_generator(_message),
                        message_from=self.message_from.user,
                        timestamp=_message.date
                    ); return
                
                ticket_open = UserTickets(**ticket_open)
                ticket_id = ticket_open.ticket_id
                initial_message = self.messages.replay_message(
                    self.template.messages.reply_additional_message_private, 
                    ticket_id=ticket_id
                )

                await self.telebot.reply_to(
                    message=message_origin,
                    text=initial_message.text,  
                    parse_mode=initial_message.parse_mode
                )
                msg: Union[Message,List[Message]] = await self._send_to_group(ticket_id=ticket_id, message=_message)
                    
                if isinstance(msg, list):
                    for m in msg:
                        await self.tickets.add_message_to_ticket(
                            ticket_id=ticket_id,
                            user_id=_message.from_user.id,
                            message_id=m.id,
                            message_chat_id=m.chat.id,
                            username=_message.from_user.username,
                            userfullname=_message.from_user.full_name,
                            message=await self.issue_generator.issue_generator(_message),
                            message_from=self.message_from.user,
                            timestamp=_message.date
                        ); return

                await self.tickets.add_message_to_ticket(
                    ticket_id=ticket_id,
                    user_id=_message.from_user.id,
                    message_id=msg.id,
                    message_chat_id=msg.chat.id,
                    username=_message.from_user.username,
                    userfullname=_message.from_user.full_name,
                    message=await self.issue_generator.issue_generator(_message),
                    message_from=self.message_from.user,
                    timestamp=_message.date
                ); return
            
        except Exception as e:
            self.logger.error(f"Error processing media group {media_group_id}: {e}")

    async def _process_media_private_after_delay(self, ticket_id: str, media_group_id: str, username: str, initial_message: Messages) -> Message:
        """
        Process media group and send the message to a private chat after a delay.

        Args:
            media_group_id (str): The unique identifier for the media group.
            username (str): The target username to send the message to.

        Returns:
            Message: The sent message object.

        Raises:
            Exception: If there is an error during message processing or sending.
        """
        await asyncio.sleep(0.1)

        try:
            group_data: MessagesStore = self.storage.temp.get(media_group_id)

            if group_data and not group_data.processed:
                messages = group_data.messages

                if not messages:
                    self.logger.warning(f"No messages in media group {media_group_id}")
                    return
                
                group_data.processed = True
                self.storage.tempstore(media_group_id, group_data)
                
                _message = messages[-1]
                
                for message in messages:
                    message_text = (message.text or message.caption)
                    if message_text:
                        _message = message
                        break

                await self._send_to_private(message=_message, ticket_id=ticket_id, from_group=True, username=username)
                await self.telebot.reply_to(
                    message=message,
                    text=initial_message.text,
                    parse_mode=initial_message.parse_mode
                )
        
        except Exception as e:
            self.logger.error(f"Error processing media group {media_group_id}: {e}")


    async def _handler_invalid_message(self, message: Message):
        """
        Handle invalid messages by checking against a list of invalid message contents.

        Args:
            message (Message): The incoming message to validate.

        Returns:
            None
        """
        if message.text or message.caption in INVALID_MESSAGE_IN_USER.split(","):
            initial_message = self.messages.privcommon(self.template.messages.template_invalid_message)
            self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            ); return
        return
    
    async def _store_media_group(self, **kwargs):
        message: Message = kwargs.get("message")
        media_group_id: int = kwargs.get("media_group_id")
        
        self.storage.tempstore("media_group_id", media_group_id)

        if media_group_id not in self.storage.temp.store:
            self.storage.tempstore(
                media_group_id, 
                MessagesStore(**arson(messages=[], processed=False))
            )
            if hasattr(message, 'photo') and message.photo:
                self.storage.tempstore(f"photo_{media_group_id}", MediaStores(medias=[]))
            elif hasattr(message, 'video') and message.video:
                self.storage.tempstore(f"video_{media_group_id}", MediaStores(medias=[]))
            elif hasattr(message, 'document') and message.document:
                self.storage.tempstore(f"document_{media_group_id}", MediaStores(medias=[]))

        group_data: MessagesStore = self.storage.temp.get(media_group_id)
        group_data.messages.append(message)
        self.storage.tempstore(media_group_id, group_data)
        
        if hasattr(message, 'photo') and message.photo:
            group_media: MediaStores = self.storage.temp.get(f"photo_{media_group_id}")
            group_media.medias.append(InputMediaPhoto(media=message.photo[-1].file_id))
            self.storage.tempstore(f"photo_{media_group_id}", group_media)
        
        elif hasattr(message, 'video') and message.video:
            group_media: MediaStores = self.storage.temp.get(f"video_{media_group_id}")
            group_media.medias.append(InputMediaVideo(media=message.video.file_id))
            self.storage.tempstore(f"video_{media_group_id}", group_media)

        elif hasattr(message, 'document') and message.document:
            group_media: MediaStores = self.storage.temp.get(f"document_{media_group_id}")
            group_media.medias.append(InputMediaDocument(media=message.document.file_id))
            self.storage.tempstore(f"document_{media_group_id}", group_media)

    
    async def _handle_media_group_message_private(self, message: Message, media_group_id: str) -> None:
        """
        Handle messages that are part of a media group.
        
        Args:
            message: The message to handle
            media_group_id: The ID of the media group
            ticket_id: The ticket ID associated with the message
            initial_message: The initial response message
        """
        await self._store_media_group(
            message=message,
            media_group_id=media_group_id
        )
        asyncio.create_task(self._process_media_groups_after_delay(message, media_group_id))


    async def _handle_media_group_message_group(self, message: Message, media_group_id: str, 
                                         ticket_id: int, username: str, initial_message: Messages) -> None:
        """
        Handle messages that are part of a media group.
        
        Args:
            message: The message to handle
            media_group_id: The ID of the media group
            ticket_id: The ticket ID associated with the message
            username: The target username to send the message to.
            initial_message: The initial response message
        
        Returns:
            None
        """
        await self._store_media_group(
            message=message,
            media_group_id=media_group_id
        )
        asyncio.create_task(self._process_media_private_after_delay(ticket_id, media_group_id, username, initial_message))


    async def _send_error_response(self, message: Message | CallbackQuery, template, **kwargs):
        """
        Helper method to send error responses and reduce code duplication.
        
        Args:
            message (Message): Original message
            template: Message template
            **kwargs: Additional formatting arguments
        """
        if isinstance(message, Message):
            initial_message = self.messages.groupcommon(template, **kwargs)
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            )
        elif isinstance(message, CallbackQuery):
            initial_message = self.messages.groupcommon(template, **kwargs)
            await self.telebot.send_message(
                chat_id=message.message.chat.id,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            )
    

    async def handler_help(self, message: Message):
        """
        Handle /help command.

        Args:
            message (Message): The message containing the command
        
        Returns:
            Message
        """
        try:
            initial_message = self.messages.reply_message_group(
                text=self.template.messages.template_help,
                bot_name=self.config.bot.name
            )
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            )
        except Exception as e:
            self.logger.error(f"Error handling help message: {e}")
        
        return message


    async def handler_message_start(self, message: Message) -> Message:
        """
        Handle /start command.
        
        Args:
            message (Message): The message containing the command
            
        Returns:
            The original message
        """
        try:
            initial_message = self.messages.replay_message(
                self.template.messages.custom_welcome_message,
                bot_name=self.config.bot.name
            )
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
        Handle messages sent in private chats with improved efficiency.
        
        Args:
            message (Message): The message to handle
        """
        try:
            message_content = (message.text or message.caption or "")
            
            if len(message_content) > 4000:
                initial_message = self.messages.privcommon(
                    self.template.messages.template_length_too_long_message
                )
                await self.telebot.reply_to(
                    message=message,
                    text=initial_message.text,
                    parse_mode=initial_message.parse_mode
                ); return

            invalid_words = set(INVALID_MESSAGE_IN_USER.split(","))
            bad_words = set(BAD_WORDS.split(","))
            
            if any(word == message_content for word in invalid_words):
                initial_message = self.messages.privcommon(self.template.messages.template_invalid_message)
                await self.telebot.reply_to(
                    message=message,
                    text=initial_message.text,
                    parse_mode=initial_message.parse_mode
                ); return

            if any(word in message_content for word in bad_words):
                initial_message = self.messages.privcommon(self.template.messages.template_reply_badwords)
                await self.telebot.reply_to(
                    message=message,
                    text=initial_message.text,
                    parse_mode=initial_message.parse_mode
                ); return

            user_details_db = await self.tickets.get_user_details_by_id(message.from_user.id)
            if not user_details_db:
                await self.tickets.registration_user(
                    id=message.from_user.id,
                    is_bot=message.from_user.is_bot,
                    first_name=message.from_user.first_name,
                    username=message.from_user.username,
                    last_name=message.from_user.last_name
                )
            
            if user_details_db:
                user_details_tele = {
                    "id": str(message.from_user.id),
                    "is_bot": int(message.from_user.is_bot) if hasattr(message.from_user, "is_bot") else 0,
                    "first_name": message.from_user.first_name,
                    "username": message.from_user.username,
                    "last_name": message.from_user.last_name,
                }

                exclude_keys = {"id"}
                diff = {}
                for key in user_details_tele:
                    if key in exclude_keys:
                        continue

                    tele_value = user_details_tele.get(key)
                    db_value = user_details_db.get(key)

                    if tele_value != db_value:
                        diff[key] = {"tele": tele_value, "db": db_value}

                user_details_tele.pop("is_bot")

                if diff:
                    user_details = UserDetails(**user_details_tele)

                    if (user_details_db["username"] != user_details.username) or \
                        (user_details_db["first_name"] != user_details.first_name) or \
                            (user_details_db["last_name"] != user_details.last_name):
                        
                        await self.tickets.update_user(id=user_details.id,
                                                       first_name=user_details.first_name,
                                                       username=user_details.username,
                                                       last_name=user_details.last_name)

            media_group_id = getattr(message, 'media_group_id', None)
            if media_group_id:
                await self._handle_media_group_message_private(message, media_group_id)
            else:

                user_tickets = await self.tickets.get_user_tickets(message.from_user.id)
                ticket_open = next(iter(user_tickets), None)

                if not ticket_open:
                    ticket_id = generate_id(message.from_user.id)
                    initial_message = self.messages.replay_message(
                        self.template.messages.reply_message_private, 
                        ticket_id=ticket_id,
                        bot_name=self.config.bot.name
                    )

                    await self.telebot.reply_to(
                        message=message,
                        text=initial_message.text,
                        parse_mode=initial_message.parse_mode
                    )
                    msg: Message = await self._send_to_group(ticket_id, message)

                    issue = await self.issue_generator.issue_generator(message)
                    await self.tickets.create_ticket(
                        ticket_id=ticket_id,
                        user_id=message.from_user.id,
                        message_id=msg.id,
                        message_chat_id=msg.chat.id,
                        username=message.from_user.username,
                        userfullname=message.from_user.full_name,
                        issue=issue,
                        timestamp=message.date
                    )
                    await self.tickets.add_message_to_ticket(
                        ticket_id=ticket_id,
                        user_id=message.from_user.id,
                        message_id=msg.id,
                        message_chat_id=msg.chat.id,
                        username=message.from_user.username,
                        userfullname=message.from_user.full_name,
                        message=issue,
                        message_from=self.message_from.user,
                        timestamp=message.date
                    ); return

                ticket_open = UserTickets(**ticket_open)
                ticket_id = ticket_open.ticket_id
                initial_message = self.messages.replay_message(
                    self.template.messages.reply_additional_message_private, 
                    ticket_id=ticket_id
                )

                await self.telebot.reply_to(
                    message=message,
                    text=initial_message.text,
                    parse_mode=initial_message.parse_mode
                )
                msg: Message = await self._send_to_group(ticket_id, message)
                
                issue = await self.issue_generator.issue_generator(message)
                await self.tickets.add_message_to_ticket(
                    ticket_id=ticket_id,
                    user_id=message.from_user.id,
                    message_id=msg.id,
                    message_chat_id=msg.chat.id,
                    username=message.from_user.username,
                    userfullname=message.from_user.full_name,
                    message=issue,
                    message_from=self.message_from.user,
                    timestamp=message.date
                ); return

        except Exception as e:
            self.logger.error(f"Error handling private message: {e}")
    
    async def handler_message_group(self, message: Message):
        """
        Handle messages sent in group chats.
        
        Args:
            message (Message): The message to handle
        """
        try:
            message_content = (message.text or message.caption or "")
            if len(message_content) > 4000:
                return await self._send_error_response(
                    message=message,
                    template=self.template.messages.template_length_too_long_message
                )
            
            if message.from_user.id not in self.handler_admin_ids:
                return await self._send_error_response(
                    message=message,
                    template=self.template.messages.template_user_not_handler
                )

            if not message.reply_to_message:
                return await self._send_error_response(
                    message=message,
                    template=self.template.messages.template_must_reply_ticket
                )
            
            if message.reply_to_message.from_user.id != self.config.telegram.bot_id:
                return

            reply_text = (message.reply_to_message.text or message.reply_to_message.caption)
            matches = search(reply_text, MESSAGE_PATTERN)
            if not matches:
                return await self._send_error_response(
                    message=message, 
                    template=self.template.messages.template_invalid_format_message
                )

            ticket_id = matches.group(1)
            username = matches.group(3)

            closed_ticket = await self.tickets.get_closed_ticket_by_ticketid(ticket_id)
            if closed_ticket:
                initial_message = self.messages.reply_message_group(
                    self.template.messages.template_reply_closed_ticket,
                    username=closed_ticket.handler_username,
                    datetime=closed_ticket.closed_at
                )
                await self.telebot.reply_to(
                    message=message,
                    text=initial_message.text,
                    parse_mode=initial_message.parse_mode
                ); return

            initial_message = self.messages.replay_message(
                self.template.messages.template_reply_bot_message,
                ticket_id=ticket_id
            )

            media_group_id = getattr(message, 'media_group_id', None)
            if media_group_id:
                await self._handle_media_group_message_group(
                    message=message, 
                    media_group_id=media_group_id, 
                    ticket_id=ticket_id,
                    username=username, 
                    initial_message=initial_message
                ); return

            msg: Message = await self._send_to_private(message, ticket_id, True, username)
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            )

            await self.tickets.add_message_to_ticket(
                ticket_id=ticket_id,
                user_id=message.from_user.id,
                message_id=msg.id,
                message_chat_id=msg.chat.id,
                username=message.from_user.username,
                userfullname=message.from_user.full_name,
                message=await self.issue_generator.issue_generator(message),
                message_from=self.message_from.handler,
                timestamp=message.date
            ); return
            
        except Exception as e:
            self.logger.error(f"Error handling group message: {e}")


    async def handler_open_tickets(self, message: Message):
        """
        Handles the command to display open tickets.

        This method retrieves all open tickets and checks if the user is an admin or a handler.
        If the user is not authorized, a warning message is sent. If no open tickets are found,
        an appropriate message is sent. Otherwise, a list of open tickets is displayed.

        Args:
            message (Message): The incoming Telegram message object.

        Returns:
            None
        """
        try:
            if message.from_user.id not in self.handler_admin_ids:
                return await self._send_error_response(
                    message=message,
                    template=self.template.messages.template_user_not_handler
                )
            
            opened_tickets = await self.tickets.get_opened_tickets()
            if not opened_tickets:
                return await self._send_error_response(
                    message=message,
                    template=self.template.messages.template_open_ticket_not_found
                )
        
            initial_message = self.messages.open(
                opened_tickets=opened_tickets,
                template1=self.template.messages.template_open_ticket_in_admin,
                template2=self.template.messages.template_link_open_ticket,
                func=self.markdown.escape_markdown
            )
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            ); return
        
        except Exception as e:
            self.logger.error(f"Error handling open tickets: {e}")


    async def handler_closed_tickets(self, message: Message):
        """
        Handles the command to closed tickets.

        Args:
            message (Message): The incoming Telegram message object.

        Returns:
            None
        """
        if not message.reply_to_message:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_close_ticket_not_reply
            )
        
        if message.from_user.id not in self.handler_admin_ids:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_user_not_handler
            )

        messages = message.reply_to_message.text or message.reply_to_message.caption
        matches = search(messages, MESSAGE_PATTERN)
        if not matches:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_invalid_format_message
            )
    
        ticket_id = matches.group(1)
        username = matches.group(3)

        closed_ticket = await self.tickets.get_closed_ticket_by_ticketid(ticket_id)
        if closed_ticket:
            initial_message = self.messages.reply_message_group(
                self.template.messages.template_reply_closed_ticket,
                username=closed_ticket.handler_username,
                datetime=closed_ticket.closed_at
            )
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            ); return

        user_id = await self.tickets.get_userid_by_username(username)

        timestamp = epodate(message.date)
        handler_username = self.markdown.escape_markdown(message.from_user.username)
        await self.tickets.close_ticket(
            ticket_id=ticket_id,
            handler_id=message.from_user.id,
            handler_username=handler_username,
            timezone=self.config.timezone
        )

        initial_message = self.messages.replay_message(
            text=self.template.messages.template_closed_ticket,
            ticket_id=ticket_id,
            username=self.markdown.escape_markdown(message.from_user.username),
            timestamp=timestamp
        )
        await self.telebot.reply_to(
            message=message,
            text=initial_message.text,
            parse_mode=initial_message.parse_mode
        )
        await self._send_closed_private(
            user_id.get("id"), 
            message, 
            ticket_id=ticket_id, 
            username=self.markdown.escape_markdown(message.from_user.username),
            timestamp=timestamp
        ); return


    async def handler_conversation(self, message: Message):
        """
        Handler the command conversation tickets.

        Args:
            message (Message): The incoming Telegram message object.

        Returns:
            None
        """
        if not message.reply_to_message:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_must_reply_ticket
            )
        
        messages = message.reply_to_message.text or message.reply_to_message.caption
        matches = search(messages, MESSAGE_PATTERN)

        if not matches:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_invalid_format_message
            )

        ticket_id = matches.group(1)
        conversation = await self.tickets.get_ticket_messages(
            ticket_id=ticket_id,
            user_id=message.from_user.id,
            is_handler=True,
        )

        if not conversation:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_not_conversation,
                ticket_id=ticket_id
            )
        
        initial_message = self.messages.conversation_message(
            template=self.template.messages.template_conversation,
            content_template=self.template.messages.template_content_conversation,
            contents=conversation,
            ticket_id=ticket_id,
            func=self.markdown.escape_markdown
        )
        await self.telebot.reply_to(
            message=message,
            text=initial_message.text,
            parse_mode=initial_message.parse_mode
        ); return


    async def handler_history(self, message: Message):
        """
        Handler the command history tickets.

        Args:
            message (Message): The incoming Telegram message object.

        Returns:
            None
        """
        if message.chat.type in ["supergroup", "group"]:
            ticket_handling = await self.tickets.get_handler_tickets_history(message.from_user.id)
            if not ticket_handling:
                return await self._send_error_response(
                    message=message,
                    template=self.template.messages.template_empty_history
                )
            
            initial_message = self.messages.history_message(
                template=self.template.messages.template_history,
                content_template=self.template.messages.template_list_history,
                contents=ticket_handling,
                time_range="today"
            )
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode
            ); return
        else:
            initial_message = self.messages.reply_message_group(
                self.template.messages.template_time_range_history
            )
            await self.telebot.reply_to(
                message=message,
                text=initial_message.text,
                parse_mode=initial_message.parse_mode,
                reply_markup=keyboard_markup(TIME_RANGES.split(","))
            )
    

    async def handler_history_time_range(self, call: CallbackQuery):
        time_range = call.data
        history_tickets = await self.tickets.get_user_tickets_history(
            user_id=call.from_user.id,
            time_range=time_range
        )
        if not history_tickets:
            return await self._send_error_response(
                message=call,
                template=self.template.messages.template_empty_history
            )
        
        initial_message = self.messages.history_message(
            template=self.template.messages.template_history,
            content_template=self.template.messages.template_list_history,
            contents=history_tickets,
            time_range=time_range
        )
        await self.telebot.send_message(
            chat_id=call.message.chat.id, 
            text=initial_message.text, 
            parse_mode=initial_message.parse_mode
        ); return
    

    async def handler_typo_command(self, message: Message):
        """
        Handler the typo command.

        Args:
            message (Message): The incoming Telegram message object.

        Returns:
            None
        """
        if message.from_user.id not in self.handler_admin_ids:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_user_not_handler
            )
        
        initial_message = self.messages.groupcommon(
            self.template.messages.template_typo_command
        )
        await self.telebot.reply_to(
            message=message,
            text=initial_message.text,
            parse_mode=initial_message.parse_mode
        );  return


    async def handler_regist_user_handler(self, message: Message):
        """
        Handler the command regist user handler.

        Args:
            message (Message): The incoming Telegram message object.

        Returns:
            None
        """
        if not message.reply_to_message:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_must_reply_to_message
            )
        
        if message.reply_to_message.from_user.id == self.config.telegram.bot_id:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_not_reply_bot
            )

        if message.from_user.id not in self.config.telegram.admin_ids:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_admin_only
            )
        
        message_reply_text = message.reply_to_message.text or message.reply_to_message.caption
        if not message_reply_text:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_reply_message_text_none
            )
        
        await self.tickets.registration_handler(
            user_id=message.reply_to_message.from_user.id,
            username=message.reply_to_message.from_user.username
        )

        # Refresh Get User Handler
        self.handler_admin_ids = (
            self.config.telegram.admin_ids + 
            [handler.user_id for handler in await self.tickets.get_all_handlers()]
        )

        username = self.markdown.escape_markdown(message.reply_to_message.from_user.username)
        initial_message = self.messages.reply_message_group(
            self.template.messages.template_added_new_handler,
            username=username
        )
        await self.telebot.reply_to(
            message=message,
            text=initial_message.text,
            parse_mode=initial_message.parse_mode
        ); return
    

    async def handler_get_user_handler(self, message: Message):
        """
        Handler the command get user handler.

        Args:
            message (Message): The incoming Telegram message object.

        Returns:
            None
        """
        if message.from_user.id not in self.config.telegram.admin_ids:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_admin_only
            )
        
        handlers = await self.tickets.get_all_handlers()
        if not handlers:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_empty_handlers
            )
        
        initial_message = self.messages.handlers_message(
            template=self.template.messages.template_handlers,
            content_template=self.template.messages.template_handlers_content,
            contents=handlers,
            func=self.markdown.escape_markdown
        )
        await self.telebot.reply_to(
            message=message,
            text=initial_message.text,
            parse_mode=initial_message.parse_mode
        ); return
    

    async def handler_deregist_user_handler(self, message: Message):
        """
        Handler the command deregist user handler.

        Args:
            message (Message): The incoming Telegram message object.

        Returns:
            None
        """
        if not message.reply_to_message:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_must_reply_to_message
            )
        
        if message.reply_to_message.from_user.id == self.config.telegram.bot_id:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_not_reply_bot
            )
        
        if message.from_user.id not in self.config.telegram.admin_ids:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_admin_only
            )
        
        message_reply_text = message.reply_to_message.text or message.reply_to_message.caption
        if not message_reply_text:
            return await self._send_error_response(
                message=message,
                template=self.template.messages.template_reply_message_text_none
            )
        
        await self.tickets.deregistration_handler(
            user_id=message.reply_to_message.from_user.id
        )
        
        # Refresh Get User Handler
        self.handler_admin_ids = (
            self.config.telegram.admin_ids + 
            [handler.user_id for handler in await self.tickets.get_all_handlers()]
        )
        
        username = self.markdown.escape_markdown(message.reply_to_message.from_user.username)
        initial_message = self.messages.reply_message_group(
            self.template.messages.template_delete_handler,
            username=username
        )
        await self.telebot.reply_to(
            message=message,
            text=initial_message.text,
            parse_mode=initial_message.parse_mode
        ); return