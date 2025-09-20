# TaxFix Multi-Agent System

A production-grade multi-agent system for personalized German tax advisory services, built with LangGraph, FastAPI, and Streamlit. This system provides intelligent tax calculations, personalized advice, and comprehensive German tax knowledge through specialized AI agents.

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (Required for LangGraph compatibility)
- **Redis Server** (For memory management and caching)
- **Supabase Account** (For database and authentication)
- **API Keys** (Groq, Google Gemini, LangSmith)

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd taxfix

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
cp config/env.example .env
# Edit .env with your API keys and configuration (see Environment Configuration below)
```

### Environment Configuration

Create a `.env` file in the root directory with the following variables:

```bash
# LangSmith Tracing (Optional but recommended for development)
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=TaxFix-MultiAgent

# LLM Providers (At least one required)
GROQ_API_KEY=your_groq_api_key          # Recommended for fast responses
GOOGLE_API_KEY=your_google_api_key      # For Gemini model

# Database Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password  # If Redis is password protected

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
```

### Database Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com)
2. **Run the database schema**:
   ```bash
   # Option 1: Using Supabase CLI
   supabase db reset
   
   # Option 2: Using SQL file directly
   # Copy the contents of supabase_schema_minimal.sql and run in Supabase SQL editor
   ```

3. **Enable Row Level Security (RLS)** on all tables in Supabase dashboard

### Redis Setup

```bash
# Install Redis (macOS with Homebrew)
brew install redis

# Start Redis server
brew services start redis

# Or start manually
redis-server

# Test Redis connection
redis-cli ping  # Should return "PONG"
```

## 🏃‍♂️ Running the Application

### Option 1: Full Application (Recommended)

```bash
# Start both backend and frontend
python scripts/start_app.py
```

This will start:
- **Backend API**: FastAPI server on http://localhost:8000
- **Frontend**: Streamlit app on http://localhost:8501
- **API Documentation**: http://localhost:8000/docs

### Option 2: Individual Services

```bash
# Terminal 1: Start backend
source venv/bin/activate
python scripts/start_backend.py

