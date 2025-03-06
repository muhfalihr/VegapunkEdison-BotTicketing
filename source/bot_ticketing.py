import asyncio

from loguru import logger
from telebot.handler_backends import State, StatesGroup
from telebot.async_telebot import AsyncTeleBot
from telebot.storage import StateMemoryStorage

from src.config.config import config
from src.controller.bt_store import Store
from src.handlers.messages import HandlerMessages
from src.handlers.tickets import HandlerTickets
from src.controller.bt_message import SetupMessage
from src.utility.bt_formatter import MarkdownFormatter
from src.controller.bt_issue_generator import IssueGenerator


class BotTicketing(HandlerMessages):
    def __init__(self):
        super().__init__()
        self.logger = logger
        self.config = config

        self.telebot: AsyncTeleBot = AsyncTeleBot(
            token=self.config.telegram.token, 
            state_storage=StateMemoryStorage())
        
        self.storage: Store = Store()
        self.messages: SetupMessage = SetupMessage()
        self.tickets: HandlerTickets = HandlerTickets()
        self.markdown: MarkdownFormatter = MarkdownFormatter()
        self.issue_generator: IssueGenerator = IssueGenerator()
        
        self._setup_handlers()

    def _setup_handlers(self):

        @self.telebot.message_handler(commands=["start"])
        async def start_handler(message):
            await self.handler_message_start(message)


        @self.telebot.message_handler(commands=["open"])
        async def open_ticket_handler(message):
            await self.handler_open_tickets(message)

        
        @self.telebot.message_handler(content_types=["text", "document", "photo", "video", "sticker"], chat_types=["private"])
        async def handle_message_from_user(message):
            await self.handler_message_private(message)
        

    async def start_polling(self):
        try:
            await self.tickets.setup_tables(
                database=self.config.database.database, 
                list_tables=self.config.database.tables
            )
            
            await self.telebot.delete_webhook()
            await self.telebot.infinity_polling()
        except Exception as e:
            print(e)
        finally:
            await self.telebot.close_session()


if __name__ == "__main__":
    bt = BotTicketing()
    asyncio.run(bt.start_polling())