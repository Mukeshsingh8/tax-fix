"""
FastAPI backend for TaxFix Multi-Agent System.
"""
import asyncio
import json
import re
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import uvicorn

from fastapi import FastAPI, HTTPException, Depends, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime

from src.core.config import get_settings, setup_langsmith_tracing
from src.core.logging import setup_logging, get_logger
from src.workflow.graph import build_workflow
from src.services.database import DatabaseService
from src.services.memory import MemoryService
from src.services.auth import AuthService

logger = get_logger(__name__)
settings = get_settings()

# Global services
workflow = None
database_service = None
memory_service = None
auth_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global workflow, database_service, memory_service, auth_service
    
    # Startup
    logger.info("Starting TaxFix API server")
    
    try:
        # Setup logging
        setup_logging("INFO")
        
        # Setup LangSmith tracing
        setup_langsmith_tracing()
        
        # Initialize services
        database_service = DatabaseService()
        memory_service = MemoryService()
        
        # Connect to Redis
        try:
            await memory_service.connect()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Memory service will work without Redis.")
        
        auth_service = AuthService(database_service, memory_service)
        
        # Initialize workflow
        workflow = await build_workflow()
        
        logger.info("TaxFix API server started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start TaxFix API server: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down TaxFix API server")
        
        # Disconnect from Redis
        if memory_service:
            try:
                await memory_service.disconnect()
                logger.info("Disconnected from Redis")
            except Exception as e:
                logger.warning(f"Error disconnecting from Redis: {e}")


# Create FastAPI app
app = FastAPI(
    title="TaxFix Multi-Agent API",
    version="1.0.0",
    description="Multi-Agent Tax Advisory System with LangGraph",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ChatMessage(BaseModel):
    """Chat message model."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    suggested_actions: list = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LoginRequest(BaseModel):
    """Login request model."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class RegisterRequest(BaseModel):
    """Registration request model."""
    name: str = Field(..., description="User name")
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class AuthResponse(BaseModel):
    """Authentication response model."""
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class UserProfile(BaseModel):
    """User profile model."""
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    annual_income: Optional[float] = None
    employment_status: Optional[str] = None
    filing_status: Optional[str] = None
    dependents: int = 0
    conversation_count: int = 0
    last_interaction: Optional[datetime] = None


class CreateProfileRequest(BaseModel):
    """Profile creation request model."""
    employment_status: str = Field(..., description="Employment status")
    filing_status: str = Field(..., description="Filing status")
    annual_income: float = Field(..., description="Annual income")
    dependents: int = Field(default=0, description="Number of dependents")
    preferred_deductions: list = Field(default_factory=list, description="Preferred deductions")
    tax_goals: list = Field(default_factory=list, description="Tax goals")
    risk_tolerance: str = Field(default="conservative", description="Risk tolerance")
    preferred_communication_style: str = Field(default="friendly", description="Communication style")
    tax_complexity_level: str = Field(default="beginner", description="Tax complexity level")


# Dependency functions
def get_workflow():
    """Get workflow instance."""
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow not initialized"
        )
    return workflow


def get_auth_service():
    """Get auth service instance."""
    if auth_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service not initialized"
        )
    return auth_service


def get_database_service():
    """Get database service instance."""
    if database_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service not initialized"
        )
    return database_service


# API Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "TaxFix Multi-Agent API",
        "version": "1.0.0",
        "status": "running",
        "description": "Multi-Agent Tax Advisory System with LangGraph"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "workflow": workflow is not None,
            "database": database_service is not None,
            "memory": memory_service is not None,
            "auth": auth_service is not None
        }
    }


# Authentication endpoints
@app.post("/auth/register", response_model=AuthResponse)
async def register_user(
    request: RegisterRequest,
    auth_svc: AuthService = Depends(get_auth_service)
):
    """Register a new user."""
    try:
        # Create a proper RegisterRequest with confirm_password
        from src.models.auth import RegisterRequest
        register_request = RegisterRequest(
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
        get_logger(__name__).error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/auth/login", response_model=AuthResponse)
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
        get_logger(__name__).error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@app.post("/auth/logout")
async def logout_user(
    token: str,
    auth_svc: AuthService = Depends(get_auth_service)
):
    """Logout user."""
    try:
        result = await auth_svc.logout_user(token)
        return {"success": result.success, "message": result.message}
    except Exception as e:
        get_logger(__name__).error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@app.get("/auth/me")
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
        get_logger(__name__).error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )






