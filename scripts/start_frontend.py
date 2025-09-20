"""
Start TaxFix Frontend only.
"""
import subprocess
import sys

def main():
    """Start the frontend server."""
    print("🎨 Starting TaxFix Frontend...")
    print("=" * 40)
    
    try:
        # Start frontend
        subprocess.run([
            sys.executable, "-m", "streamlit", 
            "run", "apps/frontend/main.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
        
    except KeyboardInterrupt:
        print("\n🛑 Frontend stopped")

if __name__ == "__main__":
    main()
