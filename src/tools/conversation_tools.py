"""Conversation monitoring and management tools for agents (refined + auto title updates)."""

from __future__ import annotations

import re
import time
from typing import Dict, Any, List, Optional, Iterable, Tuple
from datetime import datetime

from ..services.database import DatabaseService
from ..services.llm import LLMService
from ..services.memory import MemoryService  # optional, used if provided
from ..core.logging import get_logger
from ..core.config import get_settings
from ..utils import role_to_str, clean_title

logger = get_logger(__name__)
_settings = get_settings()


# -------------------------
# Helpers
# -------------------------

def _clean_title(s: str, max_len: int = 50) -> str:
    """Trim, strip quotes/newlines, enforce max length."""
    t = (s or "").strip().replace("\n", " ").replace("\r", " ")
    t = t.strip(' "\'')
    t = re.sub(r"\s+", " ", t)  # collapse whitespace
    if len(t) > max_len:
        t = t[: max_len - 1].rstrip() + "…"
    return t or "Tax Consultation"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-ZäöüÄÖÜß]+(?:-[a-zA-ZäöüÄÖÜß]+)?", text.lower())


def _score_keywords(text: str, vocab: Iterable[str]) -> List[Tuple[str, int]]:
    """Very simple frequency scoring with vocab filtering."""
    tokens = _tokenize(text)
    vocab_set = set(vocab)
    counts: Dict[str, int] = {}
    for tok in tokens:
        if tok in vocab_set:
            counts[tok] = counts.get(tok, 0) + 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))


def _title_from_keywords(keywords: List[str]) -> str:
    """Compose a compact title from top keywords."""
    if not keywords:
        return "Tax Consultation"
    top = keywords[:3]

    def cap(tok: str) -> str:
        return tok if tok.isupper() else tok.capitalize()

    return " • ".join(cap(t) for t in top)


# Canonical German/English tax vocabulary (extendable)
_TAX_VOCAB = [
    # English
    "tax", "income", "refund", "deduction", "credit", "pension", "expense", "return",
    "child", "allowance", "investment", "education", "business", "property", "mortgage",
    "home", "office", "equipment", "training", "class", "bracket", "rate", "vat",
    # German
    "einkommensteuer", "steuer", "steuererklärung", "werbungskosten", "sonderausgaben",
    "grundfreibetrag", "kinderfreibetrag", "steuerklasse", "steuerklassen", "mehrwertsteuer",
    "betriebsausgaben", "riester", "krankenversicherung", "pflegeversicherung",
    "beitragsbemessungsgrenze", "freibetrag", "vorsteuer", "umsatzsteuer",
]


