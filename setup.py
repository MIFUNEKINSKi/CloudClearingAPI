#!/usr/bin/env python3
"""
CloudClearingAPI Setup Script

This script helps set up the CloudClearingAPI environment and dependencies.
Run this after cloning the repository and before using the system.
"""

import os
import sys
import subprocess
from pathlib import Path
import json

def print_status(message, status="info"):
    """Print colored status messages"""
    colors = {
        "info": "\033[94m",     # Blue
        "success": "\033[92m",  # Green
        "warning": "\033[93m",  # Yellow
        "error": "\033[91m",    # Red
        "reset": "\033[0m"      # Reset
    }
    
    color = colors.get(status, colors["info"])
    print(f"{color}{message}{colors['reset']}")

def check_python_version():
    """Check if Python version is compatible"""
    print_status("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print_status("❌ Python 3.8+ is required. Current version: " + sys.version, "error")
        return False
    
    print_status(f"✅ Python {sys.version.split()[0]} detected", "success")
    return True

def setup_virtual_environment():
    """Create and activate virtual environment"""
    print_status("📦 Setting up virtual environment...")
    
    if not os.path.exists(".venv"):
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print_status("✅ Virtual environment created", "success")
        except subprocess.CalledProcessError:
            print_status("❌ Failed to create virtual environment", "error")
            return False
    else:
        print_status("ℹ️  Virtual environment already exists", "warning")
    
    # Provide activation instructions
    if os.name == "nt":  # Windows
        activate_cmd = ".venv\\Scripts\\activate"
    else:  # Unix/macOS
        activate_cmd = "source .venv/bin/activate"
    
    print_status(f"💡 Activate with: {activate_cmd}", "info")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print_status("📚 Installing dependencies...")
    
    try:
        # Use pip from virtual environment if it exists
        if os.path.exists(".venv"):
            if os.name == "nt":
                pip_cmd = [".venv\\Scripts\\pip"]
            else:
                pip_cmd = [".venv/bin/pip"]
        else:
            pip_cmd = [sys.executable, "-m", "pip"]
        
        # Upgrade pip first
        subprocess.run(pip_cmd + ["install", "--upgrade", "pip"], check=True)
        
        # Install requirements
        if os.path.exists("requirements.txt"):
            subprocess.run(pip_cmd + ["install", "-r", "requirements.txt"], check=True)
            print_status("✅ Dependencies installed successfully", "success")
        else:
            print_status("⚠️  requirements.txt not found", "warning")
            
    except subprocess.CalledProcessError as e:
        print_status(f"❌ Failed to install dependencies: {e}", "error")
        return False
    
    return True

def setup_configuration():
    """Set up configuration files"""
    print_status("⚙️  Setting up configuration...")
    
    # Create config directory
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Copy example config if main config doesn't exist
    config_file = config_dir / "config.yaml"
    example_config = config_dir / "config.example.yaml"
    
    if not config_file.exists() and example_config.exists():
        import shutil
        shutil.copy(example_config, config_file)
        print_status("✅ Configuration file created from example", "success")
        print_status("💡 Edit config/config.yaml with your settings", "info")
    
    # Copy .env example if .env doesn't exist
    env_file = Path(".env")
    example_env = Path(".env.example")
    
    if not env_file.exists() and example_env.exists():
        import shutil
        shutil.copy(example_env, env_file)
        print_status("✅ Environment file created from example", "success")
        print_status("💡 Edit .env with your credentials", "info")
    
    return True

def check_earth_engine_setup():
    """Check Google Earth Engine setup"""
    print_status("🌍 Checking Google Earth Engine setup...")
    
    try:
        import ee
        
        # Try to initialize (this will fail if not authenticated)
        try:
            ee.Initialize()
            print_status("✅ Google Earth Engine is ready", "success")
            return True
        except Exception:
            print_status("⚠️  Google Earth Engine not authenticated", "warning")
            print_status("💡 Run: earthengine authenticate", "info")
            print_status("💡 Visit: https://signup.earthengine.google.com/", "info")
            return False
            
    except ImportError:
        print_status("❌ earthengine-api not installed", "error")
        return False

def create_directories():
    """Create necessary directories"""
    print_status("📁 Creating project directories...")
    
    directories = [
        "data",
        "output", 
        "logs",
        "temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print_status("✅ Project directories created", "success")

def run_basic_tests():
    """Run basic functionality tests"""
    print_status("🧪 Running basic tests...")
    
    try:
        # Test imports
        sys.path.append("src")
        from core.config import get_config
        
        config = get_config()
        print_status("✅ Configuration loading works", "success")
        
        # Test API imports
        try:
            from api.main import app
            print_status("✅ API imports work", "success")
        except Exception as e:
            print_status(f"⚠️  API import issue: {e}", "warning")
        
        return True
        
    except Exception as e:
        print_status(f"❌ Basic tests failed: {e}", "error")
        return False

def print_next_steps():
    """Print next steps for the user"""
    print_status("\n🎉 Setup Complete! Next Steps:", "success")
    print_status("━" * 50, "info")
    
    steps = [
        "1. 🔑 Set up Google Earth Engine:",
        "   • Visit https://signup.earthengine.google.com/",
        "   • Run: earthengine authenticate",
        "",
        "2. ⚙️  Configure your settings:",
        "   • Edit config/config.yaml",
        "   • Edit .env with your credentials",
        "",
        "3. 🚀 Start the API server:",
        "   • python src/api/main.py",
        "   • Visit http://localhost:8000/docs",
        "",
        "4. 📓 Try the demo notebook:",
        "   • jupyter notebook notebooks/mvp_change_detection_demo.ipynb",
        "",
        "5. 🧪 Run tests:",
        "   • python -m pytest tests/",
        "",
        "📖 See README.md for detailed documentation"
    ]
    
    for step in steps:
        if step.startswith(("1.", "2.", "3.", "4.", "5.")):
            print_status(step, "success")
        elif step.startswith("   •"):
            print_status(step, "info")
        else:
            print(step)

def main():
    """Main setup function"""
    print_status("🛰️  CloudClearingAPI Setup", "success")
    print_status("=" * 50, "info")
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    # Setup steps
    steps = [
        setup_virtual_environment,
        install_dependencies,
        setup_configuration,
        create_directories,
        check_earth_engine_setup,
        run_basic_tests
    ]
    
    success = True
    for step in steps:
        if not step():
            success = False
    
    # Print results
    if success:
        print_next_steps()
    else:
        print_status("\n⚠️  Setup completed with some issues", "warning")
        print_status("Check the messages above and resolve any problems", "info")
    
    return success

if __name__ == "__main__":
    main()