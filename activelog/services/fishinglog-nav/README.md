# Professional Marine Navigation System

A comprehensive ECDIS-compliant marine navigation system with advanced features for professional maritime operations.

## Features

### Core Navigation
- **ECDIS-Compliant Chart Display** - Full compliance with IEC 61174 and IMO performance standards
- **S-57/S-63 Encrypted Chart Support** - Supports both unencrypted S-57 and encrypted S-63 nautical charts
- **Multi-Layer Chart Overlay System** - Professional overlay management with layer prioritization
- **Multi-Monitor Support** - Dedicated displays for helm, navigation station, and flybridge

### Target Tracking & Safety
- **AIS Target Tracking** - Automatic identification system with collision prediction
- **ARPA Radar Overlay** - Professional radar target tracking with CPA/TCPA calculations
- **MOB (Man Overboard) System** - Instant GPS marking with Williamson Turn recovery patterns
- **Collision Avoidance** - Real-time risk assessment and collision predictions

### Weather & Environmental
- **Weather Routing** - GRIB file support with weather overlay
- **Tide and Current Overlay** - Tidal and current information overlay
- **3D Bathymetric Visualization** - Three-dimensional depth visualization

### Navigation Planning
- **Route Planning** - Advanced waypoint optimization and route calculation
- **Track Recording** - Automatic track logging with position history
- **Split-Screen Modes** - Multiple display configurations

### Professional Features
- **Night Mode** - Red-light preservation for night operations
- **Station-Specific Displays** - Customized interfaces for different bridge stations
- **Real-Time Data Integration** - Live AIS, radar, and GPS data processing

## Installation

1. **Install Dependencies**
```bash
cd ~/activelog/services/fishinglog-nav
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your specific configuration
```

3. **Initialize Database**
```bash
# The system will automatically create the chart database on first run
```

## Usage

### Start the Navigation System
```bash
python main.py
```

The system will start on port 8365 and provide multiple interfaces:

- **Main Navigation**: http://localhost:8365/
- **Helm Station**: http://localhost:8365/helm
- **Navigation Station**: http://localhost:8365/nav-station  
- **Flybridge**: http://localhost:8365/flybridge

### API Endpoints

#### Position Management
- `GET /api/position` - Get current vessel position
- `POST /api/position` - Update vessel position

#### Chart Management
- `POST /api/charts/load` - Load chart file
- `GET /api/charts/catalog` - Get chart catalog

#### Route Planning
- `POST /api/route/plan` - Plan optimized route
- `GET /api/route/current` - Get current route

#### Safety Systems
- `POST /api/mob/mark` - Mark MOB position
- `GET /api/ais/targets` - Get AIS targets
- `GET /api/radar/targets` - Get radar targets

#### Weather & Environment
- `POST /api/weather/grib` - Load GRIB weather file
- `GET /api/tides/current` - Get tide information

#### Display Management
- `POST /api/display/config` - Configure displays
- `GET /api/night-mode/on` - Enable night mode
- `GET /api/night-mode/off` - Disable night mode

### WebSocket Events

The system uses WebSocket for real-time updates:

- `position_update` - Vessel position changes
- `ais_update` - AIS target updates
- `radar_update` - Radar target updates
- `mob_alert` - Man overboard alerts
- `collision_warning` - Collision risk warnings
- `weather_update` - Weather data updates

## Configuration

### Chart Configuration
Place S-57/S-63 chart files in the `data/charts/` directory. The system supports:
- Unencrypted S-57 charts (.000 files)
- S-63 encrypted charts (with proper permits)
- Chart updates and corrections

### AIS Configuration
Configure AIS data source in the environment:
```bash
AIS_HOST=localhost
AIS_PORT=2101
```

### Radar Configuration
Configure radar data source:
```bash
RADAR_HOST=localhost  
RADAR_PORT=2102
```

## Safety Features

### MOB (Man Overboard) System
- Instant GPS marking with single button press
- Automatic Williamson Turn calculation
- Visual and audio alerts
- Recovery pattern display

### Collision Avoidance
- Real-time CPA/TCPA calculations
- Risk level assessment (Safe/Caution/Warning/Danger)
- Automatic collision warnings
- Recommended avoidance actions

### ARPA Radar Tracking
- Automatic target acquisition
- Manual target selection
- Track quality assessment
- Target motion analysis

## Technical Specifications

### Performance
- Supports up to 100 simultaneous targets
- Sub-second position updates
- Real-time collision calculations
- Multi-threaded processing

### Compliance
- ECDIS IEC 61174 compliant
- IMO ARPA performance standards
- S-57/S-63 chart standards
- Maritime safety protocols

### Hardware Requirements
- Modern multi-core processor
- Minimum 8GB RAM
- Dedicated graphics recommended
- Multiple monitor support
- Network connectivity for data feeds

## Development

### Project Structure
```
fishinglog-nav/
├── main.py                 # Main application
├── src/                    # Core modules
│   ├── chart_engine.py     # ECDIS chart engine
│   ├── ais_tracker.py      # AIS target tracking
│   ├── radar_system.py     # ARPA radar system
│   ├── weather_router.py   # Weather routing
│   ├── mob_system.py       # MOB system
│   └── ...
├── templates/              # HTML templates
├── static/                 # CSS/JS assets
├── config/                 # Configuration files
└── data/                   # Chart and data storage
```

### Adding New Features
1. Create module in `src/` directory
2. Import and initialize in `main.py`
3. Add API endpoints as needed
4. Update WebSocket handlers
5. Add frontend components

## Support

This is a professional marine navigation system designed for real-world maritime operations. Proper training and certification is recommended for operational use.

## License

Professional maritime software - contact for licensing terms.