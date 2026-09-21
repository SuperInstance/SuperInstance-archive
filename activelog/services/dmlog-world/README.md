# DM Log World Building Service

A comprehensive world building service for tabletop RPGs, providing tools for generating maps, locations, weather, calendars, pantheons, and more.

## Features

### 🗺️ Map Generation
- **Dungeon Maps**: Generate dungeons with rooms, corridors, and multiple levels
- **Settlement Maps**: Create towns and cities with districts, roads, and buildings  
- **Region Maps**: Generate regions with biomes, settlements, and trade routes
- **World Maps**: Create world maps with continents, climate zones, and major geographic features

### 📍 Location Descriptions
- Rich, immersive location descriptions with sensory details
- Visual, auditory, olfactory, tactile, and emotional details
- Atmospheric effects and environmental conditions
- Customizable detail levels and writing styles

### 🌤️ Weather System
- Realistic weather simulation with seasonal patterns
- Weather forecasting and historical data
- Extreme weather events affecting gameplay
- Climate zone simulation
- Weather effects on movement, combat, and exploration

### 📅 Calendar & Events
- Customizable calendar systems with months, seasons, and holidays
- Event scheduling and tracking
- Time advancement with automated event triggering
- Historical timeline management
- Cultural and religious calendar integration

### 🏛️ Pantheon & Religion
- Generate complete pantheons with deity relationships
- Detailed deity creation with domains, alignments, and mythology
- Religious orders and temple generation
- Creation myths and religious lore
- Worship practices and commandments

## Installation

1. Ensure Python 3.8+ is installed
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the service:
```bash
python3 main.py
```

The service will start on port 8014 (configurable via `DMLOG_WORLD_PORT` environment variable).

## API Endpoints

### Map Generation
- `POST /maps/dungeon` - Generate dungeon maps
- `POST /maps/settlement` - Generate settlement maps
- `POST /maps/region` - Generate region maps
- `POST /maps/world` - Generate world maps

### Location Descriptions
- `POST /locations/describe` - Generate rich location descriptions

### Weather System
- `POST /weather/generate` - Generate weather conditions
- `POST /weather/query` - Query current weather
- `POST /weather/events/create` - Create weather events

### Calendar System
- `POST /calendar/create` - Create new calendar systems
- `POST /calendar/{calendar_id}/events` - Create calendar events
- `POST /calendar/{calendar_id}/advance` - Advance calendar time
- `POST /calendar/query` - Query calendar information

### Religion System
- `POST /religion/pantheon/generate` - Generate complete pantheons
- `POST /religion/deity/generate` - Generate individual deities
- `POST /religion/query` - Query religious information

### Utilities
- `GET /random/name` - Generate random names
- `GET /health` - Health check
- `GET /docs` - API documentation

## Configuration

The service can be configured through environment variables:

- `DMLOG_WORLD_PORT` - Service port (default: 8014)
- Other configuration options are available in `config.py`

## Testing

Run the test suite:
```bash
python3 test_service.py
```

## Service Architecture

- **FastAPI** - Modern, fast web framework
- **Pydantic** - Data validation and settings management
- **SQLAlchemy** - Database ORM (ready for database integration)
- **Modular Design** - Separate services for each major feature

## Example Usage

### Generate a Dungeon
```python
import requests

response = requests.post('http://localhost:8014/maps/dungeon', json={
    "name": "Ancient Catacombs",
    "levels": 3,
    "room_count": 12,
    "theme": "undead",
    "difficulty": 5,
    "include_boss_room": True,
    "width": 50,
    "height": 50
})

dungeon = response.json()
```

### Create a Location Description
```python
response = requests.post('http://localhost:8014/locations/describe', json={
    "location_type": "outdoor_area",
    "biome": "temperate_forest",
    "atmosphere": "mysterious",
    "include_sensory_details": True,
    "detail_level": "detailed",
    "time_of_day": "dusk",
    "season": "autumn"
})

location = response.json()
```

### Generate Weather
```python
response = requests.post('http://localhost:8014/weather/generate', json={
    "season": "winter",
    "forecast_duration_hours": 48,
    "include_extreme_weather": True,
    "weather_variability": 0.8
})

weather = response.json()
```

## Development

The service is built with modularity in mind:

- **Models** (`models/`) - Pydantic models for data validation
- **Services** (`services/`) - Business logic for each feature
- **Config** (`config.py`) - Configuration management
- **Main** (`main.py`) - FastAPI application and routing

Each service is independent and can be used standalone or integrated with the main API.

## Future Enhancements

- Database persistence for generated content
- User authentication and authorization
- Advanced AI-powered content generation
- Integration with popular VTT platforms
- Real-time collaborative world building
- Import/export functionality for popular formats

## License

This service is part of the DM Log project.