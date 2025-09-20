# TaxFix Multi-Agent System

A production-grade multi-agent system for personalized German tax advisory services, built with LangGraph and LangSmith.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Redis server
- Supabase account and project

### Installation

```bash
# Clone repository
git clone <repository-url>
cd taxfix

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp config/env.example .env
# Edit .env with your API keys and configuration
```

### Environment Configuration

```bash
# LangSmith Tracing
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=TaxFix-MultiAgent

# LLM Providers
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key

# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_SERVICE_KEY=your_service_key

# Redis
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password
```

### Database Setup

```bash
# Run the database setup script
psql -h your_host -U your_user -d your_database -f scripts/setup_auth_simple.sql
```

### Development

#### Option 1: Full Application (Backend + Frontend)
```bash
# Start both backend and frontend
python scripts/start_app.py
```

This will start:
- **Backend API**: FastAPI server on http://localhost:8000
- **Frontend**: Streamlit app on http://localhost:8501
- **API Documentation**: http://localhost:8000/docs

#### Option 2: LangGraph Development Only
```bash
# Start LangGraph development server
langgraph dev
```

This will start the LangGraph development server with:
- **Graph Visualization**: Interactive workflow visualization
- **LangSmith Tracing**: Complete observability
- **Hot Reload**: Automatic reload on code changes
- **Debug Tools**: Step-through debugging

#### Option 3: Individual Services
```bash
# Start backend only
python scripts/start_backend.py

# Start frontend only (in another terminal)
python scripts/start_frontend.py
```

## 🏗️ Architecture

### Core Components

```
src/
├── core/                    # Core system components
│   ├── config.py           # Configuration management
│   ├── logging.py          # Logging system
│   └── state.py            # LangGraph state management
├── workflow/               # LangGraph workflow
│   └── graph.py           # Main workflow orchestration
├── agents/                 # Specialized agents
│   ├── base.py            # Base agent class
│   ├── orchestrator.py    # Central coordinator
│   ├── profile.py         # User profile management
│   ├── tax_knowledge.py   # Tax information provider
│   ├── tax_advisor.py     # Personalized tax advisor
│   ├── memory.py          # Memory management
│   └── action.py          # Action suggestions
├── services/               # Core services
│   ├── llm.py             # LLM integration
│   ├── memory.py          # Redis memory service
│   ├── database.py        # Supabase database service
│   ├── vector.py          # Vector database service
│   └── auth.py            # Authentication service
├── tools/                  # Agent tools
│   ├── user_tools.py      # User profile tools
│   ├── memory_tools.py    # Memory management tools
│   └── tax_tools.py       # Tax calculation tools
├── models/                 # Data models
│   ├── user.py            # User and profile models
│   ├── conversation.py    # Conversation models
│   ├── auth.py            # Authentication models
│   └── tax_knowledge.py   # Tax knowledge models
└── data/                   # Tax knowledge data
    └── german_tax_data.py # German tax rules and data
```

### Multi-Agent Workflow

The system uses a sophisticated multi-agent workflow:

1. **🎯 Orchestrator**: Analyzes user input and routes to appropriate agents
2. **👤 Profile**: Manages user profile updates and confirmations
3. **📚 Tax Knowledge**: Provides general tax information
4. **💼 Tax Advisor**: Delivers personalized tax analysis
5. **🧠 Memory**: Manages conversation context
6. **⚡ Action**: Suggests specific actions
7. **🔗 Synthesize**: Creates final response

## 🔍 LangSmith Integration

With LangSmith tracing enabled, you can:

- **View Complete Workflows**: See every agent execution
- **Debug Agent Interactions**: Step through the workflow
- **Monitor Performance**: Track execution times and token usage
- **Trace Errors**: Identify issues in the workflow

Visit [LangSmith Dashboard](https://smith.langchain.com) to view your traces.

## 🛠️ Development

### LangGraph Dev Server

```bash
langgraph dev
```

The LangGraph dev server provides:
- Interactive graph visualization
- Real-time workflow execution
- Debug tools and breakpoints
- Performance metrics

### Testing

```bash
# Test the workflow
python -c "
from src.workflow.graph import build_graph
graph = build_graph()
print('✅ Graph built successfully')
"
```

## 📊 Key Features

### Backend Features
- **Multi-Agent Architecture**: Specialized agents working together
- **LangGraph Orchestration**: Production-grade workflow management
- **LangSmith Tracing**: Comprehensive observability
- **Profile-Aware Interactions**: Personalized user experiences
- **Real-time Memory Management**: Redis + Supabase integration
- **Clean Architecture**: Modular, maintainable code
- **Production-Ready**: No test endpoints, clean codebase
- **Secure Authentication**: JWT-based authentication with Supabase

### Frontend Features
- **🔐 Authentication**: Secure login/registration with Supabase
- **💬 ChatGPT-like Interface**: Beautiful chat interface with conversation history
- **📊 Tax Dashboard**: Interactive visualizations of income, taxes, and savings
- **👤 Profile Management**: Complete user profile management
- **📱 Responsive Design**: Works on desktop and mobile
- **🎨 Modern UI**: Beautiful, user-friendly interface with gradients and animations

## 🎯 Production Benefits

1. **Easy Debugging**: LangSmith traces show exactly what happens
2. **Interactive Development**: Visual workflow editing
3. **Hot Reload**: Changes reflect immediately
4. **Production Ready**: Clean codebase with no test endpoints
5. **Comprehensive Monitoring**: Full observability
6. **Secure & Scalable**: JWT authentication and modular architecture

## 📚 Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Redis Documentation](https://redis.io/docs/)

---

**Built with ❤️ using LangGraph, LangChain, and modern Python technologies.**