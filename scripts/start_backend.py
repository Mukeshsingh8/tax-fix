"""
Start TaxFix Backend only (for LangGraph development).
"""
import subprocess
import sys
import time

def main():
    """Start the backend server."""
    print("🚀 Starting TaxFix Backend for LangGraph Development...")
    print("=" * 60)
    
    try:
        # Start backend
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "apps.backend.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
        
    except KeyboardInterrupt:
        print("\n🛑 Backend stopped")

if __name__ == "__main__":
    main()
