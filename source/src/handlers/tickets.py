import re
import traceback

from typing import List, Dict, Any, Optional, Union
from loguru import logger

from src.localization.queries import (
    CREATE_TABLE_TICKETS,
    CREATE_TABLE_TICKET_MESSAGES,
    CREATE_TABLE_BANNED_USERS,
    CREATE_TABLE_HANDLERS,
    CREATE_TABLE_USERS_DETAILS,
    GET_ALL_TABLES,
    INSERT_USER_FOR_HANDLER,
    DELETE_USER_FROM_HANDLER,
    GET_ALL_HANDLERS,
    CHECK_USER_IS_HANDLER,
    CREATE_TICKET,
    ADDED_USER_DETAILS,
    ADDED_TICKET_MESSAGE,
    UPDATE_USER_DETAILS,
    GET_USER_DETAILS_BY_ID,
    GET_TICKET_BY_ID,
    CLOSED_TICKET,
    GET_USER_TICKETS,
    GET_CLOSED_TICKETS,
    GET_OPENED_TICKETS,
    GET_TICKET_MESSAGES,
    GET_USER_BY_USERNAME,
    GET_ALL_TICKET_MESSAGES,
    GET_HISTORY_USER_TICKETS,
    GET_HISTORY_HANDLER_TICKETS,
    GET_CLOSED_TICKETS_BY_TICKETID
)
from src.types.tickets import (
    UserTickets, 
    ClosedTicket, 
    OpenedTickets,
    TicketMessages,
    HistoryHandlerTickets, 
    Handlers
)
from src.utility.utility import generate_id, curtime, epodate
from src.library.database import BtAioMysql


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
    
    async def _query_time_range(self, column: str, time_range: str):
        if not isinstance(column, str) and not isinstance(time_range, str):
            raise TypeError("Both 'column' and 'time_range' must be strings.")
        
        if time_range == 'today':
            date_filter = f"AND DATE({column}) = CURDATE()"
        elif time_range == 'weekly':
            date_filter = f"AND YEARWEEK({column}, 1) = YEARWEEK(CURDATE(), 1)"
        elif time_range == 'monthly':
            date_filter = f"AND YEAR({column}) = YEAR(CURDATE()) AND MONTH({column}) = MONTH(CURDATE())"
        elif time_range == 'yearly':
            date_filter = f"AND YEAR({column}) = YEAR(CURDATE())"
        else:
            raise ValueError("Invalid time range. Use 'today', 'weekly', 'monthly', or 'yearly'.")
        return date_filter
    
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
                    CREATE_TABLE_HANDLERS,
                    CREATE_TABLE_USERS_DETAILS
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
    
    async def registration_user(self, id: int, is_bot: bool, first_name: str, username: str, last_name: str):
        """
        Registers a new user in the database.

        Args:
            id (int): The unique identifier for the user.
            is_bot (bool): Whether the user is a bot.
            first_name (str): The first name of the user.
            username (str): The username of the user.
            last_name (str): The last name of the user.

        Returns:
            bool: True if the user was successfully registered, False otherwise.

        Raises:
            Exception: If any error occurs during the database operation.
        """
        try:
            affected_rows = await self.execute(
                ADDED_USER_DETAILS, (id, is_bot, first_name, username, last_name,)
            )
            self.logger.info(f"Added user {username} with id {id}")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to add user {username}: {str(e)}")
            raise
    
    async def update_user(self, id: int, first_name: str, username: str, last_name: str):
        """
        Updates the details of an existing user in the database.

        Args:
            id (int): The unique identifier for the user.
            first_name (str): The updated first name of the user.
            username (str): The updated username of the user.
            last_name (str): The updated last name of the user.

        Returns:
            bool: True if the user was successfully updated, False otherwise.

        Raises:
            Exception: If any error occurs during the database operation.
        """
        try:
            affected_rows = await self.execute(
                UPDATE_USER_DETAILS, (id, first_name, username, last_name,)
            )
            self.logger.info(f"Update user with id {id}")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to update user with id {id}: {str(e)}")
            raise
    
    async def get_userid_by_username(self, username: str):
        """
        Retrieves a user's ID based on their username.

        Args:
            username (str): The username of the user.

        Returns:
            Any: The user ID if found, or None if no user is found.

        Raises:
            Exception: If any error occurs during the database operation.
        """
        try:
            result = await self.fetch_one(GET_USER_BY_USERNAME, (username,))
            return result
        except Exception as e:
            self.logger.error(f"Failed to get userid with {username}: {str(e)}")
            raise
    
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
    
    async def deregistration_handler(self, user_id: int) -> bool:
        """Deregister a new support handler in the system.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            True if deregistration was successful
        """
        try:
            affected_rows = await self.execute(DELETE_USER_FROM_HANDLER, (user_id,))
            self.logger.info(f"Deregistered handler: (ID: {user_id})")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to deregister handler (ID: {user_id}): {str(e)}")
            raise

    async def get_all_handlers(self) -> List[Handlers]:
        """Retrieve all registered support handlers.
        
        Returns:
            List of handler records
        """
        try:
            handlers = [
                Handlers(**handler) for handler in
                await self.fetch_all(GET_ALL_HANDLERS)
            ]
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
            message_from: str,
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
                (ticket_id, user_id, message_id, message_chat_id, 
                 username, userfullname, message, message_from, datetime)
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
    
    async def get_handler_tickets_history(self, handler_id: int) -> List[HistoryHandlerTickets]:
        """
        Retrieve the ticket history for a given handler.

        Args:
            handler_id (int): The ID of the handler whose ticket history is to be retrieved.

        Returns:
            List[HistoryHandlerTickets]: A list of HistoryHandlerTickets objects representing the handler's ticket history.

        Raises:
            Exception: If an error occurs while fetching the ticket history.
        """
        try:
            result = await self.fetch_all(GET_HISTORY_HANDLER_TICKETS, (handler_id,))
            tickets = [
                HistoryHandlerTickets(**ticket)
                for ticket in result
            ]
            self.logger.debug(f"Retrieved {len(tickets)} tickets for handler user {handler_id}")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve tickets for user {handler_id}: {str(e)}")
            raise
    
    async def get_user_tickets_history(self, user_id: int, time_range: str = "today") -> List[HistoryHandlerTickets]:
        """
        Retrieve the ticket history for a given user.

        Args:
            user_id (int): The ID of the user whose ticket history is to be retrieved.
            time_range (str): Time Range

        Returns:
            List[HistoryHandlerTickets]: A list of HistoryHandlerTickets objects representing the user's ticket history.

        Raises:
            Exception: If an error occurs while fetching the ticket history.
        """
        try:
            time_range_query = await self._query_time_range("created_at", time_range)
            query = (
                f"{GET_HISTORY_USER_TICKETS} "
                f"{time_range_query} "
                "ORDER BY created_at DESC"
            )
            result = await self.fetch_all(query, (user_id,))
            tickets = [
                HistoryHandlerTickets(**ticket)
                for ticket in result
            ]
            self.logger.debug(f"Retrieved {len(tickets)} tickets for handler user {user_id}")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve tickets for user {user_id}: {str(e)}")
            raise

    async def get_user_details_by_id(self, id: int):
        """
        Retrieve user details by their ID.

        Args:
            id (int): The ID of the user whose details are to be retrieved.

        Returns:
            dict: A dictionary containing the user's details.

        Raises:
            Exception: If an error occurs while fetching the user details.
        """
        try:
            result = await self.fetch_one(GET_USER_DETAILS_BY_ID, (id,))
            return result
        except Exception as e:
            self.logger.error(f"Failed to retrieve user {id}: {str(e)}")
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
    
    async def get_closed_ticket_by_ticketid(self, id: str):
        """
        Retrieve a closed ticket by its ticket ID.

        Args:
            id (str): The ID of the closed ticket to be retrieved.

        Returns:
            ClosedTicket: An instance of the ClosedTicket object if found, otherwise None.

        Raises:
            Exception: If an error occurs while fetching the closed ticket.
        """
        try:
            result = await self.fetch_one(GET_CLOSED_TICKETS_BY_TICKETID, (id,))
            return ClosedTicket(**result) if result else result
        except Exception as e:
            self.logger.error(f"Failed to retrieve ticket {id}: {str(e)}")
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
    
    async def get_ticket_messages(
            self, 
            ticket_id: str, 
            user_id: Optional[int] = None, 
            is_handler: bool = False):
        """
        Retrieve messages associated with a given ticket.

        Parameters:
        - ticket_id (str): The unique identifier of the ticket.
        - user_id (Optional[int], optional): The ID of the user requesting the messages. Defaults to None.
        - is_handler (bool, optional): Indicates whether the user is a handler. Defaults to False.

        Returns:
        - List[TicketMessages]: A list of ticket messages. Returns an empty list if no messages are found or the user is unauthorized.

        Raises:
        - Exception: If an error occurs while retrieving the messages.
        """
        try:
            if user_id and not is_handler:
                result = await self.fetch_one(
                    GET_TICKET_MESSAGES, 
                    (ticket_id, user_id,)
                )
                if result.get("count") == 0:
                    return []
            
            messages = await self.fetch_all(
                GET_ALL_TICKET_MESSAGES, (ticket_id,)
            )
            
            if not messages:
                return []

            messages = [TicketMessages(**msg) for msg in messages]
            return messages
        except Exception as e:
            self.logger.error(f"Failed to retrieve tickets messages: {str(e)}")
            raise
    
    async def user_is_handler(self, user_id: str):
        """
        Check if a user is a handler.

        Parameters:
        - user_id (str): The unique identifier of the user.

        Returns:
        - bool: True if the user is a handler, False otherwise.

        Raises:
        - Exception: If an error occurs while verifying the handler status.
        """
        try:
            result = await self.fetch_one(CHECK_USER_IS_HANDLER, (user_id,))
            return result.__getitem__("COUNT(*)") > 0
        except Exception as e:
            self.logger.error(f"Failed to retrieve handler {user_id}: {str(e)}")
            raise