class ConversationTools:
    """Tools for conversation monitoring and management."""

    def __init__(
        self,
        database_service: DatabaseService,
        llm_service: LLMService,
        memory_service: Optional[MemoryService] = None,
        *,
        auto_update_threshold: int = 6,
        auto_update_min_interval_sec: int = 900,  # 15 minutes
    ):
        """
        auto_update_threshold: update title every N messages (approx).
        auto_update_min_interval_sec: don't update more frequently than this wall time.
        """
        self.database = database_service
        self.llm_service = llm_service
        self.memory = memory_service  # optional
        self.default_model = getattr(_settings, "default_llm_model", None) or "groq"
        self.auto_update_threshold = max(3, int(auto_update_threshold))
        self.auto_update_min_interval_sec = max(60, int(auto_update_min_interval_sec))

    # --------------------------------------------------------------------- #
    # Titles
    # --------------------------------------------------------------------- #
    async def analyze_conversation_for_title(self, conversation_id: str, max_messages: int = 10) -> str:
        """
        Generate a concise conversation title using LLM with a robust fallback.
        - Keeps titles <= 50 chars.
        - Prioritizes main tax topic(s).
        """
        try:
            msgs = await self.database.get_conversation_messages(conversation_id, limit=max_messages)
            if not msgs:
                return "New Conversation"

            # Prefer user text; fallback to assistant
            user_msgs = [m.content for m in msgs if role_to_str(m.role) == "user"]
            assistant_msgs = [m.content for m in msgs if role_to_str(m.role) == "assistant"]

            context_text = " ".join(user_msgs[-3:] or assistant_msgs[-3:] or [])
            context_text = context_text.strip()
            if not context_text:
                return "New Conversation"

            # Try LLM first
            try:
                prompt = (
                    "Generate a concise conversation title (<= 50 characters) for a German tax consultation.\n"
                    "Use German tax terms if appropriate, otherwise plain English.\n"
                    "Focus on the main topic(s) only. Output only the title, no quotes.\n\n"
                    f"Context:\n{context_text}\n\nTitle:"
                )
                llm_resp = await self.llm_service.generate_response(
                    messages=[
                        {"role": "system", "content": "You are an expert note-taker for German tax support. Return only the title text."},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.default_model,
                )
                title = _clean_title(llm_resp)
                if title and title.lower() != "title:":
                    logger.info(f"Generated title via LLM for {conversation_id}: {title}")
                    return title
            except Exception as llm_err:
                logger.warning(f"LLM title generation failed, falling back. Err: {llm_err}")

            # Fallback: keyword-based title
            scores = _score_keywords(context_text, _TAX_VOCAB)
            top_terms = [k for k, _ in scores]
            title_fb = _clean_title(_title_from_keywords(top_terms))
            logger.info(f"Generated title via fallback for {conversation_id}: {title_fb}")
            return title_fb

        except Exception as e:
            logger.error(f"Error generating conversation title: {e}")
            return "Tax Consultation"

    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Persist title update."""
        try:
            convo = await self.database.get_conversation(conversation_id)
            if not convo:
                return False
            convo.title = _clean_title(title)
            await self.database.update_conversation(convo)
            logger.info(f"Updated conversation title: {conversation_id} -> {convo.title}")
            return True
        except Exception as e:
            logger.error(f"Error updating conversation title: {e}")
            return False

    # --------------------- Auto-Update Hooks --------------------- #

    async def _get_message_count(self, conversation_id: str) -> int:
        """Try a DB count, fallback to fetching a chunk."""
        try:
            if hasattr(self.database, "count_conversation_messages"):
                return int(await self.database.count_conversation_messages(conversation_id))
        except Exception as e:
            logger.debug(f"count_conversation_messages failed: {e}")

        try:
            # Fallback: fetch last 50 to approximate count
            msgs = await self.database.get_conversation_messages(conversation_id, limit=50)
            return len(msgs or [])
        except Exception as e:
            logger.debug(f"get_conversation_messages fallback failed: {e}")
            return 0

    def _last_update_key(self, conversation_id: str) -> str:
        return f"conv:title:last_update_ts:{conversation_id}"

    async def _should_update_title_now(self, conversation_id: str, message_count: int) -> bool:
        """Gate by message threshold + min interval if memory is available."""
        if message_count < self.auto_update_threshold:
            return False

        # Update roughly every threshold messages
        if message_count % self.auto_update_threshold != 0:
            return False

        if self.memory:
            try:
                last_ts = await self.memory.get_temp_data(self._last_update_key(conversation_id))
                now = time.time()
                if isinstance(last_ts, (int, float)):
                    if now - float(last_ts) < self.auto_update_min_interval_sec:
                        return False
                return True
            except Exception as e:
                logger.debug(f"Reading last title update ts failed: {e}")
                return True
        # No memory service = allow updates on threshold
        return True

    async def _record_title_update(self, conversation_id: str) -> None:
        """Persist last update timestamp (if memory available)."""
        if not self.memory:
            return
        try:
            await self.memory.store_temp_data(
                self._last_update_key(conversation_id),
                time.time(),
                ttl=max(self.auto_update_min_interval_sec * 4, 3600),  # keep a bit longer than interval
            )
        except Exception as e:
            logger.debug(f"Storing last title update ts failed: {e}")

    async def maybe_update_title_on_new_message(self, conversation_id: str, *, force: bool = False) -> Optional[str]:
        """
        Call this after persisting a new message.
        Will auto-refresh the title if:
          - message_count >= threshold AND
          - it's a threshold multiple AND
          - min interval elapsed (if memory service is present),
        or if force=True.
        Returns the new title if updated, else None.
        """
        try:
            count = await self._get_message_count(conversation_id)
            if not force and not await self._should_update_title_now(conversation_id, count):
                return None

            # Use a slightly larger window when refreshing mid-chat
            title = await self.analyze_conversation_for_title(conversation_id, max_messages=12)
            ok = await self.update_conversation_title(conversation_id, title)
            if ok:
                await self._record_title_update(conversation_id)
                return title
            return None
        except Exception as e:
            logger.error(f"maybe_update_title_on_new_message error: {e}")
            return None

    async def finalize_conversation_title(self, conversation_id: str) -> str:
        """
        Force a final, best-effort title (e.g., when closing a conversation).
        Uses a larger context window.
        """
        try:
            title = await self.analyze_conversation_for_title(conversation_id, max_messages=25)
            await self.update_conversation_title(conversation_id, title)
            await self._record_title_update(conversation_id)
            return title
        except Exception as e:
            logger.error(f"finalize_conversation_title error: {e}")
            return "Tax Consultation"

    # --------------------------------------------------------------------- #
    # Summary / Topics
    # --------------------------------------------------------------------- #
    async def get_conversation_summary(self, conversation_id: str, max_messages: int = 10) -> Dict[str, Any]:
        """Return a lightweight summary with message count, last activity, and top topics."""
        try:
            msgs = await self.database.get_conversation_messages(conversation_id, limit=max_messages)
            if not msgs:
                return {
                    "message_count": 0,
                    "last_activity": None,
                    "main_topics": [],
                    "summary": "No messages yet",
                }

            last_ts = getattr(msgs[-1], "timestamp", None)
            if isinstance(last_ts, str):
                last_activity = last_ts
            elif isinstance(last_ts, datetime):
                last_activity = last_ts.isoformat()
            else:
                last_activity = None

            all_text = " ".join(m.content for m in msgs if m and getattr(m, "content", ""))[:5000]
            scored = _score_keywords(all_text, _TAX_VOCAB)
            main_topics = [k for k, _ in scored][:5]
            summary = f"Conversation about {', '.join(main_topics[:3])}" if main_topics else "General tax consultation"

            return {
                "message_count": len(msgs),
                "last_activity": last_activity,
                "main_topics": main_topics,
                "summary": summary,
            }
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {
                "message_count": 0,
                "last_activity": None,
                "main_topics": [],
                "summary": "Error retrieving summary",
            }

    # --------------------------------------------------------------------- #
    # Deletion (safe, DB-method agnostic)
    # --------------------------------------------------------------------- #
    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """
        Delete a conversation and its messages, verifying ownership.
        Uses bulk DB methods when available; otherwise iterates messages.
        """
        try:
            convo = await self.database.get_conversation(conversation_id)
            if not convo or getattr(convo, "user_id", None) != user_id:
                logger.warning(f"Conversation {conversation_id} not found or not owned by {user_id}")
                return False

            try:
                if hasattr(self.database, "delete_messages_by_conversation"):
                    await self.database.delete_messages_by_conversation(conversation_id)
                else:
                    messages = await self.database.get_conversation_messages(conversation_id)
                    for m in messages:
                        try:
                            if hasattr(self.database, "delete_message"):
                                await self.database.delete_message(m.id)
                            elif hasattr(self.database, "delete_conversation_message"):
                                await self.database.delete_conversation_message(m.id)
                            else:
                                logger.debug("No message delete method available on DatabaseService")
                                break
                        except Exception as inner:
                            logger.warning(f"Error deleting message {getattr(m, 'id', '?')}: {inner}")
            except Exception as del_err:
                logger.warning(f"Bulk message deletion failed: {del_err}")

            await self.database.delete_conversation(conversation_id)
            logger.info(f"Deleted conversation {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False
