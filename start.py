"""
Quick start script for FastAPI Google OAuth application
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📝 Please create a .env file based on the env-example.md file")
        return False
    
    # Check for required variables
    required_vars = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET", 
        "JWT_SECRET_KEY",
        "SECRET_KEY",
        "DATABASE_URL"
    ]
    
    env_content = env_file.read_text()
    missing_vars = []
    
    for var in required_vars:
        if f"{var}=" not in env_content or f"{var}=your" in env_content or f"{var}=secret" in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing or incomplete environment variables: {', '.join(missing_vars)}")
        print("📝 Please update your .env file with proper values")
        return False
    
    print("✅ Environment file looks good")
    return True

def install_dependencies():
    """Install required dependencies"""
    return run_command("pip install -r requirements.txt", "Installing dependencies")

def run_application():
    """Run the FastAPI application"""
    print("🚀 Starting FastAPI application...")
    print("📖 API documentation will be available at: http://127.0.0.1:8000/docs")
    print("🔐 To test authentication, visit: http://127.0.0.1:8000/auth/login")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 60)
    
    try:
        subprocess.run([
            "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except FileNotFoundError:
        print("❌ uvicorn not found. Installing...")
        if run_command("pip install uvicorn[standard]", "Installing uvicorn"):
            run_application()

def main():
    """Main function"""
    print("🎯 FastAPI Google OAuth Quick Start")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ 'app' directory not found!")
        print("📁 Please run this script from the project root directory")
        sys.exit(1)
    
    # Check environment file
    if not check_env_file():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Run application
    run_application()

if __name__ == "__main__":
    main()