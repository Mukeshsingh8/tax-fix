"""
FastAPI backend for TaxFix Multi-Agent System.
"""
from contextlib import asynccontextmanager
from datetime import datetime
import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings, setup_langsmith_tracing
from src.core.logging import setup_logging, get_logger
from src.workflow.graph import build_workflow
from src.services.database import DatabaseService
from src.services.memory import MemoryService
from src.services.auth import AuthService

# Import routers
from .routers import auth, chat, user, conversations

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Import here to avoid circular imports
    from . import dependencies
    
    # Startup
    logger.info("Starting TaxFix API server")
    
    try:
        # Setup logging
        setup_logging("INFO")
        
        # Setup LangSmith tracing
        setup_langsmith_tracing()
        
        # Initialize services
        dependencies.database_service = DatabaseService()
        dependencies.memory_service = MemoryService()
        
        # Connect to Redis
        try:
            await dependencies.memory_service.connect()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Memory service will work without Redis.")
        
        dependencies.auth_service = AuthService(dependencies.database_service, dependencies.memory_service)
        
        # Initialize workflow
        dependencies.workflow = await build_workflow()
        
        logger.info("TaxFix API server started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start TaxFix API server: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down TaxFix API server")
        
        # Disconnect from Redis
        if dependencies.memory_service:
            try:
                await dependencies.memory_service.disconnect()
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

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(user.router)
app.include_router(conversations.router)


# Basic endpoints
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
    from . import dependencies
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "workflow": dependencies.workflow is not None,
            "database": dependencies.database_service is not None,
            "memory": dependencies.memory_service is not None,
            "auth": dependencies.auth_service is not None
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "apps.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
