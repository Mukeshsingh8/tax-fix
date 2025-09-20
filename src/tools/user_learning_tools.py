"""User learning tools for building dynamic user profiles from conversations (refined)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ..services.database import DatabaseService
from ..services.llm import LLMService
from ..core.logging import get_logger
from ..core.config import get_settings
from ..utils import role_to_str, safe_text

logger = get_logger(__name__)
_settings = get_settings()


# -------------------------
# Helpers
# -------------------------

def _safe_text(s: Any, max_len: int = 2000) -> str:
    """Basic text sanitizer with length guard."""
    if not s:
        return ""
    txt = str(s).strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt[:max_len]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_existing_value(blob: Any) -> str:
    """
    Database may store learning in different shapes:
    try common keys and fallback.
    """
    if not blob:
        return ""
    if isinstance(blob, str):
        return blob
    # dict-like
    for k in ("value", "user_learning", "summary", "data"):
        v = blob.get(k)
        if v:
            return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    # last resort
    try:
        return json.dumps(blob, ensure_ascii=False)
    except Exception:
        return ""


def _compact_json(d: Dict[str, Any]) -> str:
    try:
        return json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        # lossy fallback
        return json.dumps(d, ensure_ascii=False)


def _parse_json_maybe(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except Exception:
        return None


def _pair_turns(messages: List[Any], max_turns: int = 6) -> List[Tuple[str, str]]:
    """
    Build user→assistant turns in chronological order.
    Each turn is (user_text, assistant_text_or_empty).
    """
    turns: List[Tuple[str, str]] = []
    pending_user: Optional[str] = None

    for m in messages:
        role = role_to_str(getattr(m, "role", ""))
        content = _safe_text(getattr(m, "content", ""), max_len=1200)
        if not content:
            continue

        if role == "user":
            # If previous user had no assistant reply, close it with empty assistant text.
            if pending_user is not None:
                turns.append((pending_user, ""))  # orphan user line
            pending_user = content
        elif role == "assistant":
            if pending_user is not None:
                turns.append((pending_user, content))
                pending_user = None
            else:
                # assistant without a preceding user; put as empty user turn
                turns.append(("", content))

    if pending_user is not None:
        turns.append((pending_user, ""))

    return turns[-max_turns:]  # keep last N turns


def _format_turns_for_prompt(turns: List[Tuple[str, str]]) -> str:
    lines: List[str] = []
    for i, (u, a) in enumerate(turns, 1):
        if u:
            lines.append(f"Turn {i} — User: {u}")
        if a:
            lines.append(f"Turn {i} — Assistant: {a}")
    return "\n".join(lines)


def _fallback_from_text(all_text: str) -> Dict[str, Any]:
    """
    Super-simple heuristics to produce a structured summary when LLM is unavailable.
    """
    txt = (all_text or "").lower()
    preferences: List[str] = []
    if any(k in txt for k in ["step", "steps", "walk me through", "how to"]):
        preferences.append("Prefers step-by-step guidance")
    if any(k in txt for k in ["example", "examples", "sample"]):
        preferences.append("Likes concrete examples")
    if any(k in txt for k in ["quick", "brief", "short answer"]):
        preferences.append("Prefers concise answers")

    knowledge = "beginner"
    if any(k in txt for k in ["grundfreibetrag", "kinderfreibetrag", "werbungskosten", "sonderausgaben"]):
        knowledge = "intermediate"
    if any(k in txt for k in ["§", "estg", "beitragsbemessungsgrenze"]):
        knowledge = "advanced"

    interests = []
    for kw, label in [
        ("werbungskosten", "Work-related expenses (Werbungskosten)"),
        ("sonderausgaben", "Special expenses (Sonderausgaben)"),
        ("grundfreibetrag", "Basic allowance (Grundfreibetrag)"),
        ("kinderfreibetrag", "Child allowance (Kinderfreibetrag)"),
        ("steuerklasse", "Tax classes (Steuerklassen)"),
        ("riester", "Riester pension"),
        ("krankenversicherung", "Health insurance"),
        ("pflegeversicherung", "Long-term care insurance"),
    ]:
        if kw in txt:
            interests.append(label)

    return {
        "communication_style": "Clear and direct" if "?" in all_text else "Neutral",
        "tax_knowledge_level": knowledge,
        "preferences": preferences or ["No strong preferences detected"],
        "frustrations": [],
        "interests": interests[:5],
        "personality_traits": [],
        "goals": [],
        "learning_style": "Prefers examples" if "example" in txt else "Not specified",
        "evidence": ["Heuristic fallback (limited confidence)"],
        "updated_at": _now_iso(),
    }


def _merge_lists(a: List[str], b: List[str], max_len: int = 8) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in (a or []) + (b or []):
        t = item.strip()
        if not t or t.lower() in seen:
            continue
        seen.add(t.lower())
        out.append(t)
        if len(out) >= max_len:
            break
    return out


def _merge_learning(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two structured learning dicts."""
    merged: Dict[str, Any] = {}
    # string-ish fields
    for k in ("communication_style", "tax_knowledge_level", "learning_style"):
        merged[k] = (new.get(k) or old.get(k) or "").strip()

    # list-ish fields
    for k in ("preferences", "frustrations", "interests", "personality_traits", "goals", "evidence"):
        merged[k] = _merge_lists(old.get(k, []), new.get(k, []), max_len=10)

    merged["updated_at"] = _now_iso()
    return merged


