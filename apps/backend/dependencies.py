"""FastAPI dependencies for authentication and service injection."""

from fastapi import HTTPException, Depends, status, Header
from typing import Optional

from src.services.auth import AuthService
from src.services.database import DatabaseService
from src.workflow.graph import TaxFixWorkflow
from src.models.auth import UserSession


# Global services (set during app startup)
workflow: Optional[TaxFixWorkflow] = None
database_service: Optional[DatabaseService] = None
memory_service = None
auth_service: Optional[AuthService] = None


def get_workflow() -> TaxFixWorkflow:
    """Get workflow instance."""
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow not initialized"
        )
    return workflow


def get_auth_service() -> AuthService:
    """Get auth service instance."""
    if auth_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service not initialized"
        )
    return auth_service


def get_database_service() -> DatabaseService:
    """Get database service instance."""
    if database_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service not initialized"
        )
    return database_service


async def get_current_user(
    authorization: str = Header(None),
    auth_svc: AuthService = Depends(get_auth_service)
) -> UserSession:
    """Dependency to get current authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token = authorization.split(" ")[1]
    user = await auth_svc.get_current_user(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return user
