"""Chat routes."""

import asyncio
import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from src.core.logging import get_logger

from ..models import ChatMessage, ChatResponse
from ..dependencies import get_workflow, get_database_service, get_current_user
from src.workflow.graph import TaxFixWorkflow
from src.services.database import DatabaseService
from src.models.auth import UserSession

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    current_user: UserSession = Depends(get_current_user),
    workflow_instance: TaxFixWorkflow = Depends(get_workflow),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Send a message to the TaxFix assistant."""
    try:
        # Generate session ID if not provided
        session_id = message.session_id or f"session_{current_user.user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Get user profile
        user_profile = await db_svc.get_user_profile(current_user.user_id)
        
        # Process message through workflow
        response_data = await workflow_instance.process_message(
            user_message=message.message,
            session_id=session_id,
            user_id=current_user.user_id,
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
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.post("/message/stream")
async def send_message_stream(
    message: ChatMessage,
    current_user: UserSession = Depends(get_current_user),
    workflow_instance: TaxFixWorkflow = Depends(get_workflow),
    db_svc: DatabaseService = Depends(get_database_service)
):
    """Send a message to the TaxFix assistant with streaming response."""
    try:
        # Generate session ID if not provided
        session_id = message.session_id or f"session_{current_user.user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Get user profile
        user_profile = await db_svc.get_user_profile(current_user.user_id)
        
        # Process message through workflow
        response_data = await workflow_instance.process_message(
            user_message=message.message,
            session_id=session_id,
            user_id=current_user.user_id,
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
        logger.error(f"Streaming chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing streaming message: {str(e)}"
        )