# Chat endpoints
@app.post("/chat/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    authorization: str = Header(None),
    workflow_instance = Depends(get_workflow),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Send a message to the TaxFix assistant."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Generate session ID if not provided
        session_id = message.session_id or f"session_{user.user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Get user profile
        user_profile = await db_svc.get_user_profile(user.user_id)
        
        # Process message through workflow
        response_data = await workflow_instance.process_message(
            user_message=message.message,
            session_id=session_id,
            user_id=user.user_id,
            user_profile=user_profile
        )
        
        # Create response
        response = ChatResponse(
            content=response_data["content"],
            confidence=response_data["confidence"],
            reasoning=response_data["reasoning"],
            suggested_actions=response_data["suggested_actions"],
            metadata=response_data["metadata"],
            session_id=session_id
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        from src.core.logging import get_logger
        get_logger(__name__).error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@app.post("/chat/message/stream")
async def send_message_stream(
    message: ChatMessage,
    authorization: str = Header(None),
    workflow_instance = Depends(get_workflow),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Send a message to the TaxFix assistant with streaming response."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Generate session ID if not provided
        session_id = message.session_id or f"session_{user.user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Get user profile
        user_profile = await db_svc.get_user_profile(user.user_id)
        
        # Process message through workflow
        response_data = await workflow_instance.process_message(
            user_message=message.message,
            session_id=session_id,
            user_id=user.user_id,
            user_profile=user_profile
        )
        
        # Stream the response
        async def generate_stream():
            # Markdown-safe normalization before streaming tokens
            _md_enum = re.compile(r'(?m)^(?P<indent>\s*)(?P<num>\d+)\.\s')
            _md_bullets = re.compile(r'(?m)^(?P<indent>\s*)(?:•|-|\*)\s+')
            _md_sections = re.compile(
                r'(?m)^(Summary:|Actionable Steps:|Notes:|Assumptions:|Action Tip:|Next Steps:|Interactive Question:)\s*',
                re.IGNORECASE,
            )

            def format_markdown_safe(text: str) -> str:
                in_code = False
                out_lines = []
                for line in text.splitlines(True):  # keep newlines
                    stripped = line.strip()
                    if stripped.startswith("```"):
                        in_code = not in_code
                        out_lines.append(line)
                        continue
                    if in_code:
                        out_lines.append(line)
                        continue

                    # bullets only if at start of line
                    line = _md_bullets.sub(r'\g<indent>- ', line)
                    # numbered lists only if at start of line; add a single blank line before
                    line = _md_enum.sub(r'\n\g<indent>\g<num>. ', line)
                    out_lines.append(line)

                s = "".join(out_lines)
                s = _md_sections.sub(r'\n\n\1', s)
                s = re.sub(r'\n{3,}', '\n\n', s)
                # normalize thin NBSPs
                s = s.replace('\u202f', ' ')
                return s

            content = format_markdown_safe(response_data.get("content", ""))

            buffer = ""
            safe_boundaries = set(" \t\r.,;:!?)]}")  # not including \n
            for ch in content:
                if ch == "\n":
                    if buffer:
                        yield f"data: {json.dumps({'delta': buffer})}\n\n"
                        buffer = ""
                    # send newline as its own delta (avoid f-string backslash in expression)
                    newline_frame = "data: " + json.dumps({"delta": "\n"}) + "\n\n"
                    yield newline_frame
                    await asyncio.sleep(0.005)
                    continue

                buffer += ch
                if ch in safe_boundaries:
                    yield f"data: {json.dumps({'delta': buffer})}\n\n"
                    buffer = ""
                    await asyncio.sleep(0.005)

            if buffer:
                yield f"data: {json.dumps({'delta': buffer})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from src.core.logging import get_logger
        get_logger(__name__).error(f"Streaming chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing streaming message: {str(e)}"
        )


@app.get("/user/profile")
async def get_user_profile(
    authorization: str = Header(None),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get user profile."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user profile
        profile = await db_svc.get_user_profile(user.user_id)
        if profile:
            return {"success": True, "profile": profile.dict()}
        else:
            return {"success": False, "message": "Profile not found"}
            
    except HTTPException:
        raise
    except Exception as e:
        get_logger(__name__).error(f"Get profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting profile: {str(e)}"
        )


@app.get("/user/conversations")
async def get_user_conversations(
    authorization: str = Header(None),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get user conversation history."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get conversations
        conversations = await db_svc.get_user_conversations(user.user_id)
        
        # Get message count for each conversation
        conversations_with_counts = []
        for conv in conversations:
            messages = await db_svc.get_conversation_messages(conv.id)
            conversations_with_counts.append({
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": len(messages)
            })
        
        return {
            "success": True,
            "conversations": conversations_with_counts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        from src.core.logging import get_logger
        get_logger(__name__).error(f"Get conversations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting conversations: {str(e)}"
        )


@app.get("/conversation/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    authorization: str = Header(None),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get messages for a specific conversation."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get conversation to verify ownership
        conversation = await db_svc.get_conversation(conversation_id)
        if not conversation or conversation.user_id != user.user_id:
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
        get_logger(__name__).error(f"Get conversation messages error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting conversation messages: {str(e)}"
        )


@app.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    authorization: str = Header(None),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Delete a conversation and all its messages."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get conversation to verify ownership
        conversation = await db_svc.get_conversation(conversation_id)
        if not conversation or conversation.user_id != user.user_id:
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
        get_logger(__name__).error(f"Delete conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting conversation: {str(e)}"
        )


@app.post("/user/profile")
async def create_user_profile(
    profile_data: CreateProfileRequest,
    authorization: str = Header(None),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Create or update user profile."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Create profile data
        profile_dict = profile_data.dict()
        profile_dict["user_id"] = user.user_id
        
        # Ensure all required fields are present with defaults
        profile_dict.setdefault("frequently_asked_questions", [])
        profile_dict.setdefault("common_expenses", [])
        profile_dict.setdefault("conversation_count", 0)
        profile_dict.setdefault("last_interaction", None)
        
        # Create or update profile in database
        profile = await db_svc.create_or_update_user_profile(profile_dict)
        
        if profile:
            return {"success": True, "profile": profile.dict()}
        else:
            return {"success": False, "message": "Failed to create profile"}
            
    except HTTPException:
        raise
    except Exception as e:
        get_logger(__name__).error(f"Create profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating profile: {str(e)}"
        )


@app.get("/user/learning")
async def get_user_learning(
    authorization: str = Header(None),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get user learning insights and profile summary."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user learning summary
        from src.tools.user_learning_tools import UserLearningTools
        from src.services.llm import LLMService
        
        llm_service = LLMService()
        learning_tools = UserLearningTools(db_svc, llm_service)
        learning_summary = await learning_tools.get_user_learning_summary(user.user_id)
        
        return {
            "success": True,
            "learning_summary": learning_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        get_logger(__name__).error(f"Get user learning error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user learning: {str(e)}"
        )


@app.get("/user/expenses")
async def get_user_expenses(
    authorization: str = Header(None),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get user expenses."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user expenses
        from src.tools.expense_tools import ExpenseTools
        expense_tools = ExpenseTools(db_svc)
        expenses = await expense_tools.read_expenses(user.user_id)
        
        # Get expense summary
        summary = await expense_tools.get_expense_summary(user.user_id)
        
        return {
            "success": True,
            "expenses": expenses,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        get_logger(__name__).error(f"Get user expenses error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user expenses: {str(e)}"
        )


@app.get("/user/dashboard-data")
async def get_user_dashboard_data(
    authorization: str = Header(None),
    auth_svc: AuthService = Depends(get_auth_service),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get comprehensive dashboard data for user."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        token = authorization.split(" ")[1]
        
        # Verify user token
        user = await auth_svc.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get all user data for dashboard
        from src.tools.expense_tools import ExpenseTools
        
        # User profile
        profile = await db_svc.get_user_profile(user.user_id)
        
        # Expenses
        expense_tools = ExpenseTools(db_svc)
        expenses = await expense_tools.read_expenses(user.user_id)
        expense_summary = await expense_tools.get_expense_summary(user.user_id)
        
        # Tax documents
        tax_documents = await db_svc.get_user_tax_documents(user.user_id)
        
        # Calculate tax estimates if profile exists
        tax_data = {}
        if profile and profile.annual_income:
            # Basic tax calculation
            income = profile.annual_income
            grundfreibetrag = 11604  # Basic allowance 2024
            taxable_income = max(0, income - grundfreibetrag)
            
            # Simplified tax calculation
            if taxable_income <= 0:
                income_tax = 0
            elif taxable_income <= 62810:
                income_tax = taxable_income * 0.14
            else:
                income_tax = 62810 * 0.14 + (taxable_income - 62810) * 0.42
            
            solidarity_surcharge = income_tax * 0.055
            church_tax = income_tax * 0.09
            total_tax = income_tax + solidarity_surcharge + church_tax
            
            tax_data = {
                "annual_income": income,
                "grundfreibetrag": grundfreibetrag,
                "taxable_income": taxable_income,
                "income_tax": income_tax,
                "solidarity_surcharge": solidarity_surcharge,
                "church_tax": church_tax,
                "total_tax": total_tax,
                "net_income": income - total_tax,
                "effective_tax_rate": (total_tax / income * 100) if income > 0 else 0
            }
        
        return {
            "success": True,
            "profile": profile.dict() if profile else None,
            "expenses": {
                "items": expenses,
                "summary": expense_summary
            },
            "tax_documents": [
                {
                    "id": doc.id,
                    "document_type": doc.document_type,
                    "year": doc.year,
                    "amount": doc.amount,
                    "description": doc.description,
                    "metadata": doc.metadata,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None
                } for doc in tax_documents
            ],
            "tax_calculations": tax_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        get_logger(__name__).error(f"Get dashboard data error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting dashboard data: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(
        "apps.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
