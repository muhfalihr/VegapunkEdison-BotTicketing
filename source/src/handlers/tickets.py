import re
import traceback

from typing import List, Dict, Any, Optional, Union
from loguru import logger
from datetime import datetime

from src.localization.queries import (
    CREATE_TABLE_TICKETS,
    CREATE_TABLE_TICKET_MESSAGES,
    CREATE_TABLE_BANNED_USERS,
    CREATE_TABLE_HANDLERS,
    CREATE_TABLE_USERS_DETAILS,
    GET_ALL_TABLES,
    GET_HISTORY_USER_TICKETS,
    GET_HISTORY_HANDLER_TICKETS,
    GET_TICKET_MESSAGES,
    GET_ALL_TICKET_MESSAGES
)
from src.types.models import (
    User,
    Handler,
    Ticket,
    TicketMessage,
    BannedUser
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
        try:
            await User.objects.create(
                id=id, 
                is_bot=is_bot, 
                first_name=first_name, 
                username=username, 
                last_name=last_name
            )
            self.logger.info(f"Added user {username} with id {id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add user {username}: {str(e)}")
            # Fallback to update if duplicate entry? Or raise.
            # Assuming 'create' fails if duplicate. 
            # Original code used INSERT, which might fail on duplicate key.
            # But the original code didn't use INSERT IGNORE or ON DUPLICATE KEY UPDATE.
            raise
    
    async def update_user(self, id: int, first_name: str, username: str, last_name: str):
        try:
            affected_rows = await User.objects.filter(id=id).update(
                first_name=first_name, 
                username=username, 
                last_name=last_name
            )
            self.logger.info(f"Update user with id {id}")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to update user with id {id}: {str(e)}")
            raise
    
    async def get_userid_by_username(self, username: str):
        try:
            user = await User.objects.filter(username=username).get()
            return {"id": user.id} if user else None
        except Exception as e:
            self.logger.error(f"Failed to get userid with {username}: {str(e)}")
            raise
    
    async def registration_handler(self, user_id: int, username: str) -> bool:
        try:
            # Check if exists first to avoid error? Or use INSERT IGNORE equivalent.
            # Existing code used INSERT IGNORE query.
            # My simple ORM 'create' does INSERT.
            # I'll check existence first.
            if await Handler.objects.filter(user_id=user_id).exists():
                return False
            
            await Handler.objects.create(user_id=user_id, username=username)
            self.logger.info(f"Registered new handler: {username} (ID: {user_id})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register handler {username}: {str(e)}")
            raise
    
    async def deregistration_handler(self, user_id: int) -> bool:
        try:
            affected_rows = await Handler.objects.filter(user_id=user_id).delete()
            self.logger.info(f"Deregistered handler: (ID: {user_id})")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to deregister handler (ID: {user_id}): {str(e)}")
            raise

    async def get_all_handlers(self) -> List[Handler]:
        try:
            handlers = await Handler.objects.all()
            self.logger.debug(f"Retrieved {len(handlers)} handlers")
            return handlers
        except Exception as e:
            self.logger.error(f"Failed to retrieve handlers: {str(e)}")
            raise
        
    async def is_user_handler(self, user_id: int) -> bool:
        try:
            return await Handler.is_handler(user_id)
        except Exception as e:
            self.logger.error(f"Failed to check handler status for user {user_id}: {str(e)}")
            raise
    
    async def create_ticket(
            self, ticket_id: str, user_id: str, message_id: int, message_chat_id: int,
            username: str, userfullname: str, issue: str, timestamp: int) -> bool:
        
        status = 'open'
        created_at = epodate(timestamp, store=True)

        try:
            await Ticket.objects.create(
                ticket_id=ticket_id,
                user_id=user_id,
                message_id=message_id,
                message_chat_id=message_chat_id,
                username=username,
                userfullname=userfullname,
                issue=issue,
                created_at=created_at,
                status=status
            )
            self.logger.info(f"Created ticket {ticket_id} for user {username}")
            return True
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
        
        timestamp_dt = epodate(timestamp, store=True)

        try:
            await TicketMessage.objects.create(
                ticket_id=ticket_id,
                user_id=user_id,
                message_id=message_id,
                message_chat_id=message_chat_id,
                username=username,
                userfullname=userfullname,
                message=message,
                message_from=message_from,
                timestamp=timestamp_dt
            )
            self.logger.debug(f"Added message to ticket {ticket_id} by {username}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add message to ticket {ticket_id}: {str(e)}")
            raise

    async def get_ticket_by_id(self, ticket_id: str) -> Optional[Ticket]:
        try:
            ticket = await Ticket.objects.get(ticket_id=ticket_id)
            return ticket
        except Exception as e:
            self.logger.error(f"Failed to retrieve ticket {ticket_id}: {str(e)}")
            raise
    
    async def get_handler_tickets_history(self, handler_id: int) -> List[Ticket]:
        try:
            # Complex query, using fetch_all and manually converting to Ticket model
            result = await self.fetch_all(GET_HISTORY_HANDLER_TICKETS, (handler_id,))
            tickets = [
                Ticket(**ticket) # Note: This might fail if SQL returns fields not in Ticket model or misses some.
                                 # GET_HISTORY_HANDLER_TICKETS returns ticket_id, issue, status, created_at, closed_at, handler_username
                                 # Ticket model expects more fields if strict. But Model __init__ just sets kwargs.
                                 # So it acts as a partial model.
                for ticket in result
            ]
            self.logger.debug(f"Retrieved {len(tickets)} tickets for handler user {handler_id}")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve tickets for user {handler_id}: {str(e)}")
            raise
    
    async def get_user_tickets_history(self, user_id: int, time_range: str = "today") -> List[Ticket]:
        try:
            time_range_query = await self._query_time_range("created_at", time_range)
            query = (
                f"{GET_HISTORY_USER_TICKETS} "
                f"{time_range_query} "
                "ORDER BY created_at ASC"
            )
            result = await self.fetch_all(query, (user_id,))
            tickets = [
                Ticket(**ticket)
                for ticket in result
            ]
            self.logger.debug(f"Retrieved {len(tickets)} tickets for handler user {user_id}")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve tickets for user {user_id}: {str(e)}")
            raise

    async def get_user_details_by_id(self, id: int):
        try:
            # Return dict for compatibility as original returned dict
            user = await User.objects.get(id=id)
            return user.__dict__ if user else None
        except Exception as e:
            self.logger.error(f"Failed to retrieve user {id}: {str(e)}")
            raise
    
    async def close_ticket(self, ticket_id: str, handler_id: int, handler_username: str, timezone: str) -> bool:
        current_time = curtime(timezone)
        try:
            ticket = await Ticket.objects.get(ticket_id=ticket_id)
            if ticket:
                await ticket.close(handler_id, handler_username)
                self.logger.info(f"Ticket {ticket_id} closed by handler {handler_username}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to close ticket {ticket_id}: {str(e)}")
            raise
    
    async def get_closed_ticket_by_ticketid(self, id: str):
        try:
            # GET_CLOSED_TICKETS_BY_TICKETID returns subset.
            # Ticket.objects.get would return all columns but we want to filter by status='closed' too.
            # Original: SELECT ticket_id, handler_username, closed_at FROM tickets WHERE ticket_id = %s AND status = 'closed'
            ticket = await Ticket.objects.filter(ticket_id=id, status='closed').get()
            return ticket
        except Exception as e:
            self.logger.error(f"Failed to retrieve ticket {id}: {str(e)}")
            raise
    
    async def get_user_tickets(self, user_id: int) -> List[Ticket]:
        try:
            tickets = await Ticket.objects.filter(user_id=user_id, status='open').order_by("created_at DESC").all()
            self.logger.debug(f"Retrieved {len(tickets)} tickets for user {user_id}")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve tickets for user {user_id}: {str(e)}")
            raise

    async def get_closed_tickets(self, user_id: int) -> List[Ticket]:
        try:
            tickets = await Ticket.objects.filter(user_id=user_id, status='closed').order_by("closed_at DESC").all()
            self.logger.debug(f"Retrieved {len(tickets)} closed tickets for user {user_id}")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve closed tickets for user {user_id}: {str(e)}")
            raise
    
    async def get_opened_tickets(self) -> List[Ticket]:
        try:
            tickets = await Ticket.objects.filter(status='open').order_by("created_at DESC").all()
            self.logger.debug(f"Retrieved {len(tickets)} open tickets")
            return tickets
        except Exception as e:
            self.logger.error(f"Failed to retrieve open tickets: {str(e)}")
            raise
    
    async def get_ticket_messages(
            self, 
            ticket_id: str, 
            user_id: Optional[int] = None, 
            is_handler: bool = False) -> List[TicketMessage]:
        try:
            if user_id and not is_handler:
                # Check permission
                ticket = await Ticket.objects.get(ticket_id=ticket_id)
                if not ticket or int(ticket.user_id) != user_id:
                     return []
            
            messages = await TicketMessage.objects.filter(ticket_id=ticket_id).order_by("timestamp ASC").all()
            return messages
        except Exception as e:
            self.logger.error(f"Failed to retrieve tickets messages: {str(e)}")
            raise
    
    async def user_is_handler(self, user_id: str):
        try:
            return await Handler.is_handler(int(user_id))
        except Exception as e:
            self.logger.error(f"Failed to retrieve handler {user_id}: {str(e)}")
            raise
