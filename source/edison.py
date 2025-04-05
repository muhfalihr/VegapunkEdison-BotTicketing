import asyncio

from loguru import logger
from aiohttp import ClientSession
from typing import Optional, List
from telebot.handler_backends import State, StatesGroup
from telebot.async_telebot import AsyncTeleBot
from telebot.storage import StateMemoryStorage
from telebot import asyncio_helper

from src.utility.const import COMMANDS
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
        self.tickets: HandlerTickets = HandlerTickets()
        self.markdown: MarkdownFormatter = MarkdownFormatter()
        self.issue_generator: IssueGenerator = IssueGenerator()
        self.handler_admin_ids: Optional[List[str]] = []

        self._setup_handlers()

    def _setup_handlers(self):

        @self.telebot.message_handler(commands=["help"], chat_types=["private", "group", "supergroup"])
        async def help_handler(message):
            ...

        @self.telebot.message_handler(commands=["regist"])
        async def regist_handler(message):
            await self.handler_regist_user_handler(message)
        

        @self.telebot.message_handler(commands=["deregist"])
        async def deregist_handler(message):
            await self.handler_deregist_user_handler(message)


        @self.telebot.message_handler(commands=["handlers"])
        async def user_handler(message):
            await self.handler_get_user_handler(message)


        @self.telebot.message_handler(commands=["start"])
        async def start_handler(message):
            await self.handler_message_start(message)


        @self.telebot.message_handler(commands=["close"], 
                                      chat_types=["group", "supergroup"])
        async def close_ticket_handler(message):
            await self.handler_closed_tickets(message)


        @self.telebot.message_handler(commands=["open"], 
                                      chat_types=["group", "supergroup"])
        async def open_ticket_handler(message):
            await self.handler_open_tickets(message)
        

        @self.telebot.message_handler(commands=["conversation"], 
                                      chat_types=["group", "supergroup"])
        async def conversation_handler(message):
            await self.handler_conversation(message)
        

        @self.telebot.message_handler(commands=["history"], 
                                      chat_types=["group", "supergroup"])
        async def history_handler(message):
            await self.handler_history(message)
        

        @self.telebot.message_handler(content_types=["text"], 
                                      chat_types=["group", "supergroup"], 
                                      func=lambda msg: invalid_command(msg.text, "commands", commands=COMMANDS))
        async def typo_command_handler(message):
            await self.handler_typo_command(message)

        
        @self.telebot.message_handler(content_types=["text", "document", "photo", "video", "sticker"], chat_types=["private"])
        async def handle_message_from_user(message):
            await self.handler_message_private(message)
        

        @self.telebot.message_handler(content_types=["text", "document", "photo", "video", "sticker"], chat_types=["group", "supergroup"])
        async def handle_message_from_admin(message):
            await self.handler_message_group(message)


    async def start_polling(self):
        async with ClientSession() as session:
            asyncio_helper.session = session
            try:
                await self.tickets.setup_tables(
                    database=self.config.database.database,
                    list_tables=self.config.database.tables
                )
                await self._ids_user_admin_handler()
                
                await self.telebot.delete_webhook(drop_pending_updates=True)
                
                await self.telebot.infinity_polling(
                    timeout=10, 
                    request_timeout=60
                )
            except KeyboardInterrupt:
                logger.info("Polling interrupted by user. Shutting down gracefully...")
                await self.telebot.close()
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Polling error: {e}", exc_info=True)
                raise

if __name__ == "__main__":
    bt = BotTicketing()
    asyncio.run(bt.start_polling())