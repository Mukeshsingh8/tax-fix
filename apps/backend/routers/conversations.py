"""Conversation management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from src.core.logging import get_logger

from ..dependencies import get_database_service, get_current_user
from src.services.database import DatabaseService
from src.models.auth import UserSession

logger = get_logger(__name__)
router = APIRouter(prefix="/conversation", tags=["conversations"])


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: UserSession = Depends(get_current_user),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get messages for a specific conversation."""
    try:
        # Get conversation to verify ownership
        conversation = await db_svc.get_conversation(conversation_id)
        if not conversation or conversation.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get messages
        messages = await db_svc.get_conversation_messages(conversation_id)
        
        return {
            "success": True,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                }
                for msg in messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation messages error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting conversation messages: {str(e)}"
        )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: UserSession = Depends(get_current_user),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Delete a conversation and all its messages."""
    try:
        # Get conversation to verify ownership
        conversation = await db_svc.get_conversation(conversation_id)
        if not conversation or conversation.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Delete all messages first
        messages = await db_svc.get_conversation_messages(conversation_id)
        for message in messages:
            await db_svc.delete_message(message.id)
        
        # Delete conversation
        await db_svc.delete_conversation(conversation_id)
        
        return {
            "success": True,
            "message": f"Deleted conversation and {len(messages)} messages"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting conversation: {str(e)}"
        )
