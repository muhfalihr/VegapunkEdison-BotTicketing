import re
import traceback
import asyncio

from typing import List, Dict, Any, Optional, Union
from loguru import logger
from datetime import datetime

from src.localization.queries import (
    CREATE_TABLE_ROLES,
    INITIALIZE_ROLES,
    INITIALIZE_SYSTEM_USER,
    CREATE_TABLE_USERS,
    CREATE_TABLE_TICKETS,
    CREATE_TABLE_TICKET_MESSAGES,
    CREATE_TABLE_BANNED_USERS,
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
from src.library.redis import BtRedis


class HandlerTickets(BtAioMysql):
    """Handles database operations related to support ticket handlers and messages."""
    
    def __init__(self, pool_size: int = 10, connect_timeout: int = 10):
        """Initialize the handler store.
        
        Args:
            pool_size: Maximum number of connections in the pool
            connect_timeout: Connection timeout in seconds
        """
        super().__init__(pool_size=pool_size, connect_timeout=connect_timeout)
        self.logger = logger
        self.redis: Optional[BtRedis] = None
        self.session_ttl: int = 86400 # Default 24h

    def set_redis(self, redis_client: BtRedis, session_ttl: int):
        self.redis = redis_client
        self.session_ttl = session_ttl

    async def _update_ticket_session(self, ticket_id: str):
        """
        Update or extend ticket session in Redis.
        Session is extended by resetting TTL to session_ttl.
        """
        if not self.redis:
            return
        
        try:
            key = f"ticket_session:{ticket_id}"
            # Logic: 24 - (sisa waktu sesi) basically means resetting to 24 hours
            # because if we add (24 - sisa), it becomes sisa + 24 - sisa = 24.
            await self.redis.client.set(key, "active", ex=self.session_ttl)
            self.logger.debug(f"Extended session for ticket {ticket_id}")
        except Exception as e:
            self.logger.error(f"Failed to update ticket session in Redis: {e}")

    async def check_and_close_expired_tickets(self, timezone: str):
        """
        Check database for open tickets and close those that don't have an active session in Redis.
        """
        if not self.redis:
            return

        try:
            open_tickets = await self.get_opened_tickets()
            for ticket in open_tickets:
                key = f"ticket_session:{ticket.ticket_id}"
                is_active = await self.redis.client.exists(key)
                
                if not is_active:
                    self.logger.info(f"Ticket {ticket.ticket_id} session expired. Auto-closing...")
                    # Use a system handler ID or 0 for auto-close
                    await self.close_ticket(
                        ticket_id=ticket.ticket_id,
                        handler_id=0,
                        handler_username="SYSTEM_AUTO_CLOSE",
                        timezone=timezone
                    )
        except Exception as e:
            self.logger.error(f"Error during auto-closing expired tickets: {e}")
    
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
    
    async def setup_tables(self, database: str) -> None:
        """
        Create required tables for the handler system if they do not exist.
        """
        try:
            existing_tables = await self.fetch_all(GET_ALL_TABLES, (database,))
            existing_table_names = [table.get("TABLE_NAME") for table in existing_tables]
            self.logger.info(existing_table_names)

            tables_to_create = [
                table_def for table_def in [
                    CREATE_TABLE_ROLES,
                    CREATE_TABLE_USERS,
                    CREATE_TABLE_TICKETS, 
                    CREATE_TABLE_TICKET_MESSAGES, 
                    CREATE_TABLE_BANNED_USERS
                ]
                if self._extract_table_name(table_def) not in existing_table_names
            ]

            if tables_to_create:
                await self.create_tables(table_definitions=tables_to_create)
                self.logger.info(f"Created {len(tables_to_create)} new handler system tables")
            else:
                self.logger.info("All required tables already exist")

            # Always ensure roles and system user are initialized
            await self.execute(INITIALIZE_ROLES)
            await self.execute(INITIALIZE_SYSTEM_USER)
            self.logger.info("Initialized roles and system user")

        except Exception as e:
            self.logger.error(f"Failed to setup handler system tables: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    async def initialize_admins(self, admin_ids: List[int]) -> None:
        """
        Ensure all admin IDs from config are registered in the users table with admin role.
        """
        try:
            for admin_id in admin_ids:
                # Use a raw query with ON DUPLICATE KEY UPDATE to ensure role_id is set to 3
                # even if the user already exists with a different role.
                query = """
                INSERT INTO users (id, role_id, first_name, username, is_bot)
                VALUES (%s, 3, 'ADMIN', 'CONFIG_ADMIN', 0)
                ON DUPLICATE KEY UPDATE role_id = 3
                """
                await self.execute(query, (admin_id,))
                self.logger.info(f"Initialized admin ID {admin_id} from config")
        except Exception as e:
            self.logger.error(f"Failed to initialize admins: {e}")
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
    
    async def register_user(self, id: int, first_name: str, username: str, role_id: int, last_name: str = None, is_bot: bool = False):
        """
        Register or update a user with specific details and role.
        """
        try:
            query = """
            INSERT INTO users (id, role_id, first_name, username, last_name, is_bot)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                role_id = VALUES(role_id),
                first_name = VALUES(first_name),
                username = VALUES(username),
                last_name = VALUES(last_name)
            """
            await self.execute(query, (id, role_id, first_name, username, last_name, is_bot))
            self.logger.info(f"Registered/Updated user {id} (@{username}) with role_id {role_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register user {id}: {e}")
            raise

    async def registration_user(self, id: int, is_bot: bool, first_name: str, username: str, last_name: str):
        try:
            await User.objects.create(
                id=id, 
                is_bot=is_bot, 
                first_name=first_name, 
                username=username, 
                last_name=last_name,
                role_id=1 # Default to user role
            )
            self.logger.info(f"Added user {username} with id {id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add user {username}: {str(e)}")
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

    async def ensure_user(self, id: int, is_bot: bool, first_name: str, username: str, last_name: str) -> int:
        """
        Check if user exists, update details if needed, and return their role_id.
        Registers new users if they don't exist.
        """
        try:
            # 1. Try to find user by ID
            user = await User.objects.filter(id=id).get()
            
            if user:
                # Check for changes and update details if needed
                has_changes = (
                    user.first_name != first_name or
                    user.username != username or
                    user.last_name != last_name
                )
                
                if has_changes:
                    self.logger.info(f"User {id} details changed, updating...")
                    await self.update_user(id, first_name, username, last_name)
                
                return user.role_id

            # 2. If ID not found, try to find by username (if available)
            if username:
                user_by_username = await User.objects.filter(username=username).get()
                if user_by_username:
                    self.logger.info(f"User found by username @{username}, updating ID from {user_by_username.id} to {id}")
                    # Use raw query to update primary key and other fields
                    query = """
                    UPDATE users 
                    SET id = %s, first_name = %s, last_name = %s, is_bot = %s
                    WHERE username = %s
                    """
                    await self.execute(query, (id, first_name, last_name, is_bot, username))
                    return user_by_username.role_id

            # 3. User not found, register as new user
            self.logger.info(f"Registering new user {id} (@{username})")
            await self.registration_user(
                id=id,
                is_bot=is_bot,
                first_name=first_name,
                username=username,
                last_name=last_name
            )
            return 1 # Default role for new users
            
        except Exception as e:
            self.logger.error(f"Failed to ensure user {id}: {str(e)}")
            raise
    
    async def get_userid_by_username(self, username: str):
        try:
            user = await User.objects.filter(username=username).get()
            return {"id": user.id} if user else None
        except Exception as e:
            self.logger.error(f"Failed to get userid with {username}: {str(e)}")
            raise
    
    async def registration_handler(self, user_id: int, username: str, first_name: str = None, role_id: int = 2) -> bool:
        try:
            # Use register_user to ensure user is created or updated with the specified role and details
            return await self.register_user(
                id=user_id,
                first_name=first_name or "HANDLER",
                username=username,
                role_id=role_id,
                is_bot=False
            )
        except Exception as e:
            self.logger.error(f"Failed to register handler {username}: {str(e)}")
            raise
    
    async def deregistration_handler(self, user_id: int) -> bool:
        try:
            # Update user role back to user (role_id = 1)
            affected_rows = await User.objects.filter(id=user_id).update(role_id=1)
            self.logger.info(f"Deregistered handler: (ID: {user_id})")
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to deregister handler (ID: {user_id}): {str(e)}")
            raise

    async def get_user_role(self, username: str) -> int:
        """
        Retrieve the role_id for a specific user by username.
        """
        try:
            user = await User.objects.filter(username=username).get()
            return user.role_id if user else 1 # Default to user role
        except Exception as e:
            self.logger.error(f"Failed to get user role for @{username}: {str(e)}")
            return 1

    async def get_all_handlers(self) -> List[User]:
        try:
            handlers = await User.objects.filter(role_id=2).all()
            self.logger.debug(f"Retrieved {len(handlers)} handlers")
            return handlers
        except Exception as e:
            self.logger.error(f"Failed to retrieve handlers: {str(e)}")
            raise
        
    async def is_user_handler(self, user_id: int) -> bool:
        try:
            return await User.is_handler(user_id)
        except Exception as e:
            self.logger.error(f"Failed to check handler status for user {user_id}: {str(e)}")
            raise
    
    async def create_ticket(
            self, ticket_id: str, user_id: int, message_id: int, message_chat_id: int,
            username: str, userfullname: str, issue: str, timestamp: int) -> bool:
        
        status = 'open'
        created_at = epodate(timestamp, store=True)

        try:
            # Ensure user exists in users table to satisfy foreign key constraint
            user_exists = await User.objects.filter(username=username).exists()
            if not user_exists:
                self.logger.info(f"User {user_id} (@{username}) not found in users table, registering...")
                try:
                    await self.registration_user(
                        id=user_id,
                        is_bot=False, # Default to False
                        first_name=userfullname, # Using userfullname for first_name if we don't have separate names
                        username=username,
                        last_name=None
                    )
                except Exception as reg_error:
                    self.logger.warning(f"Failed to register user {user_id} during ticket creation: {reg_error}")
                    # If registration fails, we still try to create the ticket
                    # as it might have been created by another process.

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
            
            # Start session in Redis
            await self._update_ticket_session(ticket_id)
            
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
            # Ensure user exists in users table to satisfy foreign key constraint
            user_exists = await User.objects.filter(id=user_id).exists()
            if not user_exists:
                self.logger.info(f"User {user_id} (@{username}) not found in users table, registering...")
                try:
                    await self.registration_user(
                        id=user_id,
                        is_bot=False, # Default to False
                        first_name=userfullname, # Using userfullname for first_name if we don't have separate names
                        username=username,
                        last_name=None
                    )
                except Exception as reg_error:
                    self.logger.warning(f"Failed to register user {user_id} during message addition: {reg_error}")
                    # If registration fails (e.g. race condition), we still try to create the message
                    # as it might have been created by another process in the meantime.

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
            
            # Extend session in Redis
            await self._update_ticket_session(ticket_id)
            
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
                Ticket(**ticket)
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
            self.logger.debug(f"Retrieved {len(tickets)} tickets for user {user_id}")
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
                
                # Clear Redis session if it exists
                if self.redis:
                    await self.redis.client.delete(f"ticket_session:{ticket_id}")
                
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to close ticket {ticket_id}: {str(e)}")
            raise
    
    async def get_closed_ticket_by_ticketid(self, id: str):
        try:
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
