# TaxFix Project Structure

## 📁 Directory Organization

```
taxfix/
├── 📁 apps/                    # Application modules
│   ├── 📁 backend/            # FastAPI backend application
│   │   ├── __init__.py
│   │   └── main.py           # Main FastAPI app
│   └── 📁 frontend/           # Streamlit frontend application
│       ├── __init__.py
│       └── main.py           # Main Streamlit app
├── 📁 config/                 # Configuration files
│   ├── __init__.py
│   ├── env.example           # Environment variables template
│   └── langgraph.json        # LangGraph configuration
├── 📁 docs/                   # Documentation
│   ├── __init__.py
│   ├── FRONTEND_GUIDE.md     # Frontend development guide
│   ├── PROJECT_STRUCTURE.md  # This file
│   └── README.md             # Main project documentation
├── 📁 scripts/                # Utility scripts
│   ├── setup_auth_simple.sql # Database setup script
│   ├── start_app.py          # Start both frontend and backend
│   ├── start_backend.py      # Start backend only
│   └── start_frontend.py     # Start frontend only
├── 📁 src/                    # Source code
│   ├── 📁 agents/            # AI agents
│   ├── 📁 core/              # Core utilities
│   ├── 📁 data/              # Data models and sources
│   ├── 📁 models/            # Pydantic models
│   ├── 📁 services/          # Business logic services
│   ├── 📁 tools/             # Agent tools
│   └── 📁 workflow/          # LangGraph workflow
├── 📁 venv/                   # Virtual environment (not in git)
├── requirements.txt           # Python dependencies
└── .env                      # Environment variables (not in git)
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Copy environment template
cp config/env.example .env

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Applications

#### Start Both Frontend and Backend
```bash
python scripts/start_app.py
```

#### Start Backend Only
```bash
python scripts/start_backend.py
```

#### Start Frontend Only
```bash
python scripts/start_frontend.py
```

### 3. Access Applications
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📋 Key Components

### Applications (`apps/`)
- **Backend**: FastAPI REST API with multi-agent workflow
- **Frontend**: Streamlit web interface for user interaction

### Configuration (`config/`)
- **env.example**: Template for environment variables
- **langgraph.json**: LangGraph workflow configuration

### Scripts (`scripts/`)
- **start_app.py**: Orchestrates both frontend and backend
- **start_backend.py**: Backend-only startup
- **start_frontend.py**: Frontend-only startup
- **setup_auth_simple.sql**: Database initialization

### Source Code (`src/`)
- **agents/**: AI agents (orchestrator, tax knowledge, profile, etc.)
- **core/**: Core utilities (config, logging, state management)
- **services/**: Business logic (database, LLM, memory, vector)
- **workflow/**: LangGraph multi-agent workflow

## 🔧 Development

### Adding New Features
1. **Backend**: Add to `apps/backend/main.py`
2. **Frontend**: Add to `apps/frontend/main.py`
3. **Agents**: Add to `src/agents/`
4. **Services**: Add to `src/services/`

### Configuration
- Environment variables: `.env` (copy from `config/env.example`)
- LangGraph config: `config/langgraph.json`

### Database
- Setup script: `scripts/setup_auth_simple.sql`
- Models: `src/models/`

## 🧹 Production Readiness

### Code Quality
- **✅ Clean Codebase**: All test endpoints and debugging code removed
- **✅ Production Endpoints**: Only authenticated, production-ready API endpoints
- **✅ Proper Authentication**: JWT-based authentication for all protected routes
- **✅ Error Handling**: Comprehensive error handling and logging
- **✅ Security**: Row-level security (RLS) enabled on all database tables

### Testing Status
- **✅ Backend**: Successfully tested and running on port 8000
- **✅ Frontend**: Successfully tested and running on port 8501
- **✅ API Integration**: Frontend properly connected to backend with authentication
- **✅ Database**: Supabase schema properly configured with all required tables

## 📚 Documentation
- **README.md**: Main project overview
- **FRONTEND_GUIDE.md**: Frontend development guide
- **PROJECT_STRUCTURE.md**: This file