# Terminal 2: Start frontend
source venv/bin/activate
python scripts/start_frontend.py
```

### Option 3: LangGraph Development Server

```bash
# For LangGraph workflow development and debugging
langgraph dev
```

This provides:
- Interactive graph visualization
- Real-time workflow execution
- Debug tools and breakpoints
- Performance metrics

## 🏗️ Architecture Overview

### Multi-Agent System

The system uses a sophisticated multi-agent workflow orchestrated by LangGraph:

```
User Input → Orchestrator → Specialized Agents → Synthesizer → Response
```

### Core Agents

#### 1. 🎯 **Orchestrator Agent** (`src/agents/orchestrator.py`)
- **Purpose**: Central coordinator that analyzes user input and routes to appropriate agents
- **Responsibilities**:
  - Intent classification (tax calculation, general advice, profile updates)
  - Agent selection and routing
  - Workflow orchestration
  - Response synthesis

#### 2. 👤 **Profile Agent** (`src/agents/profile.py`)
- **Purpose**: Manages user profile information and updates
- **Responsibilities**:
  - User profile creation and updates
  - Income and filing status management
  - Dependents and family information
  - Health insurance type tracking

#### 3. 📚 **Tax Knowledge Agent** (`src/agents/tax_knowledge.py`)
- **Purpose**: Provides comprehensive German tax information and calculations
- **Responsibilities**:
  - German tax law explanations
  - Tax calculation with health insurance contributions
  - Deduction identification and recommendations
  - Social security contribution calculations

#### 4. 🧠 **Memory Agent** (`src/agents/memory.py`)
- **Purpose**: Manages conversation context and user history
- **Responsibilities**:
  - Conversation history storage
  - Context retrieval and management
  - User preference learning
  - Session management

### Core Services

#### 1. **LLM Service** (`src/services/llm.py`)
- **Providers**: Groq (Llama), Google Gemini
- **Features**: Model selection, response streaming, error handling

#### 2. **Database Service** (`src/services/database.py`)
- **Backend**: Supabase PostgreSQL
- **Features**: User management, conversation storage, profile persistence

#### 3. **Memory Service** (`src/services/memory.py`)
- **Backend**: Redis
- **Features**: Session caching, conversation context, temporary storage

#### 4. **Vector Service** (`src/services/vector.py`)
- **Backend**: ChromaDB with SentenceTransformers
- **Features**: Tax knowledge retrieval, semantic search, RAG implementation

#### 5. **Tax Knowledge Service** (`src/services/tax_knowledge_service.py`)
- **Purpose**: German tax calculations and rules
- **Features**:
  - Progressive tax rate calculations
  - Health insurance contribution calculations (statutory/private)
  - Long-term care insurance calculations
  - Social security contribution ceilings
  - Deduction and allowance calculations

### Tools

#### 1. **User Tools** (`src/tools/user_tools.py`)
- `get_user_profile`: Retrieve user profile information
- `update_user_profile`: Update user profile data
- `create_user_profile`: Create new user profile

#### 2. **Conversation Tools** (`src/tools/conversation_tools.py`)
- `get_conversation_history`: Retrieve conversation history
- `save_conversation`: Save conversation messages
- `get_user_conversations`: List user conversations

#### 3. **User Learning Tools** (`src/tools/user_learning_tools.py`)
- `get_user_learning_preferences`: Retrieve user preferences
- `update_learning_progress`: Track learning progress
- `get_recommended_content`: Suggest relevant content

## 📊 Key Features

### Backend Features

#### Multi-Agent Architecture
- **Specialized Agents**: Each agent has a specific role and expertise
- **LangGraph Orchestration**: Production-grade workflow management
- **Agent Communication**: Seamless inter-agent communication
- **Error Handling**: Robust error handling and recovery

#### German Tax System
- **Comprehensive Calculations**: Income tax, solidarity surcharge, church tax
- **Health Insurance**: Statutory and private health insurance contributions
- **Long-term Care**: Pflegeversicherung with childless surcharges
- **Social Security**: Contribution assessment ceilings and rates
- **Deductions**: Werbungskosten, Sonderausgaben, allowances

#### Production Features
- **LangSmith Tracing**: Complete observability and debugging
- **Redis Caching**: Fast response times and session management
- **Supabase Integration**: Secure authentication and data persistence
- **API Documentation**: Auto-generated OpenAPI documentation
- **Streaming Responses**: Real-time response streaming

### Frontend Features

#### Authentication & User Management
- **Secure Login/Registration**: JWT-based authentication with Supabase
- **Profile Management**: Complete user profile setup and updates
- **Session Management**: Persistent user sessions

#### Chat Interface
- **ChatGPT-like Experience**: Beautiful, responsive chat interface
- **Streaming Responses**: Real-time response streaming with proper formatting
- **Conversation History**: Persistent conversation storage
- **Markdown Rendering**: Rich text formatting for tax calculations

#### Tax Dashboard
- **Interactive Visualizations**: Income, taxes, and savings breakdowns
- **Real-time Calculations**: Live tax calculations as you type
- **Deduction Recommendations**: Personalized deduction suggestions
- **Export Features**: Download tax summaries and reports

## 🔍 Development & Debugging

### LangSmith Integration

With LangSmith tracing enabled, you can:

- **View Complete Workflows**: See every agent execution step-by-step
- **Debug Agent Interactions**: Step through the workflow with breakpoints
- **Monitor Performance**: Track execution times and token usage
- **Trace Errors**: Identify and debug issues in the workflow
- **Optimize Costs**: Monitor token usage and optimize prompts

Visit [LangSmith Dashboard](https://smith.langchain.com) to view your traces.

### Testing the System

```bash
# Test the workflow
python -c "
from src.workflow.graph import build_graph
graph = build_graph()
print('✅ Graph built successfully')
"

