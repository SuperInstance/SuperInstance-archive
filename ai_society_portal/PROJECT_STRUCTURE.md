# 📁 AI Society Portal - Project Structure

## Overview

```
ai_society_portal/
├── README.md                    # Main documentation
├── QUICKSTART.md               # Quick start guide
│
├── backend/                    # Python FastAPI backend
│   ├── character_system.py    # Character & laptop management
│   ├── room_system.py          # Room & atmosphere system
│   ├── orchestration_engine.py # Conversation orchestration
│   ├── api_server.py           # FastAPI server with WebSocket
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Environment variables template
│
├── frontend/                   # React frontend
│   ├── public/
│   │   └── index.html         # HTML template
│   ├── src/
│   │   ├── App.jsx            # Main app component
│   │   ├── App.css            # Main app styles
│   │   ├── index.jsx          # React entry point
│   │   ├── index.css          # Global styles
│   │   └── components/        # React components
│   │       ├── ChatInterface.jsx        # Left column chat
│   │       ├── ChatInterface.css
│   │       ├── RoomWindow.jsx           # Floating room windows
│   │       ├── RoomWindow.css
│   │       ├── CreateCharacter.jsx      # Character creation modal
│   │       ├── CreateRoom.jsx           # Room creation modal
│   │       ├── Modal.css                # Shared modal styles
│   │       ├── CharacterList.jsx        # Character list display
│   │       ├── RoomList.jsx             # Room list display
│   │       └── Lists.css                # Shared list styles
│   └── package.json           # Node dependencies
│
├── characters/                # Generated: Character storage
│   └── {character_id}/
│       ├── character.json     # Character profile
│       └── laptop/            # Character's files
│           ├── documents/
│           ├── code/
│           ├── images/
│           └── research_notes/
│
├── rooms/                     # Generated: Room storage
│   └── {room_id}/
│       ├── room.json          # Room configuration
│       └── sessions/          # Session history
│           └── {session_id}/
│               └── session.json
│
└── vector_db/                 # Generated: Vector database data
