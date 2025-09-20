"""Memory service for Redis integration (async, robust, minimal round-trips)."""

import asyncio
import json
from typing import Dict, List, Optional, Any

import redis.asyncio as redis

from ..core.state import Message
from ..models.user import UserProfile
from ..utils import model_to_json, json_to_dict, utc_now_iso
from .base_service import BaseService, DatabaseMixin


class MemoryService(BaseService, DatabaseMixin):
    """Memory service for managing short-term and session memory (Redis)."""

    def __init__(self):
        super().__init__("MemoryService")
        self.redis_client: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None

    # ---- Connection ---------------------------------------------------------

    async def connect(self):
        """Create a shared connection pool and client."""
        try:
            self._pool = redis.ConnectionPool.from_url(
                self.settings.redis_url,
                password=self.settings.redis_password or None,
                decode_responses=True,
            )
            self.redis_client = redis.Redis(connection_pool=self._pool)
            await self.redis_client.ping()
            self.logger.info("Connected to Redis")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close the client/pool gracefully."""
        try:
            if self.redis_client:
                await self.redis_client.close()
            if self._pool:
                await self._pool.disconnect()
            self.logger.info("Disconnected from Redis")
        except Exception as e:
            self.logger.warning(f"Error during Redis disconnect: {e}")

    async def _ensure(self) -> bool:
        """Ensure we have a usable client (lazy connect if needed)."""
        if self.redis_client is None:
            try:
                await self.connect()
            except Exception:
                return False
        return True

    # ---- Keys ---------------------------------------------------------------

    @staticmethod
    def _k_session(session_id: str) -> str: return f"session:{session_id}"
    @staticmethod
    def _k_context(session_id: str) -> str: return f"context:{session_id}"
    @staticmethod
    def _k_messages(session_id: str) -> str: return f"messages:{session_id}"
    @staticmethod
    def _k_history(conv_id: str) -> str: return f"conversation_history:{conv_id}"
    @staticmethod
    def _k_profile(user_id: str) -> str: return f"profile:{user_id}"
    @staticmethod
    def _k_agent(session_id: str, agent_type: str) -> str: return f"agent_state:{session_id}:{agent_type}"
    @staticmethod
    def _k_user_session(user_id: str) -> str: return f"user_session:{user_id}"

    # ---- Session Management -------------------------------------------------

    async def create_session(self, session_id: str, user_id: str) -> None:
        if not await self._ensure():
            return
        try:
            data = {
                "user_id": user_id,
                "created_at": _utc_now_iso(),
                "last_activity": _utc_now_iso(),
            }
            key = self._k_session(session_id)
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.hset(key, mapping=data)
                pipe.expire(key, self.settings.short_term_memory_ttl)
                await pipe.execute()
            self.logger.info(f"Created session: {session_id}")
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not await self._ensure():
            return None
        try:
            data = await self.redis_client.hgetall(self._k_session(session_id))
            return data or None
        except Exception as e:
            self.logger.error(f"Error getting session: {e}")
            return None

    async def update_session_activity(self, session_id: str) -> None:
        if not await self._ensure():
            return
        try:
            key = self._k_session(session_id)
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.hset(key, "last_activity", _utc_now_iso())
                pipe.expire(key, self.settings.short_term_memory_ttl)
                await pipe.execute()
        except Exception as e:
            self.logger.error(f"Error updating session activity: {e}")

    # ---- Conversation Context ----------------------------------------------

    async def store_conversation_context(self, session_id: str, context: Dict[str, Any]) -> None:
        if not await self._ensure():
            return
        try:
            key = self._k_context(session_id)
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.set(key, json.dumps(context, default=str))
                pipe.expire(key, self.settings.short_term_memory_ttl)
                await pipe.execute()
            self.logger.info(f"Stored conversation context for session: {session_id}")
        except Exception as e:
            self.logger.error(f"Error storing conversation context: {e}")

    async def get_conversation_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not await self._ensure():
            return None
        try:
            raw = await self.redis_client.get(self._k_context(session_id))
            return json_to_dict(raw) or None
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {e}")
            return None

    async def update_conversation_context(self, session_id: str, updates: Dict[str, Any]) -> None:
        try:
            ctx = await self.get_conversation_context(session_id) or {}
            ctx.update(updates or {})
            await self.store_conversation_context(session_id, ctx)
        except Exception as e:
            self.logger.error(f"Error updating conversation context: {e}")

    # ---- Message History (short-term) --------------------------------------

    async def store_message(self, session_id: str, message: Message) -> None:
        if not await self._ensure():
            return
        try:
            key = self._k_messages(session_id)
            raw = model_to_json(message)
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.lpush(key, raw)
                pipe.ltrim(key, 0, self.settings.conversation_context_limit - 1)
                pipe.expire(key, self.settings.short_term_memory_ttl)
                await pipe.execute()
            self.logger.info(f"Stored message for session: {session_id}")
        except Exception as e:
            self.logger.error(f"Error storing message: {e}")

    async def get_recent_messages(self, session_id: str, limit: int = 10) -> List[Message]:
        if not await self._ensure():
            return []
        try:
            key = self._k_messages(session_id)
            rows = await self.redis_client.lrange(key, 0, max(0, limit - 1))
            out: List[Message] = []
            for s in rows:
                try:
                    out.append(Message(**json_to_dict(s)))
                except Exception as ex:
                    self.logger.warning(f"Error parsing message: {ex}")
            return out
        except Exception as e:
            self.logger.error(f"Error getting recent messages: {e}")
            return []

    # ---- Conversation History Cache ----------------------------------------

    async def cache_conversation_history(self, conversation_id: str, messages: List[Message]) -> None:
        if not await self._ensure():
            return
        try:
            key = self._k_history(conversation_id)
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.delete(key)
                # store newest last → we’ll LPUSH reversed for fast prepend later
                for msg in messages:
                    pipe.rpush(key, model_to_json(msg))
                pipe.ltrim(key, -10, -1)  # keep last 10
                pipe.expire(key, self.settings.short_term_memory_ttl)
                await pipe.execute()
            self.logger.info(f"Cached {len(messages)} messages for conversation: {conversation_id}")
        except Exception as e:
            self.logger.error(f"Error caching conversation history: {e}")

    async def get_cached_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Message]:
        if not await self._ensure():
            return []
        try:
            key = self._k_history(conversation_id)
            # get last N (chronological order)
            rows = await self.redis_client.lrange(key, -limit, -1)
            out: List[Message] = []
            for s in rows:
                try:
                    out.append(Message(**json_to_dict(s)))
                except Exception as ex:
                    self.logger.warning(f"Error parsing cached message: {ex}")
            self.logger.info(f"Retrieved {len(out)} cached messages for conversation: {conversation_id}")
            return out
        except Exception as e:
            self.logger.error(f"Error getting cached conversation history: {e}")
            return []

    async def add_message_to_conversation_cache(self, conversation_id: str, message: Message) -> None:
        if not await self._ensure():
            return
        try:
            key = self._k_history(conversation_id)
            raw = model_to_json(message)
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.rpush(key, raw)  # keep chronological order
                pipe.ltrim(key, -10, -1)
                pipe.expire(key, self.settings.short_term_memory_ttl)
                await pipe.execute()
            self.logger.info(f"Added message to conversation cache: {conversation_id}")
        except Exception as e:
            self.logger.error(f"Error adding message to conversation cache: {e}")

    # ---- User Profile Cache -------------------------------------------------

    async def cache_user_profile(self, user_id: str, profile: UserProfile) -> None:
        if not await self._ensure():
            return
        try:
            key = self._k_profile(user_id)
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.set(key, model_to_json(profile))
                pipe.expire(key, self.settings.short_term_memory_ttl)
                await pipe.execute()
            self.logger.info(f"Cached user profile: {user_id}")
        except Exception as e:
            self.logger.error(f"Error caching user profile: {e}")

    async def get_cached_user_profile(self, user_id: str) -> Optional[UserProfile]:
        if not await self._ensure():
            return None
        try:
            raw = await self.redis_client.get(self._k_profile(user_id))
            if not raw:
                return None
            return UserProfile(**json_to_dict(raw))
        except Exception as e:
            self.logger.error(f"Error getting cached user profile: {e}")
            return None

    # ---- Agent State --------------------------------------------------------

    async def store_agent_state(self, session_id: str, agent_type: str, state: Dict[str, Any]) -> None:
        if not await self._ensure():
            return
        try:
            key = self._k_agent(session_id, agent_type)
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.set(key, json.dumps(state, default=str))
                pipe.expire(key, self.settings.short_term_memory_ttl)
                await pipe.execute()
            self.logger.info(f"Stored agent state: {agent_type} (session {session_id})")
        except Exception as e:
            self.logger.error(f"Error storing agent state: {e}")

    async def get_agent_state(self, session_id: str, agent_type: str) -> Optional[Dict[str, Any]]:
        if not await self._ensure():
            return None
        try:
            raw = await self.redis_client.get(self._k_agent(session_id, agent_type))
            return json_to_dict(raw) or None
        except Exception as e:
            self.logger.error(f"Error getting agent state: {e}")
            return None

    # ---- Temporary Data -----------------------------------------------------

    async def store_temp_data(self, key: str, data: Any, ttl: int = 300) -> None:
        if not await self._ensure():
            return
        try:
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.set(key, json.dumps(data, default=str))
                pipe.expire(key, ttl)
                await pipe.execute()
            self.logger.info(f"Stored temporary data: {key}")
        except Exception as e:
            self.logger.error(f"Error storing temporary data: {e}")

    async def get_temp_data(self, key: str) -> Optional[Any]:
        if not await self._ensure():
            return None
        try:
            raw = await self.redis_client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            self.logger.error(f"Error getting temporary data: {e}")
            return None

    # ---- Cache Management ---------------------------------------------------

    async def clear_session_cache(self, session_id: str) -> None:
        if not await self._ensure():
            return
        try:
            patterns = [
                self._k_session(session_id),
                self._k_context(session_id),
                self._k_messages(session_id),
                f"agent_state:{session_id}:*",
                f"conversation_history:{session_id}*",  # if conv_id == session_id in your app
            ]
            to_delete = []
            for p in patterns:
                async for key in self.redis_client.scan_iter(p):
                    to_delete.append(key)
            if to_delete:
                await self.redis_client.delete(*to_delete)
            self.logger.info(f"Cleared cache for session: {session_id} (keys: {len(to_delete)})")
        except Exception as e:
            self.logger.error(f"Error clearing session cache: {e}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        if not await self._ensure():
            return {}
        try:
            info = await self.redis_client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {}

    # ---- User Session (Auth helper) ----------------------------------------

    async def store_user_session(self, session_data: Dict[str, Any]) -> None:
        if not await self._ensure():
            return
        try:
            user_id = session_data.get("user_id")
            if not user_id:
                raise ValueError("user_id is required for session storage")
            key = self._k_user_session(user_id)
            async with self.redis_client.pipeline(transaction=False) as pipe:
                pipe.hset(key, mapping=session_data)
                pipe.expire(key, self.settings.short_term_memory_ttl)
                await pipe.execute()
            self.logger.info(f"Stored user session: {user_id}")
        except Exception as e:
            self.logger.error(f"Error storing user session: {e}")

    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not await self._ensure():
            return None
        try:
            data = await self.redis_client.hgetall(self._k_user_session(user_id))
            return data or None
        except Exception as e:
            self.logger.error(f"Error getting user session: {e}")
            return None

    async def delete_user_session(self, user_id: str) -> None:
        if not await self._ensure():
            return
        try:
            await self.redis_client.delete(self._k_user_session(user_id))
            self.logger.info(f"Deleted user session: {user_id}")
        except Exception as e:
            self.logger.error(f"Error deleting user session: {e}")
