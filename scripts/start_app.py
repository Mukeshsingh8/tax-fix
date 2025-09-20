"""
Startup script for TaxFix Multi-Agent System.
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def check_requirements():
    """Check if required packages are installed."""
    required_packages = [
        'streamlit', 'fastapi', 'uvicorn', 'requests', 
        'plotly', 'pandas', 'streamlit-option-menu'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install them with: pip install -r requirements.txt")
        return False
    
    return True

def start_backend():
    """Start the FastAPI backend."""
    print("🚀 Starting TaxFix Backend...")
    try:
        # Start backend in background
        backend_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "apps.backend.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for backend to start
        time.sleep(3)
        
        # Check if backend is running
        if backend_process.poll() is None:
            print("✅ Backend started successfully on http://localhost:8000")
            return backend_process
        else:
            print("❌ Backend failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return None

def start_frontend():
    """Start the Streamlit frontend."""
    print("🎨 Starting TaxFix Frontend...")
    try:
        # Start frontend
        frontend_process = subprocess.Popen([
            sys.executable, "-m", "streamlit", 
            "run", "apps/frontend/main.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
        
        print("✅ Frontend started successfully on http://localhost:8501")
        return frontend_process
        
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        return None

def main():
    """Main startup function."""
    print("💰 TaxFix Multi-Agent System Startup")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("⚠️  .env file not found. Please copy config/env.example to .env and configure it.")
        sys.exit(1)
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        sys.exit(1)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        backend_process.terminate()
        sys.exit(1)
    
    print("\n🎉 TaxFix is now running!")
    print("📱 Frontend: http://localhost:8501")
    print("🔧 Backend API: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop both services")
    
    try:
        # Wait for processes
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("❌ Backend process stopped unexpectedly")
                break
            
            if frontend_process.poll() is not None:
                print("❌ Frontend process stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down TaxFix...")
        
        # Terminate processes
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        
        print("✅ TaxFix stopped successfully")

if __name__ == "__main__":
    main()
