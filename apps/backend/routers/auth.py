"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from src.core.logging import get_logger

from ..models import LoginRequest, RegisterRequest, AuthResponse
from ..dependencies import get_auth_service
from src.services.auth import AuthService

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=AuthResponse)
async def register_user(
    request: RegisterRequest,
    auth_svc: AuthService = Depends(get_auth_service)
):
    """Register a new user."""
    try:
        # Create a proper RegisterRequest with confirm_password
        from src.models.auth import RegisterRequest as InternalRegisterRequest
        register_request = InternalRegisterRequest(
            name=request.name,
            email=request.email,
            password=request.password,
            confirm_password=request.password  # Use the same password for confirmation
        )
        result = await auth_svc.register_user(register_request)
        
        if result.success:
            return AuthResponse(
                success=True,
                message="User registered successfully",
                token=result.token,
                user=result.user.dict() if result.user else None
            )
        else:
            return AuthResponse(
                success=False,
                message=result.message
            )
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login_user(
    request: LoginRequest,
    auth_svc: AuthService = Depends(get_auth_service)
):
    """Login user."""
    try:
        result = await auth_svc.login_user(request)
        
        if result.success:
            return AuthResponse(
                success=True,
                message="Login successful",
                token=result.token,
                user=result.user.dict() if result.user else None
            )
        else:
            return AuthResponse(
                success=False,
                message=result.message
            )
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/logout")
async def logout_user(
    token: str,
    auth_svc: AuthService = Depends(get_auth_service)
):
    """Logout user."""
    try:
        result = await auth_svc.logout_user(token)
        return {"success": result.success, "message": result.message}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.get("/me")
async def get_current_user(
    token: str,
    auth_svc: AuthService = Depends(get_auth_service)
):
    """Get current user information."""
    try:
        user = await auth_svc.get_current_user(token)
        if user:
            return {"success": True, "user": user}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )
