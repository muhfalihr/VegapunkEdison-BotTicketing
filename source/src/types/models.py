"""
ORM models for the ticket management system
"""
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.library.database import Model


class User(Model):
    """User model for the system"""
    _table_name = "users"
    _primary_key = "id"
    
    id: int
    role_id: int
    is_bot: bool
    first_name: str
    username: str
    last_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = datetime.now()


class Handler(Model):
    """Handler model representing support staff"""
    _table_name = "users"
    _primary_key = "id"
    
    id: int
    role_id: int
    first_name: str
    username: str
    is_active: bool
    
    @classmethod
    async def is_handler(cls, user_id: int) -> bool:
        """Check if a user is a handler"""
        result = await cls.objects.filter(id=user_id, role_id=2).exists()
        return result


class Ticket(Model):
    """Support ticket model"""
    _table_name = "tickets"
    _primary_key = "ticket_id"
    
    ticket_id: str
    user_id: int
    message_id: int
    message_chat_id: int
    username: str
    userfullname: str
    issue: str
    created_at: datetime
    status: str
    handler_id: Optional[int] = None
    handler_username: Optional[str] = None
    closed_at: Optional[datetime] = None
    
    @classmethod
    async def get_open_tickets(cls) -> List['Ticket']:
        """Get all open tickets"""
        return await cls.objects.filter(status="open").all()
    
    @classmethod
    async def get_user_tickets(cls, user_id: int) -> List['Ticket']:
        """Get all tickets for a specific user"""
        return await cls.objects.filter(user_id=user_id).all()
    
    @classmethod
    async def get_closed_tickets(cls, user_id: int = None) -> List['Ticket']:
        """Get closed tickets, optionally filtered by user"""
        query = cls.objects.filter(status="closed")
        if user_id:
            query = query.filter(user_id=user_id)
        return await query.all()
    
    async def close(self, handler_id: int, handler_username: str) -> None:
        """Close the ticket"""
        self.status = "closed"
        self.handler_id = handler_id
        self.handler_username = handler_username
        self.closed_at = datetime.now()
        
        await self.__class__.objects.filter(ticket_id=self.ticket_id).update(
            status=self.status,
            handler_id=self.handler_id,
            handler_username=self.handler_username,
            closed_at=self.closed_at
        )


class TicketMessage(Model):
    """Message associated with a ticket"""
    _table_name = "ticket_messages"
    _primary_key = "id"
    
    id: int
    ticket_id: str
    user_id: int
    message_id: int
    message_chat_id: int
    username: str
    userfullname: str
    message: str
    message_from: str
    timestamp: datetime
    
    @classmethod
    async def get_messages_for_ticket(cls, ticket_id: str) -> List['TicketMessage']:
        """Get all messages for a specific ticket"""
        return await cls.objects.filter(ticket_id=ticket_id).order_by("timestamp").all()
    
    @classmethod
    async def user_can_view_messages(cls, ticket_id: str, user_id: int, is_handler: bool = False) -> bool:
        """Check if a user can view messages for a ticket"""
        if is_handler:
            return True
        
        # Check if user is the ticket creator
        ticket = await Ticket.objects.get(ticket_id=ticket_id)
        return ticket and str(ticket.user_id) == str(user_id)


class BannedUser(Model):
    """Model for banned users"""
    _table_name = "banned_users"
    _primary_key = "user_id"
    
    user_id: int
    reason: str
    banned_by: int
    banned_at: datetime
    expires_at: Optional[datetime] = None
    
    @classmethod
    async def is_banned(cls, user_id: int) -> bool:
        """Check if a user is banned"""
        return await cls.objects.filter(user_id=user_id).exists()
