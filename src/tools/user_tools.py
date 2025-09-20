"""User management tools for agents (refined)."""

from __future__ import annotations

from typing import Dict, Any, Optional, Tuple, Iterable
from copy import deepcopy

from ..models.user import UserProfile
from ..services.database import DatabaseService
from ..core.logging import get_logger
from ..utils import to_dict, clean_updates

logger = get_logger(__name__)


# -------------------------
# Helpers
# -------------------------

def _clean_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and whitelist update fields to avoid accidental schema drift.
    Casts common numeric fields and trims strings.
    """
    if not isinstance(updates, dict):
        return {}

    allowed_fields: Iterable[str] = {
        "name",
        "email",
        "occupation",
        "annual_income",
        "filing_status",
        "dependents",
        "employment_status",
        "country",
        "currency",
        "tax_goals",
        "risk_tolerance",
        "tax_complexity_level",
        "conversation_count",
        "health_insurance_type",
        "age",
    }

    out: Dict[str, Any] = {}
    for k, v in updates.items():
        if k not in allowed_fields:
            # Ignore unknown keys silently (tools can be noisy otherwise)
            continue

        if v is None:
            # Skip explicit None to avoid unintentional nulling unless caller really wants that
            # (if you want nulling behavior, pass {"$unset": ["field1", "field2"]} via a separate path)
            continue

        if k in {"name", "email", "occupation", "filing_status", "employment_status", "country", "currency",
                 "risk_tolerance", "tax_complexity_level", "health_insurance_type"}:
            try:
                out[k] = str(v).strip()
            except Exception:
                continue

        elif k in {"annual_income"}:
            try:
                out[k] = float(v)
            except Exception:
                logger.warning(f"Coercion failed for annual_income='{v}'")
                continue

        elif k in {"dependents", "age", "conversation_count"}:
            try:
                out[k] = int(v)
            except Exception:
                logger.warning(f"Coercion failed for {k}='{v}'")
                continue

        elif k == "tax_goals":
            # Normalize list of strings
            try:
                if isinstance(v, (list, tuple)):
                    vals = [str(x).strip() for x in v if str(x).strip()]
                else:
                    vals = [str(v).strip()] if str(v).strip() else []
                # Dedup while preserving order
                seen = set()
                deduped = []
                for item in vals:
                    key = item.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    deduped.append(item)
                out[k] = deduped
            except Exception:
                continue

        else:
            # Default pass-through
            out[k] = v

    return out


def _merge_lists(existing: Optional[list], incoming: Optional[list], max_len: int = 16) -> list:
    """Merge two lists of strings with de-duplication and length cap."""
    existing = existing or []
    incoming = incoming or []
    out = []
    seen = set()
    for item in [*existing, *incoming]:
        s = str(item).strip()
        if not s:
            continue
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
        if len(out) >= max_len:
            break
    return out


def _apply_updates(profile: UserProfile, updates: Dict[str, Any]) -> UserProfile:
    """
    Apply updates to a profile safely, respecting types where possible.
    Uses pydantic re-validation by reconstructing the model after merge.
    """
    base = to_dict(profile)
    merged = deepcopy(base)

    for k, v in updates.items():
        if k == "tax_goals":
            merged[k] = _merge_lists(base.get("tax_goals"), v)
        else:
            merged[k] = v

    # Re-validate with pydantic
    try:
        return UserProfile(**merged)
    except Exception as e:
        logger.error(f"Re-validation failed when applying updates: {e}")
        # As a fallback, set field-by-field on the existing model
        for k, v in updates.items():
            if hasattr(profile, k):
                try:
                    setattr(profile, k, v)
                except Exception as ee:
                    logger.warning(f"Failed to set {k} on profile: {ee}")
        return profile


# -------------------------
# UserTools
# -------------------------

class UserTools:
    """Tools for user profile management (get/upsert/patch/increment)."""

    def __init__(self, database_service: DatabaseService):
        self.database = database_service

    # ---- Retrieval ----
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile as a plain dict."""
        try:
            profile = await self.database.get_user_profile(user_id)
            return to_dict(profile) if profile else None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get basic user info (non-sensitive)."""
        try:
            user = await self.database.get_user(user_id)
            if not user:
                return None
            return {
                "user_id": user.id,
                "name": getattr(user, "name", None),
                "email": getattr(user, "email", None),
                "created_at": getattr(user, "created_at", None).isoformat()
                if getattr(user, "created_at", None)
                else None,
            }
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    # ---- Upsert/Patch ----
    async def upsert_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create or update a profile in a single call.
        Returns the updated profile as dict on success, None on failure.
        """
        try:
            cleaned = _clean_updates(updates)
            current = await self.database.get_user_profile(user_id)

            if current:
                new_profile = _apply_updates(current, cleaned)
                saved = await self.database.update_user_profile(new_profile)
                logger.info(f"Updated user profile for {user_id}: {cleaned}")
                return to_dict(saved) if saved else None

            # Create new
            payload = {"user_id": user_id, **cleaned}
            try:
                new_profile = UserProfile(**payload)
            except Exception as e:
                logger.error(f"Validation error creating profile: {e}")
                return None

            created = await self.database.create_user_profile(new_profile)
            logger.info(f"Created new user profile for {user_id}: {cleaned}")
            return to_dict(created) if created else None

        except Exception as e:
            logger.error(f"Error upserting user profile: {e}")
            return None

    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Backwards-compatible wrapper: applies a patch and returns success boolean.
        Prefer `upsert_user_profile` if you need the updated object back.
        """
        result = await self.upsert_user_profile(user_id, updates)
        return result is not None

    # ---- Counters ----
    async def update_conversation_count(self, user_id: str, increment: int = 1) -> bool:
        """Increment conversation_count safely (creates profile if missing)."""
        try:
            profile = await self.database.get_user_profile(user_id)
            if not profile:
                # Create minimal profile with counter = increment
                payload = {"user_id": user_id, "conversation_count": int(max(increment, 0))}
                try:
                    new_profile = UserProfile(**payload)
                except Exception as e:
                    logger.error(f"Validation error creating profile with counter: {e}")
                    return False
                created = await self.database.create_user_profile(new_profile)
                return created is not None

            # Update existing
            current = to_dict(profile)
            current_count = int(current.get("conversation_count") or 0)
            new_count = max(0, current_count + int(increment))
            patched = _apply_updates(profile, {"conversation_count": new_count})
            saved = await self.database.update_user_profile(patched)
            return saved is not None

        except Exception as e:
            logger.error(f"Error updating conversation count: {e}")
            return False
