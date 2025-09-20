"""Database service for Supabase integration."""

from typing import Dict, List, Optional, Any
from supabase import create_client, Client
from datetime import datetime
from ..models.user import User, UserProfile, TaxDocument
from ..models.conversation import Conversation, Message
from .base_service import BaseService, DatabaseMixin


class DatabaseService(BaseService, DatabaseMixin):
    """Database service for managing data persistence."""
    
    def __init__(self):
        """Initialize database service."""
        super().__init__("DatabaseService")
        self.validate_required_settings("supabase_url", "supabase_service_key")
        
        # Use service role key for custom authentication to bypass RLS when needed
        self.client: Client = create_client(
            self.settings.supabase_url,
            self.settings.supabase_service_key
        )
    
    # ---------------------------
    # Users
    # ---------------------------
    async def create_user(self, user: User) -> User:
        return self.safe_database_operation(
            "create_user",
            self._create_user_operation,
            user
        )
    
    def _create_user_operation(self, user: User) -> User:
        """Internal operation for creating a user."""
        data = user.dict()
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].isoformat()
        if isinstance(data.get("updated_at"), datetime):
            data["updated_at"] = data["updated_at"].isoformat()
        result = self.client.table("users").insert(data).execute()
        return User(**result.data[0])
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            result = self.client.table("users").select("*").eq("email", email).execute()
            if result.data:
                return User(**result.data[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting user by email: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[User]:
        try:
            result = self.client.table("users").select("*").eq("id", user_id).execute()
            if result.data:
                return User(**result.data[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting user: {e}")
            return None
    
    async def update_user(self, user: User) -> User:
        try:
            data = user.dict()
            if isinstance(data.get("created_at"), datetime):
                data["created_at"] = data["created_at"].isoformat()
            if isinstance(data.get("updated_at"), datetime):
                data["updated_at"] = data["updated_at"].isoformat()
            result = self.client.table("users").update(data).eq("id", user.id).execute()
            self.logger.info(f"Updated user: {user.id}")
            return User(**result.data[0])
        except Exception as e:
            self.logger.error(f"Error updating user: {e}")
            raise
    
    # ---------------------------
    # User Profiles
    # ---------------------------
    async def create_user_profile(self, profile: UserProfile) -> UserProfile:
        try:
            data = profile.dict()
            for f in ("created_at", "updated_at", "last_interaction"):
                if f in data and isinstance(data[f], datetime):
                    data[f] = data[f].isoformat()
            result = self.client.table("user_profiles").insert(data).execute()
            self.logger.info(f"Created profile for user: {profile.user_id}")
            return UserProfile(**result.data[0])
        except Exception as e:
            self.logger.error(f"Error creating user profile: {e}")
            raise
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        try:
            result = self.client.table("user_profiles").select("*").eq("user_id", user_id).execute()
            if result.data:
                return UserProfile(**result.data[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting user profile: {e}")
            return None
    
    async def update_user_profile(self, profile: UserProfile) -> UserProfile:
        try:
            data = profile.dict()
            for f in ("created_at", "updated_at", "last_interaction"):
                if f in data and isinstance(data[f], datetime):
                    data[f] = data[f].isoformat()
            result = self.client.table("user_profiles").update(data).eq("user_id", profile.user_id).execute()
            self.logger.info(f"Updated profile for user: {profile.user_id}")
            return UserProfile(**result.data[0])
        except Exception as e:
            self.logger.error(f"Error updating user profile: {e}")
            raise
    
    async def create_or_update_user_profile(self, profile_data: Dict[str, Any]) -> Optional[UserProfile]:
        try:
            user_id = profile_data.get("user_id")
            if not user_id:
                self.logger.error("User ID is required for profile creation/update")
                return None
            
            existing = await self.get_user_profile(user_id)
            now_iso = datetime.utcnow().isoformat()

            if existing:
                profile_data["updated_at"] = now_iso
                result = self.client.table("user_profiles").update(profile_data).eq("user_id", user_id).execute()
                self.logger.info(f"Updated profile for user: {user_id}")
            else:
                profile_data.setdefault("created_at", now_iso)
                profile_data.setdefault("updated_at", now_iso)
                result = self.client.table("user_profiles").insert(profile_data).execute()
                self.logger.info(f"Created profile for user: {user_id}")
            
            if result.data:
                return UserProfile(**result.data[0])
            return None
        except Exception as e:
            self.logger.error(f"Error creating/updating user profile: {e}")
            raise
    
    # ---------------------------
    # Conversations
    # ---------------------------
    async def create_conversation(self, conversation: Conversation) -> Conversation:
        try:
            data = conversation.dict(exclude={"messages", "context", "status"})
            for f in ("created_at", "updated_at"):
                if f in data and isinstance(data[f], datetime):
                    data[f] = data[f].isoformat()
            result = self.client.table("conversations").insert(data).execute()
            self.logger.info(f"Created conversation: {conversation.id}")
            db = result.data[0]
            db["context"] = {}
            db["status"] = "active"
            db["messages"] = []
            return Conversation(**db)
        except Exception as e:
            self.logger.error(f"Error creating conversation: {e}")
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        try:
            result = self.client.table("conversations").select("*").eq("id", conversation_id).execute()
            if result.data:
                db = result.data[0]
                db["context"] = db.get("context") or {}
                db["status"] = db.get("status") or "active"
                db["messages"] = []
                return Conversation(**db)
            return None
        except Exception as e:
            self.logger.error(f"Error getting conversation: {e}")
            return None
    
    async def get_user_conversations(self, user_id: str, limit: int = 10) -> List[Conversation]:
        try:
            result = self.client.table("conversations").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            out: List[Conversation] = []
            for conv in result.data:
                conv["context"] = conv.get("context") or {}
                conv["status"] = conv.get("status") or "active"
                conv["messages"] = []
                out.append(Conversation(**conv))
            return out
        except Exception as e:
            self.logger.error(f"Error getting user conversations: {e}")
            return []
    
    async def update_conversation(self, conversation: Conversation) -> Conversation:
        try:
            data = conversation.dict(exclude={"messages", "context", "status"})
            for f in ("created_at", "updated_at"):
                if f in data and isinstance(data[f], datetime):
                    data[f] = data[f].isoformat()
            result = self.client.table("conversations").update(data).eq("id", conversation.id).execute()
            self.logger.info(f"Updated conversation: {conversation.id}")
            db = result.data[0]
            db["context"] = conversation.context
            db["status"] = conversation.status
            db["messages"] = conversation.messages
            return Conversation(**db)
        except Exception as e:
            self.logger.error(f"Error updating conversation: {e}")
            raise
    
    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        try:
            self.client.table("conversations").update({"title": title}).eq("id", conversation_id).execute()
            self.logger.info(f"Updated conversation title: {conversation_id} -> {title}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating conversation title: {e}")
            return False
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        try:
            self.client.table("conversations").delete().eq("id", conversation_id).execute()
            self.logger.info(f"Deleted conversation: {conversation_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting conversation: {e}")
            return False
    
    # ---------------------------
    # Messages
    # ---------------------------
    async def add_message(self, message: Message) -> Message:
        try:
            data = message.dict()
            self.logger.info(f"Adding message data: {data}")

            if "conversation_id" not in data or not data["conversation_id"]:
                data["conversation_id"] = message.conversation_id

            if "timestamp" in data and isinstance(data["timestamp"], datetime):
                data["timestamp"] = data["timestamp"].isoformat()

            result = self.client.table("messages").insert(data).execute()
            self.logger.info(f"Added message: {message.id}, result: {result.data[0] if result.data else 'No data'}")
            return Message(**result.data[0])
        except Exception as e:
            self.logger.error(f"Error adding message: {e}")
            raise
    
    async def get_conversation_messages(self, conversation_id: str, limit: int = 50) -> List[Message]:
        try:
            result = self.client.table("messages").select("*").eq("conversation_id", conversation_id).order("timestamp").limit(limit).execute()
            return [Message(**m) for m in result.data]
        except Exception as e:
            self.logger.error(f"Error getting conversation messages: {e}")
            return []
    
    async def delete_message(self, message_id: str) -> bool:
        try:
            self.client.table("messages").delete().eq("id", message_id).execute()
            self.logger.info(f"Deleted message: {message_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting message: {e}")
            return False
    
    # ---------------------------
    # User Learning (single-row per user)
    # ---------------------------
    async def create_or_update_user_learning(self, user_id: str, learning_summary: str) -> Dict[str, Any]:
        try:
            import uuid
            existing = await self.get_user_learning(user_id)
            now_iso = datetime.utcnow().isoformat()

            if existing:
                update_data = {"value": learning_summary, "updated_at": now_iso}
                result = self.client.table("user_learning").update(update_data).eq("user_id", user_id).eq("learning_type", "user_profile_summary").execute()
                self.logger.info(f"Updated user learning summary for user: {user_id}")
                return result.data[0] if result.data else {**existing, **update_data}
            else:
                learning_data = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "learning_type": "user_profile_summary",
                    "key": "comprehensive_summary",
                    "value": learning_summary,
                    "confidence": 0.9,
                    "source": "conversation_analysis",
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }
                result = self.client.table("user_learning").insert(learning_data).execute()
                self.logger.info(f"Created user learning summary for user: {user_id}")
                return result.data[0] if result.data else learning_data
        except Exception as e:
            self.logger.error(f"Error creating/updating user learning: {e}")
            raise
    
    async def get_user_learning(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.client.table("user_learning").select("*").eq("user_id", user_id).eq("learning_type", "user_profile_summary").execute()
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(f"Error getting user learning: {e}")
            return None
    
    async def delete_user_learning(self, user_id: str) -> bool:
        try:
            self.client.table("user_learning").delete().eq("user_id", user_id).eq("learning_type", "user_profile_summary").execute()
            self.logger.info(f"Deleted user learning for user: {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting user learning: {e}")
            return False
    
    # ---------------------------
    # Tax Documents (used by ExpenseTools)
    # ---------------------------
    async def create_tax_document(self, document: TaxDocument) -> TaxDocument:
        try:
            data = document.dict()
            for f in ("created_at", "updated_at"):
                if f in data and isinstance(data[f], datetime):
                    data[f] = data[f].isoformat()
            result = self.client.table("tax_documents").insert(data).execute()
            self.logger.info(f"Created tax document: {document.id}")
            return TaxDocument(**result.data[0])
        except Exception as e:
            self.logger.error(f"Error creating tax document: {e}")
            raise
    
    async def get_tax_document(self, document_id: str) -> Optional[TaxDocument]:
        """(New) Fetch a single tax document by ID."""
        try:
            result = self.client.table("tax_documents").select("*").eq("id", document_id).execute()
            if result.data:
                return TaxDocument(**result.data[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting tax document: {e}")
            return None
    
    async def get_user_tax_documents(self, user_id: str, year: Optional[int] = None) -> List[TaxDocument]:
        try:
            query = self.client.table("tax_documents").select("*").eq("user_id", user_id)
            if year:
                query = query.eq("year", year)
            result = query.order("created_at", desc=True).execute()
            return [TaxDocument(**doc) for doc in result.data]
        except Exception as e:
            self.logger.error(f"Error getting tax documents: {e}")
            return []
    
    async def update_tax_document(self, document: TaxDocument) -> Optional[TaxDocument]:
        try:
            payload = {
                "document_type": document.document_type,
                "year": document.year,
                "amount": document.amount,
                "description": document.description,
                "file_path": document.file_path,
                "metadata": document.metadata,
                "updated_at": datetime.utcnow().isoformat(),
            }
            result = self.client.table("tax_documents").update(payload).eq("id", document.id).execute()
            if result.data:
                return TaxDocument(**result.data[0])
            return None
        except Exception as e:
            self.logger.error(f"Error updating tax document: {e}")
            return None

    async def delete_tax_document(self, document_id: str) -> bool:
        """(New) Delete a tax document by ID (used by ExpenseTools.delete_expense)."""
        try:
            self.client.table("tax_documents").delete().eq("id", document_id).execute()
            self.logger.info(f"Deleted tax document: {document_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting tax document: {e}")
            return False
    
    # ---------------------------
    # Analytics / Insights
    # ---------------------------
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get user insights and analytics (safe `.in_()` usage, no subqueries)."""
        try:
            # Conversations
            conv_res = self.client.table("conversations").select("id", count="exact").eq("user_id", user_id).execute()
            conversation_count = conv_res.count or 0
            conv_ids = [c["id"] for c in (conv_res.data or [])]

            # Messages across user's conversations
            if conv_ids:
                msg_res = self.client.table("messages").select("id", count="exact").in_("conversation_id", conv_ids).execute()
                message_count = msg_res.count or 0

                last_msg = (
                    self.client.table("messages")
                    .select("*")
                    .in_("conversation_id", conv_ids)
                    .order("timestamp", desc=True)
                    .limit(1)
                    .execute()
                )
                last_activity = (last_msg.data[0]["timestamp"] if last_msg.data else None)
            else:
                message_count = 0
                last_activity = None

            # Documents
            doc_res = self.client.table("tax_documents").select("id", count="exact").eq("user_id", user_id).execute()
            document_count = doc_res.count or 0

            return {
                "conversation_count": conversation_count,
                "message_count": message_count,
                "document_count": document_count,
                "last_activity": last_activity,
            }
        except Exception as e:
            self.logger.error(f"Error getting user insights: {e}")
            return {"conversation_count": 0, "message_count": 0, "document_count": 0, "last_activity": None}
