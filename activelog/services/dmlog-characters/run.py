#!/usr/bin/env python3
"""
Startup script for the Character AI Service.
"""

import uvicorn
from main import app, config

if __name__ == "__main__":
    print(f"""
    🎭 DM Log Characters AI Service
    ================================
    
    Starting advanced character AI system...
    
    Features:
    • Voice synthesis with emotional modulation
    • Personality-driven behavior prediction  
    • Dynamic dialogue generation
    • Memory system for consistent interactions
    • Emotion engine for realistic responses
    • Voice cloning from audio samples
    • Accent and speech pattern system
    • AI portrait generation
    • Mannerism and gesture descriptions
    • Faction reputation tracking
    • Character arc progression
    • Party banter generation
    
    Service will be available at: http://localhost:{config.SERVICE_PORT}
    API Documentation: http://localhost:{config.SERVICE_PORT}/docs
    """)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.SERVICE_PORT,
        log_level="info",
        reload=False
    )