# Test individual services
python -c "
from src.services.tax_knowledge_service import TaxKnowledgeService
service = TaxKnowledgeService()
result = service.calculate_german_tax(80000, 'single', 0)
print('✅ Tax calculation working:', result.get('net_income', 'N/A'))
"
```

### API Testing

```bash
# Test the API endpoints
curl -X GET "http://localhost:8000/health"
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is my tax liability with €80,000 income?"}'
```

## 📁 Project Structure

```
taxfix/
├── apps/                          # Application entry points
│   ├── backend/                   # FastAPI backend
│   │   └── main.py               # Backend server
│   └── frontend/                  # Streamlit frontend
│       └── main.py               # Frontend application
├── config/                        # Configuration files
│   ├── env.example               # Environment variables template
│   └── langgraph.json           # LangGraph configuration
├── docs/                          # Documentation
│   ├── README.md                 # This file
│   ├── PROJECT_STRUCTURE.md      # Detailed project structure
│   └── FRONTEND_GUIDE.md         # Frontend development guide
├── scripts/                       # Utility scripts
│   ├── start_app.py              # Start full application
│   ├── start_backend.py          # Start backend only
│   ├── start_frontend.py         # Start frontend only
│   └── setup_auth_simple.sql     # Database setup
├── src/                           # Source code
│   ├── agents/                   # AI agents
│   │   ├── base.py              # Base agent class
│   │   ├── orchestrator.py      # Central coordinator
│   │   ├── profile.py           # User profile management
│   │   ├── tax_knowledge.py     # Tax information provider
│   │   └── memory.py            # Memory management
│   ├── core/                     # Core system components
│   │   ├── config.py            # Configuration management
│   │   ├── logging.py           # Logging system
│   │   ├── state.py             # LangGraph state management
│   │   └── helpers.py           # Utility functions
│   ├── data/                     # Static data
│   │   └── german_tax_data.py   # German tax rules and data
│   ├── models/                   # Data models
│   │   ├── user.py              # User and profile models
│   │   ├── conversation.py      # Conversation models
│   │   ├── auth.py              # Authentication models
│   │   └── tax_knowledge.py     # Tax knowledge models
│   ├── services/                 # Core services
│   │   ├── llm.py               # LLM integration
│   │   ├── memory.py            # Redis memory service
│   │   ├── database.py          # Supabase database service
│   │   ├── vector.py            # Vector database service
│   │   ├── auth.py              # Authentication service
│   │   └── tax_knowledge_service.py # Tax calculation service
│   ├── tools/                    # Agent tools
│   │   ├── user_tools.py        # User profile tools
│   │   ├── conversation_tools.py # Conversation management tools
│   │   └── user_learning_tools.py # Learning and preferences tools
│   └── workflow/                 # LangGraph workflow
│       └── graph.py             # Main workflow orchestration
├── requirements.txt              # Python dependencies
├── Makefile                      # Build and development commands
└── supabase_schema_minimal.sql   # Database schema
```

## 🎯 Production Benefits

1. **Easy Debugging**: LangSmith traces show exactly what happens in each agent
2. **Interactive Development**: Visual workflow editing with LangGraph
3. **Hot Reload**: Changes reflect immediately during development
4. **Production Ready**: Clean codebase with comprehensive error handling
5. **Comprehensive Monitoring**: Full observability with LangSmith
6. **Secure & Scalable**: JWT authentication and modular architecture
7. **Real-time Streaming**: Fast, responsive user experience
8. **German Tax Accuracy**: Comprehensive German tax system implementation

## 🚨 Troubleshooting

### Common Issues

#### 1. Redis Connection Error
```bash
# Check if Redis is running
redis-cli ping

# Start Redis if not running
brew services start redis  # macOS
sudo systemctl start redis  # Linux
```

#### 2. Supabase Connection Error
- Verify your Supabase URL and keys in `.env`
- Check if RLS is enabled on all tables
- Ensure your Supabase project is active

#### 3. LangSmith Tracing Issues
- Verify your LangChain API key
- Check if the project name exists in LangSmith
- Ensure `LANGCHAIN_TRACING_V2=true` is set

#### 4. Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### 5. Frontend Streaming Issues
- Check browser console for JavaScript errors
- Verify backend is running on port 8000
- Ensure WebSocket connections are not blocked

### Performance Optimization

1. **Redis Configuration**: Increase Redis memory limits for better caching
2. **Vector Database**: Use GPU acceleration for embeddings if available
3. **LLM Selection**: Use Groq for faster responses, Gemini for complex reasoning
4. **Database Indexing**: Add indexes on frequently queried columns

## 📚 Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Redis Documentation](https://redis.io/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ using LangGraph, LangChain, FastAPI, Streamlit, and modern Python technologies.**

**TaxFix - Making German tax calculations simple and intelligent.**
