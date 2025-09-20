"""User-related routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from src.core.logging import get_logger

from ..models import CreateProfileRequest
from ..dependencies import get_database_service, get_current_user
from src.services.database import DatabaseService
from src.models.auth import UserSession

logger = get_logger(__name__)
router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile")
async def get_user_profile(
    current_user: UserSession = Depends(get_current_user),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get user profile."""
    try:
        # Get user profile
        profile = await db_svc.get_user_profile(current_user.user_id)
        if profile:
            return {"success": True, "profile": profile.dict()}
        else:
            return {"success": False, "message": "Profile not found"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting profile: {str(e)}"
        )


@router.post("/profile")
async def create_user_profile(
    profile_data: CreateProfileRequest,
    current_user: UserSession = Depends(get_current_user),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Create or update user profile."""
    try:
        # Create profile data
        profile_dict = profile_data.dict()
        profile_dict["user_id"] = current_user.user_id
        
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
        logger.error(f"Create profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating profile: {str(e)}"
        )


@router.get("/conversations")
async def get_user_conversations(
    current_user: UserSession = Depends(get_current_user),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get user conversation history."""
    try:
        # Get conversations
        conversations = await db_svc.get_user_conversations(current_user.user_id)
        
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
        logger.error(f"Get conversations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting conversations: {str(e)}"
        )


@router.get("/learning")
async def get_user_learning(
    current_user: UserSession = Depends(get_current_user),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get user learning insights and profile summary."""
    try:
        # Get user learning summary
        from src.tools.user_learning_tools import UserLearningTools
        from src.services.llm import LLMService
        
        llm_service = LLMService()
        learning_tools = UserLearningTools(db_svc, llm_service)
        learning_summary = await learning_tools.get_user_learning_summary(current_user.user_id)
        
        return {
            "success": True,
            "learning_summary": learning_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user learning error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user learning: {str(e)}"
        )


@router.get("/expenses")
async def get_user_expenses(
    current_user: UserSession = Depends(get_current_user),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get user expenses."""
    try:
        # Get user expenses
        from src.tools.expense_tools import ExpenseTools
        expense_tools = ExpenseTools(db_svc)
        expenses = await expense_tools.read_expenses(current_user.user_id)
        
        # Get expense summary
        summary = await expense_tools.get_expense_summary(current_user.user_id)
        
        return {
            "success": True,
            "expenses": expenses,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user expenses error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user expenses: {str(e)}"
        )


@router.get("/dashboard-data")
async def get_user_dashboard_data(
    current_user: UserSession = Depends(get_current_user),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Get comprehensive dashboard data for user."""
    try:
        # Get all user data for dashboard
        from src.tools.expense_tools import ExpenseTools
        
        # User profile
        profile = await db_svc.get_user_profile(current_user.user_id)
        
        # Expenses
        expense_tools = ExpenseTools(db_svc)
        expenses = await expense_tools.read_expenses(current_user.user_id)
        expense_summary = await expense_tools.get_expense_summary(current_user.user_id)
        
        # Tax documents
        tax_documents = await db_svc.get_user_tax_documents(current_user.user_id)
        
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
        logger.error(f"Get dashboard data error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting dashboard data: {str(e)}"
        )
