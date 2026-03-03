import asyncio

from loguru import logger
from aiohttp import ClientSession
from typing import Optional, List
from telebot.handler_backends import State, StatesGroup
from telebot.async_telebot import AsyncTeleBot
from telebot.storage import StateMemoryStorage
from telebot import asyncio_helper

from src.utility.const import COMMANDS, TIME_RANGES
from src.localization.config import config
from src.localization.template import template
from src.utility.utility import invalid_command
from src.controller.store import Store
from src.types.tickets import MessageFrom
from src.handlers.messages import HandlerMessages
from src.handlers.tickets import HandlerTickets
from src.controller.message import SetupMessage
from src.utility.formatter import MarkdownFormatter
from src.controller.issue_generator import IssueGenerator
from src.library.database import Model
from src.library.redis import BtRedis


class BotTicketing(HandlerMessages):
    def __init__(self):
        super().__init__()
        self.logger = logger
        self.config = config

        self.logger.info(f"Initializing {self.config.bot.name}")

        self.template = template(self.config.bot.lang)
        self.logger.info(f"Template loaded with language: {self.config.bot.lang}")

        self.telebot: AsyncTeleBot = AsyncTeleBot(
            token=self.config.telegram.token, 
            state_storage=StateMemoryStorage())
        self.logger.info("Telegram bot initialized with state storage")
        
        self.storage: Store = Store()
        self.messages: SetupMessage = SetupMessage()
        self.message_from: MessageFrom = MessageFrom()
        
        # Redis Initialization
        self.redis = BtRedis(self.config.redis)
        
        self.tickets: HandlerTickets = HandlerTickets()
        self.tickets.set_redis(self.redis, self.config.redis.session_ttl)
        
        Model.db = self.tickets
        self.markdown: MarkdownFormatter = MarkdownFormatter()
        self.issue_generator: IssueGenerator = IssueGenerator()
        self.handler_admin_ids: Optional[List[str]] = []

        self._setup_handlers()

    def _setup_handlers(self):

        @self.telebot.message_handler(commands=["help"], chat_types=["private", "group", "supergroup"])
        async def help_handler(message):
            await self.handler_help(message)

        @self.telebot.message_handler(commands=["regist"])
        async def regist_handler(message):
            if await self.tickets.get_user_role(message.from_user.username) == 3:
                await self.handler_regist_user_handler(message)
            else:
                await self._send_error_response(message, self.template.messages.template_admin_only)
        

        @self.telebot.message_handler(commands=["deregist"])
        async def deregist_handler(message):
            if await self.tickets.get_user_role(message.from_user.username) == 3:
                await self.handler_deregist_user_handler(message)
            else:
                await self._send_error_response(message, self.template.messages.template_admin_only)


        @self.telebot.message_handler(commands=["handlers"])
        async def user_handler(message):
            if await self.tickets.get_user_role(message.from_user.username) == 3:
                await self.handler_get_user_handler(message)
            else:
                await self._send_error_response(message, self.template.messages.template_admin_only)


        @self.telebot.message_handler(commands=["start"])
        async def start_handler(message):
            if await self.tickets.get_user_role(message.from_user.username) in [1, 2]:
                await self.handler_message_start(message)
            else:
                await self._send_error_response(message, self.template.messages.template_warning_message)


        @self.telebot.message_handler(commands=["close"], 
                                      chat_types=["group", "supergroup"])
        async def close_ticket_handler(message):
            if await self.tickets.get_user_role(message.from_user.username) == 2:
                await self.handler_closed_tickets(message)
            else:
                await self._send_error_response(message, self.template.messages.template_user_not_handler)


        @self.telebot.message_handler(commands=["open"], 
                                      chat_types=["group", "supergroup"])
        async def open_ticket_handler(message):
            if await self.tickets.get_user_role(message.from_user.username) == 2:
                await self.handler_open_tickets(message)
            else:
                await self._send_error_response(message, self.template.messages.template_user_not_handler)
        

        @self.telebot.message_handler(commands=["conversation"], 
                                      chat_types=["private", "group", "supergroup"])
        async def conversation_handler(message):
            if await self.tickets.get_user_role(message.from_user.username) in [1, 2]:
                await self.handler_conversation(message)
            else:
                await self._send_error_response(message, self.template.messages.template_warning_message)
        

        @self.telebot.message_handler(commands=["history"], 
                                      chat_types=["private", "group", "supergroup"])
        async def history_handler(message):
            if await self.tickets.get_user_role(message.from_user.username) in [1, 2]:
                await self.handler_history(message)
            else:
                await self._send_error_response(message, self.template.messages.template_warning_message)
        

        @self.telebot.callback_query_handler(func=lambda call: True if call.data in TIME_RANGES.split(",") else False)
        async def history_time_range_handler(call):
            await self.handler_history_time_range(call)
        

        @self.telebot.message_handler(content_types=["text"], 
                                      chat_types=["group", "supergroup"], 
                                      func=lambda msg: invalid_command(msg.text, "commands", commands=COMMANDS))
        async def typo_command_handler(message):
            user_role = await self.tickets.ensure_user(
                id=message.from_user.id,
                is_bot=message.from_user.is_bot,
                first_name=message.from_user.first_name,
                username=message.from_user.username,
                last_name=message.from_user.last_name
            )
            if user_role in [2, 3]:
                await self.handler_typo_command(message)
            else:
                await self._send_error_response(message, self.template.messages.template_user_not_handler)

        
        @self.telebot.message_handler(content_types=["text", "document", "photo", "video"], chat_types=["private"])
        async def handle_message_from_user(message):
            user_role = await self.tickets.ensure_user(
                id=message.from_user.id,
                is_bot=message.from_user.is_bot,
                first_name=message.from_user.first_name,
                username=message.from_user.username,
                last_name=message.from_user.last_name
            )
            if user_role in [1, 2, 3]:
                await self.handler_message_private(message)
            else:
                await self._send_error_response(message, self.template.messages.template_warning_message)
        

        @self.telebot.message_handler(content_types=["text", "document", "photo", "video"], chat_types=["group", "supergroup"])
        async def handle_message_from_admin(message):
            user_role = await self.tickets.ensure_user(
                id=message.from_user.id,
                is_bot=message.from_user.is_bot,
                first_name=message.from_user.first_name,
                username=message.from_user.username,
                last_name=message.from_user.last_name
            )
            if user_role in [2, 3]:
                await self.handler_message_group(message)
            else:
                await self._send_error_response(message, self.template.messages.template_user_not_handler)

    async def _auto_close_task(self):
        """
        Background task to periodically check for expired ticket sessions.
        """
        while True:
            try:
                self.logger.debug("Running auto-close check for expired tickets...")
                await self.tickets.check_and_close_expired_tickets(self.config.timezone)
            except Exception as e:
                self.logger.error(f"Error in auto-close task: {e}")
            
            # Check every 5 minutes
            await asyncio.sleep(300)

    async def start_polling(self):
        async with ClientSession() as session:
            asyncio_helper.session = session
            try:
                # Connect to Redis
                await self.redis.connect()
                
                await self.tickets.setup_tables(
                    database=self.config.database.database
                )
                
                # Initialize admins from config
                await self.tickets.initialize_admins(self.config.telegram.admin_ids)
                
                # Start auto-close background task
                asyncio.create_task(self._auto_close_task())
                
                await self.telebot.delete_webhook(drop_pending_updates=True)
                
                await self.telebot.infinity_polling(
                    timeout=10, 
                    request_timeout=60
                )
            except KeyboardInterrupt:
                logger.info("Polling interrupted by user. Shutting down gracefully...")
                await self.telebot.close()
                await self.redis.disconnect()
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Polling error: {e}", exc_info=True)
                await self.redis.disconnect()
                raise
