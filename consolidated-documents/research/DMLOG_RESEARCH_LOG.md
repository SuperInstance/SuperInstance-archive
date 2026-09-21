# DMLog.ai Gaming Platform - Complete Research Log

## Overview
DMLog.ai is a revolutionary RPG/D&D gaming platform with 31 interconnected services providing comprehensive campaign management, character building, AI-powered dungeon mastering, and immersive gaming experiences.

## Core Architecture Components

### 1. BASIC TIER SERVICES (Always-On - Tiny Instance)
**Essential services that need to be running for basic functionality:**

#### **dmlog-backend** (Port 8300)
- **Purpose**: Main API backend, lightweight service
- **Technology**: FastAPI (Python)
- **Size**: Small (~40 lines of code, minimal resources)
- **Function**: Health checks, basic API routing
- **Dependencies**: None critical

#### **dmlog-frontend** (Web Interface)
- **Purpose**: Main user interface for the gaming platform
- **Technology**: FastAPI + Jinja2 templates, static files
- **Function**: Game dashboard, basic campaign management
- **Resources**: Static web content, minimal processing

#### **dmlog-core** (Port 8012) 
- **Purpose**: Core RPG rules engine and game mechanics
- **Technology**: FastAPI with comprehensive API routes
- **Function**: Dice rolling, combat, spells, encounters, experience
- **API Routes**: /dice, /character, /combat, /spells, /encounters
- **Dependencies**: SQLite database, rules data

#### **dmlog-session-logger**
- **Purpose**: Basic session recording and management
- **Technology**: Python/FastAPI
- **Function**: Track game sessions, basic logging

### 2. ADVANCED TIER SERVICES (On-Demand - Powerful Instance)
**Resource-intensive services for advanced gaming features:**

#### **AI & Intelligence Services**
- **dmlog-ai-dm**: AI-powered Dungeon Master with narrative management
- **dmlog-ai-insights**: Advanced analytics and player insights
- **dmlog-adaptive**: Adaptive gaming engine with ML optimization

#### **Character & World Building**
- **dmlog-character-builder**: Advanced character creation with:
  - AI generators, voice guidance, WebGL visualization
  - Combat simulation, neural optimization
  - Raytracing renderer, VR/AR support
  - Mocap animation system
- **dmlog-world-builder-v2**: Node.js-based world creation tools
- **dmlog-world**: World services (maps, religion, weather, locations)

#### **Advanced Gaming Features**
- **dmlog-visualizer**: Unreal Engine integration, scene generation
- **dmlog-battle**: Combat system with grid-based battles
- **dmlog-characters**: Advanced NPC personality and emotion systems
- **dmlog-templates**: Campaign and adventure generators

#### **Collaboration & Streaming**
- **dmlog-stream**: Live streaming capabilities
- **dmlog-mobile**: Mobile app support
- **dmlog-web-portal**: Advanced web portal with public access

#### **Economy & Marketplace**
- **dmlog-marketplace**: Asset trading and content marketplace
- **dmlog-converter**: Multi-system game conversion tools

## Technology Stack Summary

### Backend Technologies
- **Primary**: Python FastAPI (most services)
- **Secondary**: Node.js (world-builder, visualizer, some advanced features)
- **Database**: SQLite (development), PostgreSQL (production scaling)

### Frontend Technologies
- **Web**: HTML/CSS/JavaScript, WebGL, Jinja2 templates
- **Mobile**: React Native/Expo
- **3D/Visualization**: Unreal Engine integration, WebGL, raytracing

### AI/ML Stack
- **Speech Recognition**: Python speech_recognition
- **AI Integration**: Custom AI clients, OpenAI integration
- **Neural Networks**: Custom neural optimizers for character builds

## Port Allocation
- **8012**: dmlog-core (RPG rules engine)
- **8300**: dmlog-backend (main backend)
- **8090**: AI insights integration
- **8092**: User management integration
- Various others for specialized services

## Data Architecture
- **Character Data**: SQLite databases for character builds
- **Session Data**: Game session logs and analytics
- **World Data**: Maps, locations, campaign information
- **User Data**: Player profiles and preferences

## Critical Dependencies
1. **Python 3.8+** with FastAPI, SQLite
2. **Node.js** for world-builder and visualization services
3. **AI/ML Libraries**: speech_recognition, custom neural networks
4. **3D Graphics**: WebGL, potential Unreal Engine integration

## Performance Characteristics
- **Basic Tier**: Low resource usage, mainly API calls and web serving
- **Advanced Tier**: High CPU/GPU for AI, 3D rendering, real-time processing
- **Scaling**: Microservices can be deployed independently

## Integration Points
- Services communicate via HTTP APIs
- Shared authentication system
- Cross-domain data integration (fitness → character stats)
- Compute capital economy integration

---

*This research forms the foundation for the two-tier AWS deployment strategy.*