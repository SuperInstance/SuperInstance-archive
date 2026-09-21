#!/usr/bin/env python3
"""
Loopless Content Studio - Main Startup Script
Handles first-run setup, dependency checks, and system launch
"""

import sys
import os
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def check_python_version():
    """Ensure Python 3.10+"""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")


def check_dependencies():
    """Check if required packages are installed"""
    required = [
        'anthropic',
        'openai',
        'fastapi',
        'uvicorn',
        'asyncio',
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"\n⚠️ Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        print("\nOr install all dependencies:")
        print("  pip install -r requirements.txt")
        return False

    print("✓ All core dependencies installed")
    return True


def check_env_file():
    """Check if .env exists and has API keys"""
    env_path = Path(".env")

    if not env_path.exists():
        return False

    # Read and check for keys
    with open(env_path, 'r') as f:
        content = f.read()

    # Check if any real API keys exist (not placeholder)
    has_keys = any([
        'ANTHROPIC_API_KEY=' in content and 'your-' not in content and content.split('ANTHROPIC_API_KEY=')[1].split('\n')[0].strip(),
        'OPENAI_API_KEY=' in content and 'your-' not in content and content.split('OPENAI_API_KEY=')[1].split('\n')[0].strip(),
        'GROQ_API_KEY=' in content and 'your-' not in content and 'GROQ_API_KEY=' in content and content.split('GROQ_API_KEY=')[1].split('\n')[0].strip()
    ])

    return has_keys


def run_first_time_setup():
    """Run first-time setup wizard"""
    print("\n" + "="*60)
    print("🔧 FIRST-TIME SETUP REQUIRED")
    print("="*60 + "\n")

    from src.utils.first_run_setup import FirstRunSetup

    setup = FirstRunSetup()
    success = setup.run()

    if not success:
        print("\n⚠️ Setup incomplete. Exiting.")
        sys.exit(1)

    return True


def start_system():
    """Start the content studio system"""
    print("\n" + "="*60)
    print("🚀 STARTING LOOPLESS CONTENT STUDIO")
    print("="*60 + "\n")

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Import and run FastAPI server
    try:
        import uvicorn

        print("Starting FastAPI server on http://localhost:8000")
        print("\n" + "="*60)
        print("🎬 API ENDPOINTS AVAILABLE")
        print("="*60)
        print("\nTo send a request:")
        print("  curl -X POST http://localhost:8000/api/request \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"message\": \"Create Episode 1 for YouTube\", \"user_id\": \"casey\"}'")
        print("\nTo check status:")
        print("  curl http://localhost:8000/api/status")
        print("\nTo view agents:")
        print("  curl http://localhost:8000/api/agents")
        print("\nAPI Documentation:")
        print("  http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop")
        print("="*60 + "\n")

        # Start FastAPI server using uvicorn
        uvicorn.run(
            "src.orchestrator.api_server:app",
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )

    except KeyboardInterrupt:
        print("\n\n🛑 Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error starting system: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print(" "*15 + "🎬 LOOPLESS CONTENT STUDIO 🎬")
    print(" "*10 + "Multi-Agent Parallel Content Production System")
    print("="*70 + "\n")

    # Step 1: Check Python version
    print("Step 1: Checking Python version...")
    check_python_version()

    # Step 2: Check dependencies
    print("\nStep 2: Checking dependencies...")
    if not check_dependencies():
        print("\n❌ Please install dependencies first")
        sys.exit(1)

    # Step 3: Check configuration
    print("\nStep 3: Checking configuration...")
    if not check_env_file():
        print("⚠️ No API keys configured")
        if input("\nRun first-time setup now? (Y/n): ").lower() != 'n':
            if not run_first_time_setup():
                sys.exit(1)
        else:
            print("\n⚠️ Configuration required. Please run:")
            print("   python src/utils/first_run_setup.py")
            sys.exit(1)
    else:
        print("✓ Configuration found")

    # Step 4: Start system
    print("\n" + "="*70)
    print(" "*20 + "🚀 LAUNCHING SYSTEM")
    print("="*70)

    start_system()


if __name__ == "__main__":
    main()
