"""
Authentication routes for TaxFix

handles registration, login, logout, 
and getting current user info. This is where users first interact with our system.
"""

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
    """
    Register a new user get basic user info, from frontend,
    and I need to create a proper internal request with password confirmation.
    This looks fine for now, will pop in here later to add email verification - if i have time.
    """
    try:
        # proper RegisterRequest with confirm_password
        # The frontend doesn't send confirm_password, so I'll use the same password - lot of issues with this.
        from src.models.auth import RegisterRequest as InternalRegisterRequest
        register_request = InternalRegisterRequest(
            name=request.name,
            email=request.email,
            password=request.password,
            confirm_password=request.password  # Using same password for confirmation - works now
        )
        
        # Let the auth service handle the actual registration logic
        result = await auth_svc.register_user(register_request)
        
        if result.success:
            return AuthResponse(
                success=True,
                message="User registered successfully",
                token=result.token,
                user=result.user.dict() if result.user else None
            )
        else:
            # Registration failed - probably duplicate email or validation error - if time can make this better.
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
    """
    Login user - standard email/password authentication.
    
    This looks fine for now, will pop in here later to add rate limiting
    and maybe remember me functionality. - i feel this is fine as of now.
    """
    try:
        # Delegate to auth service - they handle password hashing and validation - working finally!
        result = await auth_svc.login_user(request)
        
        if result.success:
            return AuthResponse(
                success=True,
                message="Login successful",
                token=result.token,
                user=result.user.dict() if result.user else None
            )
        else:
            # Login failed - wrong credentials or user doesn't exist
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
    """
    Logout user - invalidate their session token.
    
    This looks fine for now, will pop in here later to add token blacklisting
    and maybe audit logging for security. - a lot of token handling issues here. - works but very buggy.
    """
    try:
        # Let the auth service handle token invalidation
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
    """
    Get current user information - used to check if user is still logged in. - made this for refreash part - still buggy.
    """
    try:
        # Validate the token and get user info
        user = await auth_svc.get_current_user(token)
        if user:
            return {"success": True, "user": user}
        else:
            # Token is invalid or expired
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
