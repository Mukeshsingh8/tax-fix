# 🚀 TaxFix Quick Start Guide

Get up and running with TaxFix in under 10 minutes!

## Prerequisites Checklist

- [ ] **Python 3.11+** installed
- [ ] **Git** installed  
- [ ] **Redis** server (document will help you install this)
- [ ] **Groq API Key** ([Get one here](https://console.groq.com/))
- [ ] **Supabase Account** ([Sign up here](https://supabase.com/)) -> I have attached the supabase keys in the Email (feel free to use that)

## 🎯 One-Command Setup

```bash
# Clone and run automated setup
git clone https://github.com/Mukeshsingh8/tax-fix.git
cd taxfix
python scripts/setup.py
```

The setup script will:
- ✅ Check Python version
- ✅ Install Redis if needed
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Set up configuration files
- ✅ Test connections

## 🔧 Manual Setup (Alternative)

### 1. Clone & Install

```bash
git clone https://github.com/Mukeshsingh8/tax-fix.git
cd taxfix

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Redis

**macOS (Homebrew):**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**Docker (Any OS):**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 3. Configure Environment

```bash
# Copy example configuration
cp config/env.example .env

# Edit with your API keys
nano .env  # or use your preferred editor
```

**Required Configuration:**
```bash
# Get from https://console.groq.com/
GROQ_API_KEY=your_groq_api_key_here

# Get from your Supabase project
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Redis (default for local)
REDIS_URL=redis://localhost:6379
```

### 4. Set Up Database

1. Go to your **Supabase project dashboard**
2. Open **SQL Editor**
3. Copy contents of `supabase_schema.sql`
4. Execute the SQL to create tables

### 5. Run the Application

```bash
# Option 1: Using scripts (recommended)
python scripts/start_app.py

# Option 2: Using Makefile
make dev

# Option 3: Manual start (two terminals)
# Terminal 1:
python scripts/start_backend.py

# Terminal 2:
python scripts/start_frontend.py
```

## 🌐 Access Your Application

- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🎉 First Steps

1. **Register Account**: Create your user account
2. **Complete Profile**: Add your tax information
3. **Ask Questions**: Try "What deductions can I claim?"
4. **Track Expenses**: Add some expenses to test functionality

## 🐳 Docker Quick Start (Alternative)

```bash
# Clone repository
git clone https://github.com/your-username/taxfix.git
cd taxfix

# Create .env file with your API keys
cp config/env.example .env
# Edit .env with your keys

# Start with Docker Compose
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

## ❓ Having Issues?

### Redis Connection Error
```bash
# Test Redis
redis-cli ping  # Should return "PONG"

# If not working:
brew services restart redis  # macOS
sudo systemctl restart redis-server  # Linux
```

### API Key Errors
- Verify your Groq API key at https://console.groq.com/
- Check Supabase keys in your project settings
- Ensure `.env` file has no extra spaces

### Import Errors
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies if needed
pip install -r requirements.txt
```

### Database Issues
- Verify Supabase URL and keys
- Check if database schema was created
- Test connection in Supabase dashboard

## 🔗 Quick Links

- [📖 Full Documentation](README.md)
- [🏗️ Architecture Guide](docs/PROJECT_STRUCTURE.md)
- [🛠️ Development Guide](docs/FRONTEND_GUIDE.md)
- [❓ Troubleshooting](README.md#troubleshooting)

## 💬 Need Help?

- **Issues**: [GitHub Issues](https://github.com/your-username/taxfix/issues)
- **Questions**: [GitHub Discussions](https://github.com/your-username/taxfix/discussions)

---

**Ready to go? Run `python scripts/setup.py` and start building! 🚀**
