import re
import traceback

from typing import List, Dict, Any, Optional
from loguru import logger

from src.resources.queries import (
    CREATE_TABLE_TICKETS,
    CREATE_TABLE_TICKET_MESSAGES,
    CREATE_TABLE_BANNED_USERS,
    CREATE_TABLE_HANDLERS,
    GET_ALL_TABLES,
    INSERT_USER_FOR_HANDLER,
    GET_ALL_HANDLERS,
    CHECK_USER_IS_HANDLER,
    CREATE_TICKET,
    ADDED_TICKET_MESSAGE,
    GET_TICKET_BY_ID,
    CLOSED_TICKET,
    GET_USER_TICKETS,
    GET_CLOSED_TICKETS,
    GET_OPENED_TICKETS
)
from src.types.tickets import UserTickets, OpenedTickets
from src.utility.bt_utility import generate_id, curtime, epodate
from src.library.bt_aiomysql import BtAioMysql


class HandlerTickets(BtAioMysql):
    """Handles database operations related to support ticket handlers and messages."""
    
    def __init__(self, pool_size: int = 10, connect_timeout: int = 10):
        """Initialize the handler store.
        
        Args:
            pool_size: Maximum number of connections in the pool
            connect_timeout: Connection timeout in seconds
        """
        super().__init__(pool_size, connect_timeout)
        self.logger = logger
    
    async def setup_tables(self, database: str, list_tables: List[str]) -> None:
        """
        Create required tables for the handler system if they do not exist.
        
        Args:
            database (str): The database name
            list_tables (List[str]): List of tables to check and create
        
        Raises:
            Exception: If table creation fails
        """
        try:
            existing_tables = await self.fetch_all(GET_ALL_TABLES, (database,))
            existing_table_names = [table.get("TABLE_NAME") for table in existing_tables]
            self.logger.info(existing_table_names)

            tables_to_create = [
                table_def for table_def in [
                    CREATE_TABLE_TICKETS, 
                    CREATE_TABLE_TICKET_MESSAGES, 
                    CREATE_TABLE_BANNED_USERS, 
                    CREATE_TABLE_HANDLERS
                ]
                if self._extract_table_name(table_def) not in existing_table_names
            ]

            if tables_to_create:
                await self.create_tables(table_definitions=tables_to_create)
                self.logger.info(f"Created {len(tables_to_create)} new handler system tables")
            else:
                self.logger.info("All required tables already exist")

        except Exception as e:
            self.logger.error(f"Failed to setup handler system tables: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    def _extract_table_name(self, create_table_statement: str) -> str:
        """
        Extract table name from a CREATE TABLE statement.
        
        Args:
            create_table_statement (str): SQL CREATE TABLE statement
        
        Returns:
            str: Name of the table
        """
        try:
            table_name = None
            pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:``|`)?([a-zA-Z0-9_]+)(?:``|`)?'
            match = re.search(pattern, create_table_statement, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                return table_name
            return table_name
        
        except Exception as e:
            self.logger.warning(f"Could not extract table name from: {str(e)}")
            return
    
    async def registration_handler(self, user_id: int, username: str) -> bool:
        """Register a new support handler in the system.
        
        Args:
            user_id: Unique identifier for the user
            username: Username for the handler
            
        Returns:
            True if registration was successful
        """
        try:
            affected_rows = await self.execute(INSERT_USER_FOR_HANDLER, (user_id, username))
            self.logger.info(f"Registered new handler: {username} (ID: {user_id})")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to register handler {username}: {str(e)}")
            raise
    
    async def get_all_handlers(self) -> List[Dict[str, Any]]:
        """Retrieve all registered support handlers.
        
        Returns:
            List of handler records
        """
        try:
            handlers = await self.fetch_all(GET_ALL_HANDLERS)
            self.logger.debug(f"Retrieved {len(handlers)} handlers")
            return handlers
        except Exception as e:
            self.logger.error(f"Failed to retrieve handlers: {str(e)}")
            raise
        
    async def is_user_handler(self, user_id: int) -> bool:
        """Check if a user is registered as a support handler.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if the user is a registered handler
        """
        try:
            result = await self.fetch_one(CHECK_USER_IS_HANDLER, (user_id,))
            return result is not None
        except Exception as e:
            self.logger.error(f"Failed to check handler status for user {user_id}: {str(e)}")
            raise
    
    async def create_ticket(
            self, ticket_id: str, user_id: str, message_id: int, message_chat_id: int,
            username: str, userfullname: str, issue: str, timestamp: int) -> bool:
        """Create a new support ticket in the database.
        
        Args:
            ticket_id: ID of the ticket
            user_id: ID of the user creating the ticket
            username: Username of the ticket creator
            issue: Description of the issue
            timestamp: Timestamp of the issue
            
        Returns:
            True if ticket was created successfully
        """
        status = 'open'
        datetime = epodate(timestamp, store=True)

        try:
            affected_rows = await self.execute(
                CREATE_TICKET, (ticket_id, user_id, message_id, message_chat_id, username, userfullname, issue, datetime, status)
            )
            self.logger.info(f"Created ticket {ticket_id} for user {username}")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to create ticket for user {username}: {str(e)}")
            raise
    
    async def add_message_to_ticket(
            self, 
            ticket_id: str, 
            user_id: int, 
            message_id: int,
            message_chat_id: int, 
            username: str, 
            userfullname: str, 
            message: str,
            timestamp: str) -> bool:
        """Add a message to an existing ticket.
        
        Args:
            ticket_id: ID of the ticket
            user_id: ID of the message sender
            username: Username of the message sender
            message: Content of the message
            timezone: Timestamp of the message
            
        Returns:
            True if message was added successfully
        """
        datetime = epodate(timestamp, store=True)

        try:
            affected_rows = await self.execute(
                ADDED_TICKET_MESSAGE, 
                (ticket_id, user_id, message_id, message_chat_id, username, userfullname, message, datetime)
            )
            self.logger.debug(f"Added message to ticket {ticket_id} by {username}")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to add message to ticket {ticket_id}: {str(e)}")
            raise

    async def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a ticket by its ID.
        
        Args:
            ticket_id: ID of the ticket to retrieve
            
        Returns:
            Ticket data as dictionary or None if not found
        """
        try:
            result = await self.fetch_one(GET_TICKET_BY_ID, (ticket_id,))
            return result
        except Exception as e:
            self.logger.error(f"Failed to retrieve ticket {ticket_id}: {str(e)}")
            raise
    
    async def close_ticket(self, ticket_id: str, handler_id: int, handler_username: str, timezone: str) -> bool:
        """Mark a ticket as closed.
        
        Args:
            ticket_id: ID of the ticket to close
            handler_id: ID of the handler closing the ticket
            handler_username: Username of the handler
            timezone: Handler's timezone for timestamp calculation
            
        Returns:
            True if ticket was closed successfully
        """
        current_time = curtime(timezone)
        try:
            affected_rows = await self.execute(
                CLOSED_TICKET, 
                (handler_id, handler_username, current_time, ticket_id)
            )
            self.logger.info(f"Ticket {ticket_id} closed by handler {handler_username}")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to close ticket {ticket_id}: {str(e)}")
            raise
    
    async def get_user_tickets(self, user_id: int) -> List[UserTickets]:
        """Retrieve all tickets created by a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of ticket records
        """
        try:
            tickets: List[UserTickets] = await self.fetch_all(GET_USER_TICKETS, (user_id,))
            self.logger.debug(f"Retrieved {len(tickets)} tickets for user {user_id}")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve tickets for user {user_id}: {str(e)}")
            raise

    async def get_closed_tickets(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve all closed tickets for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of closed ticket records
        """
        try:
            tickets = await self.fetch_all(GET_CLOSED_TICKETS, (user_id,))
            self.logger.debug(f"Retrieved {len(tickets)} closed tickets for user {user_id}")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve closed tickets for user {user_id}: {str(e)}")
            raise
    
    async def get_opened_tickets(self) -> List[OpenedTickets]:
        """Retrieve all currently open tickets in the system.
        
        Returns:
            List of open ticket records
        """
        try:
            tickets: List[OpenedTickets] = await self.fetch_all(GET_OPENED_TICKETS)
            self.logger.debug(f"Retrieved {len(tickets)} open tickets")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve open tickets: {str(e)}")
            raise
