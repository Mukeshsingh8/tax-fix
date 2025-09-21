#!/usr/bin/env python3
"""
TaxFix Multi-Agent System Setup Script
=====================================

This script helps you set up the TaxFix system step by step.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import platform


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_colored(message, color=Colors.WHITE):
    """Print colored message to terminal."""
    print(f"{color}{message}{Colors.END}")


def print_header(title):
    """Print a formatted header."""
    print_colored("\n" + "="*60, Colors.CYAN)
    print_colored(f"  {title}", Colors.BOLD + Colors.CYAN)
    print_colored("="*60, Colors.CYAN)


def print_step(step_num, description):
    """Print a step description."""
    print_colored(f"\n{step_num}. {description}", Colors.BOLD + Colors.BLUE)


def print_success(message):
    """Print success message."""
    print_colored(f"✅ {message}", Colors.GREEN)


def print_warning(message):
    """Print warning message."""
    print_colored(f"⚠️  {message}", Colors.YELLOW)


def print_error(message):
    """Print error message."""
    print_colored(f"❌ {message}", Colors.RED)


def run_command(command, check=True, shell=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            command, 
            shell=shell, 
            check=check, 
            capture_output=True, 
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def check_python_version():
    """Check if Python version is 3.11+."""
    print_step(1, "Checking Python version")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} is supported")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor}.{version.micro} is not supported")
        print_error("Please install Python 3.11 or higher")
        return False


def check_redis():
    """Check if Redis is installed and running."""
    print_step(2, "Checking Redis installation")
    
    # Check if redis-cli is available
    success, _, _ = run_command("redis-cli --version", check=False)
    if not success:
        print_warning("Redis is not installed")
        install_redis()
        return False
    
    # Check if Redis is running
    success, _, _ = run_command("redis-cli ping", check=False)
    if success:
        print_success("Redis is installed and running")
        return True
    else:
        print_warning("Redis is installed but not running")
        start_redis()
        return True


def install_redis():
    """Install Redis based on the operating system."""
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        print_colored("Installing Redis on macOS using Homebrew...", Colors.YELLOW)
        success, _, _ = run_command("brew install redis", check=False)
        if success:
            print_success("Redis installed successfully")
            start_redis()
        else:
            print_error("Failed to install Redis. Please install Homebrew first.")
            print_colored("Visit: https://brew.sh/", Colors.CYAN)
    
    elif system == "linux":
        print_colored("Installing Redis on Linux...", Colors.YELLOW)
        # Try apt-get first (Ubuntu/Debian)
        success, _, _ = run_command("sudo apt update && sudo apt install -y redis-server", check=False)
        if success:
            print_success("Redis installed successfully")
            run_command("sudo systemctl start redis-server", check=False)
            run_command("sudo systemctl enable redis-server", check=False)
        else:
            print_error("Failed to install Redis. Please install manually.")
    
    else:
        print_error("Automatic Redis installation not supported on this OS")
        print_colored("Please install Redis manually:", Colors.CYAN)
        print_colored("- Windows: https://redis.io/download", Colors.CYAN)
        print_colored("- Or use Docker: docker run -d -p 6379:6379 redis:7-alpine", Colors.CYAN)


def start_redis():
    """Start Redis service."""
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        success, _, _ = run_command("brew services start redis", check=False)
        if success:
            print_success("Redis started successfully")
        else:
            print_warning("Could not start Redis automatically")
    
    elif system == "linux":
        success, _, _ = run_command("sudo systemctl start redis-server", check=False)
        if success:
            print_success("Redis started successfully")
        else:
            print_warning("Could not start Redis automatically")


def setup_virtual_environment():
    """Set up Python virtual environment."""
    print_step(3, "Setting up virtual environment")
    
    if os.path.exists("venv"):
        print_success("Virtual environment already exists")
        return True
    
    success, _, stderr = run_command("python3 -m venv venv")
    if success:
        print_success("Virtual environment created successfully")
        return True
    else:
        print_error(f"Failed to create virtual environment: {stderr}")
        return False


def install_dependencies():
    """Install Python dependencies."""
    print_step(4, "Installing Python dependencies")
    
    # Determine the activation script based on OS
    if platform.system().lower() == "windows":
        activate_script = "venv\\Scripts\\activate"
        pip_command = "venv\\Scripts\\pip"
    else:
        activate_script = "source venv/bin/activate"
        pip_command = "venv/bin/pip"
    
    # Upgrade pip first
    success, _, stderr = run_command(f"{pip_command} install --upgrade pip")
    if not success:
        print_error(f"Failed to upgrade pip: {stderr}")
        return False
    
    # Install requirements
    success, _, stderr = run_command(f"{pip_command} install -r requirements.txt")
    if success:
        print_success("Dependencies installed successfully")
        return True
    else:
        print_error(f"Failed to install dependencies: {stderr}")
        return False


def setup_environment_file():
    """Set up .env configuration file."""
    print_step(5, "Setting up environment configuration")
    
    if os.path.exists(".env"):
        print_success(".env file already exists")
        return True
    
    if os.path.exists("config/env.example"):
        shutil.copy("config/env.example", ".env")
        print_success("Created .env file from template")
        print_warning("Please edit .env file with your API keys and configuration")
        return True
    else:
        print_error("config/env.example not found")
        return False


def check_api_keys():
    """Check if API keys are configured."""
    print_step(6, "Checking API key configuration")
    
    if not os.path.exists(".env"):
        print_warning(".env file not found")
        return False
    
    required_keys = ["GROQ_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    missing_keys = []
    
    with open(".env", "r") as f:
        content = f.read()
        for key in required_keys:
            if f"{key}=" not in content or f"{key}=your_" in content or f"{key}=" in content and content.split(f"{key}=")[1].split("\n")[0].strip() == "":
                missing_keys.append(key)
    
    if missing_keys:
        print_warning(f"Missing or placeholder API keys: {', '.join(missing_keys)}")
        print_colored("\nPlease configure the following:", Colors.CYAN)
        print_colored("- GROQ_API_KEY: Get from https://console.groq.com/", Colors.CYAN)
        print_colored("- SUPABASE_URL & SUPABASE_KEY: Get from https://supabase.com/", Colors.CYAN)
        return False
    else:
        print_success("API keys appear to be configured")
        return True


def test_connections():
    """Test connections to external services."""
    print_step(7, "Testing service connections")
    
    # Test Redis connection
    success, output, _ = run_command("redis-cli ping", check=False)
    if success and "PONG" in output:
        print_success("Redis connection: OK")
    else:
        print_warning("Redis connection: Failed")
    
    # Note: We can't easily test Supabase/Groq without running the app
    print_colored("Note: Supabase and Groq connections will be tested when you run the app", Colors.CYAN)


def create_database_schema():
    """Provide instructions for database schema setup."""
    print_step(8, "Database schema setup")
    
    schema_files = ["supabase_schema.sql", "scripts/supabase_schema.sql"]
    schema_file = None
    
    for file_path in schema_files:
        if os.path.exists(file_path):
            schema_file = file_path
            break
    
    if schema_file:
        print_success("Database schema file found")
        print_colored("\nTo set up your database:", Colors.CYAN)
        print_colored("1. Go to your Supabase project dashboard", Colors.CYAN)
        print_colored("2. Open the SQL Editor", Colors.CYAN)
        print_colored(f"3. Copy and run the contents of {schema_file}", Colors.CYAN)
        print_colored("4. This will create all necessary tables", Colors.CYAN)
        return True
    else:
        print_error("Database schema file not found")
        return False


def final_instructions():
    """Display final setup instructions."""
    print_header("Setup Complete!")
    
    print_colored("\n🎉 TaxFix setup is complete!", Colors.GREEN + Colors.BOLD)
    print_colored("\nNext steps:", Colors.CYAN)
    print_colored("1. Configure your .env file with API keys", Colors.WHITE)
    print_colored("2. Set up your Supabase database schema", Colors.WHITE)
    print_colored("3. Start the application:", Colors.WHITE)
    print_colored("   make dev  # or python scripts/start_app.py", Colors.MAGENTA)
    print_colored("\nApplication URLs:", Colors.CYAN)
    print_colored("- Frontend: http://localhost:8501", Colors.WHITE)
    print_colored("- Backend API: http://localhost:8000", Colors.WHITE)
    print_colored("- API Docs: http://localhost:8000/docs", Colors.WHITE)
    
    print_colored("\nFor help:", Colors.CYAN)
    print_colored("- Read the README.md for detailed documentation", Colors.WHITE)
    print_colored("- Check the troubleshooting section if you encounter issues", Colors.WHITE)


def main():
    """Main setup function."""
    print_header("TaxFix Multi-Agent System Setup")
    print_colored("Welcome! This script will help you set up TaxFix.", Colors.GREEN)
    
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print_colored(f"Working directory: {os.getcwd()}", Colors.CYAN)
    
    # Run setup steps
    steps_passed = 0
    total_steps = 8
    
    if check_python_version():
        steps_passed += 1
    
    if check_redis():
        steps_passed += 1
    
    if setup_virtual_environment():
        steps_passed += 1
    
    if install_dependencies():
        steps_passed += 1
    
    if setup_environment_file():
        steps_passed += 1
    
    if check_api_keys():
        steps_passed += 1
    
    test_connections()
    steps_passed += 1
    
    if create_database_schema():
        steps_passed += 1
    
    # Show results
    print_header("Setup Results")
    print_colored(f"Completed: {steps_passed}/{total_steps} steps", Colors.CYAN)
    
    if steps_passed == total_steps:
        print_colored("🎉 All setup steps completed successfully!", Colors.GREEN + Colors.BOLD)
    else:
        print_colored("⚠️  Some steps need attention. Please review the output above.", Colors.YELLOW)
    
    final_instructions()


if __name__ == "__main__":
    main()
