"""Authentication service (JWT + Redis-backed session cache)."""

import secrets
import jwt
import hashlib
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from ..models.auth import LoginRequest, RegisterRequest, UserSession, AuthResponse, UserRole
from ..models.user import User
from ..services.database import DatabaseService
from ..services.memory import MemoryService
from .base_service import BaseService


class AuthService(BaseService):
    """Authentication service for user management (register/login/logout/token)."""

    def __init__(self, database_service: DatabaseService, memory_service: MemoryService):
        super().__init__("AuthService")
        self.database = database_service
        self.memory_service = memory_service
        self.secret_key = self.settings.jwt_secret
        self.algorithm = "HS256"
        self.token_expiry = timedelta(hours=24)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Validate JWT secret is available
        if not self.secret_key:
            raise ValueError("JWT secret key is required but not configured")

    # ---- Passwords ----------------------------------------------------------

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify bcrypt (primary) and SHA-256 (legacy fallback)."""
        try:
            return self.pwd_context.verify(password, hashed_password)
        except Exception:
            try:
                return hashlib.sha256(password.encode()).hexdigest() == hashed_password
            except Exception:
                return False

    # ---- JWT ----------------------------------------------------------------

    def generate_token(self, user_id: str, email: str) -> str:
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.now(timezone.utc) + self.token_expiry,
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        # PyJWT v2 returns str; older could return bytes
        return token.decode("utf-8") if isinstance(token, (bytes, bytearray)) else token

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid token")
            return None
        except Exception as e:
            self.logger.error(f"Token decode error: {e}")
            return None

    # ---- Redis session helpers ---------------------------------------------

    async def store_user_session(self, session: UserSession) -> None:
        try:
            data = {
                "user_id": session.user_id,
                "session_id": session.session_id,
                "email": session.email,
                "name": session.name,
                "role": session.role.value,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "is_active": "true" if session.is_active else "false",
            }
            await self.memory_service.store_temp_data(
                f"user_session:{session.user_id}",
                data,
                ttl=self.settings.short_term_memory_ttl,
            )
            self.logger.info(f"Stored user session in Redis: {session.user_id}")
        except Exception as e:
            self.logger.error(f"Error storing user session: {e}")

    async def get_user_session(self, user_id: str) -> Optional[UserSession]:
        try:
            raw = await self.memory_service.get_temp_data(f"user_session:{user_id}")
            if not raw:
                return None
            return UserSession(
                user_id=raw["user_id"],
                session_id=raw["session_id"],
                email=raw["email"],
                name=raw["name"],
                role=UserRole(raw["role"]),
                created_at=datetime.fromisoformat(raw["created_at"]),
                expires_at=datetime.fromisoformat(raw["expires_at"]),
                is_active=str(raw.get("is_active", "")).lower() == "true",
            )
        except Exception as e:
            self.logger.error(f"Error getting user session: {e}")
            return None

    async def invalidate_user_session(self, user_id: str) -> None:
        try:
            await self.memory_service.delete_user_session(user_id)
            # Also drop temp copy if used
            await self.memory_service.store_temp_data(f"user_session:{user_id}", {}, ttl=1)
            self.logger.info(f"Invalidated user session: {user_id}")
        except Exception as e:
            self.logger.error(f"Error invalidating user session: {e}")

    # ---- Public API ---------------------------------------------------------

    async def register_user(self, request: RegisterRequest) -> AuthResponse:
        """Create a user, store hashed password, return session + token."""
        try:
            if request.password != request.confirm_password:
                return AuthResponse(success=False, message="Passwords do not match")

            existing = await self.database.get_user_by_email(request.email)
            if existing:
                return AuthResponse(success=False, message="User with this email already exists")

            user = User(
                id=secrets.token_urlsafe(16),
                email=request.email,
                name=request.name,
                password_hash=self.hash_password(request.password),
            )
            created = await self.database.create_user(user)

            session = UserSession(
                user_id=created.id,
                session_id=secrets.token_urlsafe(32),
                email=created.email,
                name=created.name,
                role=UserRole.USER,
            )
            token = self.generate_token(created.id, created.email)

            # Cache session for fast lookup
            await self.store_user_session(session)

            self.logger.info(f"User registered: {created.email}")
            return AuthResponse(success=True, message="User registered successfully", user=session, token=token)
        except Exception as e:
            self.logger.error(f"Error registering user: {e}")
            return AuthResponse(success=False, message=f"Registration failed: {str(e)}")

    async def login_user(self, request: LoginRequest) -> AuthResponse:
        """Verify credentials, issue fresh token, cache session."""
        try:
            user = await self.database.get_user_by_email(request.email)
            if not user or not self.verify_password(request.password, user.password_hash):
                return AuthResponse(success=False, message="Invalid email or password")

            session = UserSession(
                user_id=user.id,
                session_id=secrets.token_urlsafe(32),
                email=user.email,
                name=user.name,
                role=UserRole.USER,
            )
            token = self.generate_token(user.id, user.email)

            await self.store_user_session(session)

            self.logger.info(f"User logged in: {user.email}")
            return AuthResponse(success=True, message="Login successful", user=session, token=token)
        except Exception as e:
            self.logger.error(f"Error logging in user: {e}")
            return AuthResponse(success=False, message=f"Login failed: {str(e)}")

    async def verify_token(self, token: str) -> Optional[UserSession]:
        """Validate JWT and synthesize a transient session (no cache write)."""
        try:
            payload = self.decode_token(token)
            if not payload:
                return None

            user = await self.database.get_user(payload["user_id"])
            if not user:
                return None

            return UserSession(
                user_id=user.id,
                session_id=secrets.token_urlsafe(32),
                email=user.email,
                name=user.name,
                role=UserRole.USER,
            )
        except Exception as e:
            self.logger.error(f"Error verifying token: {e}")
            return None

    async def logout_user(self, token: str) -> AuthResponse:
        """Invalidate cached session for the token's user (JWT remains stateless)."""
        try:
            payload = self.decode_token(token)
            if payload and payload.get("user_id"):
                await self.invalidate_user_session(payload["user_id"])
            else:
                self.logger.warning("Logout called with invalid/expired token")
            return AuthResponse(success=True, message="Logout successful")
        except Exception as e:
            self.logger.error(f"Error logging out user: {e}")
            return AuthResponse(success=False, message=f"Logout failed: {str(e)}")

    async def get_current_user(self, token: str) -> Optional[UserSession]:
        """Return an active session if in cache, otherwise rehydrate from DB and cache."""
        try:
            payload = self.decode_token(token)
            if not payload:
                return None

            user_id = payload.get("user_id")
            if not user_id:
                return None

            # Fast path: cached
            cached = await self.get_user_session(user_id)
            if cached and cached.is_active:
                return cached

            # Rehydrate from DB
            user = await self.database.get_user(user_id)
            if not user:
                return None

            session = UserSession(
                user_id=user.id,
                session_id=secrets.token_urlsafe(32),
                email=user.email,
                name=user.name,
                role=UserRole.USER,
            )
            await self.store_user_session(session)
            return session
        except Exception as e:
            self.logger.error(f"Error getting current user: {e}")
            return None
