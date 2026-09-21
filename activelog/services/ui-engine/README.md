# UI Engine Service

Advanced UI customization service with comprehensive visual development tools.

## Features

### 🔌 Visual Wiring for App Building
- Node-based visual programming interface
- Component connection system
- Data flow visualization
- Drag-and-drop wiring

### 🫧 Bubble Map Workflow Designer
- Interactive bubble-based workflow creation
- Force-directed auto-layout
- Workflow validation and execution planning
- Visual workflow export/import

### 🖥️ Multi-Monitor Support
- Adaptive UI layouts for multiple displays
- Display configuration management
- Viewport scaling and optimization
- Monitor-specific UI adaptations

### 🤖 Chatbot-Driven Development
- Natural language UI creation
- AI-powered component suggestions
- Code generation from descriptions
- Interactive development assistant

### ⚡ Real-Time Preview
- Live preview with hot reload
- Device viewport simulation
- WebSocket-based updates
- Performance monitoring

### 📦 Drag-Drop Component Library
- Comprehensive component catalog
- Custom component creation
- Drag-and-drop interface builder
- Component property management

### 🎨 Theme Marketplace
- Theme discovery and purchasing
- Community theme sharing
- Theme customization tools
- License management

### 📝 Interface Versioning
- Git-like version control for UIs
- Branch and merge support
- Change tracking and history
- Version comparison tools

### ⚙️ Preference Persistence
- User preference management
- Cross-device synchronization
- Preference categories and validation
- Import/export settings

### 📥 Export/Import Layouts
- Multiple format support (JSON, YAML, XML, ZIP)
- Figma/Sketch integration
- Asset bundling
- Cross-platform compatibility

## Quick Start

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the service:
```bash
python run.py
```

3. Access the service:
- Service: http://localhost:8324
- API Docs: http://localhost:8324/docs
- Health Check: http://localhost:8324/health

## API Endpoints

### Core Service
- `GET /` - Service information
- `GET /health` - Health check
- `GET /api/components` - Component library

### Visual Wiring
- `GET /api/wiring/templates` - Get component templates
- `POST /api/wiring/canvas` - Create wiring canvas
- `GET /api/wiring/canvas/{id}` - Get canvas details

### Bubble Workflows
- `POST /api/bubble/workflow` - Create workflow
- `GET /api/bubble/workflow/{id}` - Get workflow
- `GET /api/bubble/templates` - Get bubble templates

### Multi-Monitor
- `GET /api/monitors/detect` - Detect displays
- `POST /api/monitors/configuration` - Create display config

### Chatbot Development
- `POST /api/chatbot/conversation` - Start conversation
- `POST /api/chatbot/conversation/{id}/message` - Send message

### Real-Time Preview
- `POST /api/preview/session` - Create preview session
- `WebSocket /ws/preview/{id}` - Preview updates

### Component Library
- `GET /api/components/library` - Get component library
- `POST /api/components/instance` - Create component instance

### Theme Marketplace
- `GET /api/themes/marketplace` - Browse themes
- `GET /api/themes/marketplace/{id}` - Theme details
- `POST /api/themes/purchase` - Purchase theme

### Interface Versioning
- `POST /api/versions/snapshot` - Create version snapshot
- `GET /api/versions/{id}/history` - Version history

### Preferences
- `GET /api/preferences/{user_id}` - Get user preferences
- `POST /api/preferences/{user_id}` - Set preference

### Layout Import/Export
- `POST /api/layouts/export` - Export layout
- `GET /api/layouts/export/{id}/download` - Download export
- `POST /api/layouts/import` - Import layout

## Architecture

The UI Engine consists of several integrated modules:

- **Visual Wiring Engine**: Node-based component connections
- **Bubble Workflow Designer**: Interactive workflow creation
- **Multi-Monitor Manager**: Display configuration and adaptation
- **Chatbot Interface**: AI-powered development assistance
- **Preview System**: Real-time UI preview and testing
- **Component Library**: Reusable UI components
- **Theme Marketplace**: Theme distribution system
- **Interface Versioning**: Version control for UIs
- **Preference Manager**: User settings persistence
- **Import/Export System**: Layout portability

## Data Storage

The service uses SQLite for persistent storage:
- `data/ui_engine.db` - Main database
- `data/preferences.db` - User preferences
- `exports/` - Exported layouts
- `assets/` - Component assets

## WebSocket Support

Real-time features use WebSocket connections:
- Preview updates
- Collaborative editing
- Live component changes
- Multi-monitor synchronization

## Development

### Running in Development Mode
```bash
python run.py
```

### Adding New Components
1. Define component in `component_library.py`
2. Add component template
3. Update API endpoints
4. Test integration

### Extending Themes
1. Create theme definition in `theme_marketplace.py`
2. Add color palettes and styling
3. Test across components
4. Publish to marketplace

## Configuration

Environment variables:
- `PORT` - Service port (default: 8324)
- `HOST` - Service host (default: 0.0.0.0)
- `DEBUG` - Debug mode (default: false)
- `DB_PATH` - Database path

## Compatibility

- Python 3.8+
- FastAPI framework
- WebSocket support
- Cross-platform compatible
- Multi-browser support

## License

MIT License - See LICENSE file for details