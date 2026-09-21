#!/usr/bin/env python3
"""
UI Engine Service Runner
Starts the UI Engine service on port 8324
"""

import uvicorn
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting UI Engine Service...")
    print("📍 Running on http://localhost:8324")
    print("📚 API Documentation: http://localhost:8324/docs")
    print("🔧 Features:")
    print("   • Visual wiring for app building")
    print("   • Bubble map workflow designer")
    print("   • Multi-monitor support")
    print("   • Chatbot-driven development")
    print("   • Real-time preview")
    print("   • Drag-drop component library")
    print("   • Theme marketplace")
    print("   • Interface versioning")
    print("   • Preference persistence")
    print("   • Export/import layouts")
    print()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8324,
        reload=True,
        log_level="info"
    )