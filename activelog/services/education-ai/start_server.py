#!/usr/bin/env python3
"""
ActiveLog Education AI Suite - Server Startup Script
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from education_ai_server import EducationAIServer

def main():
    """Main startup function"""
    print("🚀 Starting ActiveLog Education AI Suite...")
    print("📚 Comprehensive AI-powered education platform")
    print("=" * 60)
    
    try:
        # Create and run server
        server = EducationAIServer(port=8016)
        asyncio.run(server.start_server())
        
    except KeyboardInterrupt:
        print("\n👋 Education AI Suite stopped by user")
    except Exception as e:
        print(f"❌ Failed to start Education AI Suite: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()