class UserLearningTools:
    """Tools for learning about users from conversations and building dynamic profiles."""

    def __init__(self, database_service: DatabaseService, llm_service: LLMService):
        self.database = database_service
        self.llm_service = llm_service
        self.default_model = getattr(_settings, "default_llm_model", None) or "groq"

    # --------------------------------------------------------------------- #
    # Core analysis
    # --------------------------------------------------------------------- #
    async def analyze_conversation_for_learning(
        self,
        user_id: str,
        conversation_id: str,
        max_messages: int = 14,
    ) -> str:
        """
        Extract *structured* user-learning from recent messages.
        Returns minified JSON (string) on success, or a short textual note on failure.
        """
        try:
            messages = await self.database.get_conversation_messages(conversation_id, limit=max_messages)
            if not messages:
                return "No conversation data available for analysis."

            turns = _pair_turns(messages, max_turns=6)
            if not turns:
                return "No user messages found for analysis."

            convo_for_prompt = _format_turns_for_prompt(turns)

            existing_learning_raw = await self.database.get_user_learning(user_id)
            existing_summary_str = _load_existing_value(existing_learning_raw)
            existing_struct = _parse_json_maybe(existing_summary_str) or {}

            # Build prompt with clear JSON-only instruction
            system = (
                "You analyze conversations to infer stable user preferences for future personalization. "
                "STRICTLY return valid minified JSON only (no text outside JSON)."
            )
            user_prompt = (
                "From the conversation turns below, extract a structured user-learning profile. "
                "Focus on stable traits useful for future answers (style, knowledge level, preferences).\n\n"
                f"Existing summary (JSON may be empty):\n{existing_summary_str or '{}'}\n\n"
                "Conversation (latest turns at the end):\n"
                f"{convo_for_prompt}\n\n"
                "Return JSON with keys:\n"
                "{"
                "\"communication_style\": \"string\", "
                "\"tax_knowledge_level\": \"beginner|intermediate|advanced\", "
                "\"preferences\": [\"string\"], "
                "\"frustrations\": [\"string\"], "
                "\"interests\": [\"string\"], "
                "\"personality_traits\": [\"string\"], "
                "\"goals\": [\"string\"], "
                "\"learning_style\": \"string\", "
                "\"evidence\": [\"very short bullet quotes from the conversation\"], "
                "\"updated_at\": \"ISO-8601 timestamp\""
                "}"
            )

            llm_resp = await self.llm_service.generate_response(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user_prompt}],
                model=self.default_model,
            )

            # Parse & merge
            parsed = _parse_json_maybe(llm_resp.strip())
            if not isinstance(parsed, dict):
                raise ValueError("Model did not return valid JSON")

            if "updated_at" not in parsed:
                parsed["updated_at"] = _now_iso()

            merged = _merge_learning(existing_struct if isinstance(existing_struct, dict) else {}, parsed)
            return _compact_json(merged)

        except Exception as e:
            logger.error(f"Error analyzing conversation for learning: {e}")

            # Fallback summary (heuristics)
            try:
                # Build a quick all-text window
                all_text = " ".join(
                    _safe_text(getattr(m, "content", ""), max_len=500)
                    for m in (messages or [])
                    if getattr(m, "content", None)
                )[:5000]
                fallback = _fallback_from_text(all_text)
                return _compact_json(fallback)
            except Exception as inner:
                logger.error(f"Fallback learning also failed: {inner}")
                return f"Error analyzing conversation: {e}"

    # --------------------------------------------------------------------- #
    # Persistence & retrieval
    # --------------------------------------------------------------------- #
    async def process_conversation_learning(self, user_id: str, conversation_id: str) -> bool:
        """
        Analyze a conversation and store/merge a *structured* summary string (JSON).
        """
        try:
            learning_summary = await self.analyze_conversation_for_learning(user_id, conversation_id)
            if not learning_summary or learning_summary.startswith("Error"):
                logger.info(f"No insights extracted from conversation {conversation_id}")
                return False

            # Persist as string (DB layer can store as TEXT/JSONB/etc.)
            await self.database.create_or_update_user_learning(user_id, learning_summary)
            logger.info(f"Updated user learning summary for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error processing conversation learning: {e}")
            return False

    async def get_user_learning_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Return a normalized view:
        - summary: string (JSON if available)
        - last_updated: iso str if known
        """
        try:
            learning_data = await self.database.get_user_learning(user_id)
            if not learning_data:
                return {"user_id": user_id, "summary": "No learning data available", "last_updated": None}

            raw = _load_existing_value(learning_data)
            parsed = _parse_json_maybe(raw)
            # Prefer JSON if available
            if isinstance(parsed, dict):
                return {"user_id": user_id, "summary": _compact_json(parsed), "last_updated": parsed.get("updated_at")}
            # else: return whatever string we found, try a DB timestamp
            return {
                "user_id": user_id,
                "summary": raw or "No summary available",
                "last_updated": getattr(learning_data, "updated_at", None) or learning_data.get("updated_at", None),
            }
        except Exception as e:
            logger.error(f"Error getting user learning summary: {e}")
            return {"user_id": user_id, "summary": f"Error retrieving learning data: {e}", "last_updated": None}

    # --------------------------------------------------------------------- #
    # Update cadence
    # --------------------------------------------------------------------- #
    async def should_update_user_profile(self, user_id: str, conversation_id: str) -> bool:
        """
        Decide whether to update learning now.
        Default: every 5 user messages (lightweight), with at least 1 user message present.
        """
        try:
            messages = await self.database.get_conversation_messages(conversation_id)
            user_msgs = [m for m in messages or [] if role_to_str(getattr(m, "role", "")) == "user"]
            count = len(user_msgs)
            logger.info(f"Message count check: conversation_id={conversation_id}, user_messages={count}")

            return count > 0 and (count % 5 == 0)
        except Exception as e:
            logger.error(f"Error checking if should update profile: {e}")
            return False
