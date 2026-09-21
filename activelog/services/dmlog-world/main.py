"""
DM Log World Building Service
Main FastAPI application
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn
from typing import Optional, List

from .config import Config
from .services.map_service import MapService
from .services.location_service import LocationDescriptionService
from .services.weather_service import WeatherService
from .services.calendar_service import CalendarService
from .services.religion_service import ReligionService

from .models.maps import (
    DungeonGenerationRequest, SettlementGenerationRequest,
    RegionGenerationRequest, WorldGenerationRequest, MapGenerationResponse
)
from .models.location import (
    LocationDescriptionRequest, LocationDescriptionResponse
)
from .models.weather import (
    WeatherGenerationRequest, WeatherQueryRequest, WeatherResponse,
    WeatherEventRequest
)
from .models.calendar import (
    CalendarCreationRequest, EventCreationRequest, CalendarQueryRequest,
    TimeAdvanceRequest, CalendarResponse
)
from .models.religion import (
    PantheonGenerationRequest, DeityGenerationRequest, ReligionQueryRequest,
    ReligionResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instances
map_service: MapService
location_service: LocationDescriptionService
weather_service: WeatherService
calendar_service: CalendarService
religion_service: ReligionService
config: Config

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global map_service, location_service, weather_service, calendar_service, religion_service, config
    
    # Startup
    logger.info("Starting DM Log World Building Service...")
    
    config = Config()
    config.ensure_directories()
    
    # Initialize services
    map_service = MapService()
    location_service = LocationDescriptionService()
    weather_service = WeatherService()
    calendar_service = CalendarService()
    religion_service = ReligionService()
    
    logger.info(f"World Building Service initialized on port {config.SERVICE_PORT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DM Log World Building Service...")

# Create FastAPI app
app = FastAPI(
    title="DM Log World Building Service",
    description="Comprehensive world building tools for tabletop RPGs",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "DM Log World Building Service",
        "version": "1.0.0"
    }

# Map Generation Endpoints
@app.post("/maps/dungeon", response_model=MapGenerationResponse)
async def generate_dungeon(request: DungeonGenerationRequest):
    """Generate a dungeon map with rooms and corridors."""
    try:
        return await map_service.generate_dungeon(request)
    except Exception as e:
        logger.error(f"Error generating dungeon: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/maps/settlement", response_model=MapGenerationResponse)
async def generate_settlement(request: SettlementGenerationRequest):
    """Generate a settlement map (town/city) with districts and buildings."""
    try:
        return await map_service.generate_settlement(request)
    except Exception as e:
        logger.error(f"Error generating settlement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/maps/region", response_model=MapGenerationResponse)
async def generate_region(request: RegionGenerationRequest):
    """Generate a region map with biomes and settlements."""
    try:
        return await map_service.generate_region(request)
    except Exception as e:
        logger.error(f"Error generating region: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/maps/world", response_model=MapGenerationResponse)
async def generate_world(request: WorldGenerationRequest):
    """Generate a world map with continents and climate zones."""
    try:
        return await map_service.generate_world(request)
    except Exception as e:
        logger.error(f"Error generating world: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Location Description Endpoints
@app.post("/locations/describe", response_model=LocationDescriptionResponse)
async def generate_location_description(request: LocationDescriptionRequest):
    """Generate rich location descriptions with sensory details."""
    try:
        return await location_service.generate_description(request)
    except Exception as e:
        logger.error(f"Error generating location description: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Weather System Endpoints
@app.post("/weather/generate", response_model=WeatherResponse)
async def generate_weather(request: WeatherGenerationRequest):
    """Generate weather conditions and forecasts."""
    try:
        return await weather_service.generate_weather(request)
    except Exception as e:
        logger.error(f"Error generating weather: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/weather/query", response_model=WeatherResponse)
async def query_weather(request: WeatherQueryRequest):
    """Query current weather conditions for a location."""
    try:
        # For now, generate new weather as we don't have persistent storage
        gen_request = WeatherGenerationRequest(
            location=request.location,
            forecast_duration_hours=24 if request.include_forecast else 0
        )
        return await weather_service.generate_weather(gen_request)
    except Exception as e:
        logger.error(f"Error querying weather: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/weather/events/create", response_model=WeatherResponse)
async def create_weather_event(request: WeatherEventRequest):
    """Create a custom weather event."""
    try:
        return await weather_service.create_weather_event(request)
    except Exception as e:
        logger.error(f"Error creating weather event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Calendar System Endpoints
@app.post("/calendar/create", response_model=CalendarResponse)
async def create_calendar(request: CalendarCreationRequest):
    """Create a new calendar system."""
    try:
        return await calendar_service.create_calendar(request)
    except Exception as e:
        logger.error(f"Error creating calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calendar/{calendar_id}/events", response_model=CalendarResponse)
async def create_event(calendar_id: str, request: EventCreationRequest):
    """Create a new event in the calendar."""
    try:
        # In a real implementation, we'd load the calendar from database
        # For now, create a simple calendar for demonstration
        calendar_req = CalendarCreationRequest(name="Default Calendar")
        calendar_resp = await calendar_service.create_calendar(calendar_req)
        
        if not calendar_resp.success or not calendar_resp.calendar_data:
            raise HTTPException(status_code=500, detail="Failed to create calendar")
        
        return await calendar_service.create_event(request, calendar_resp.calendar_data)
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calendar/{calendar_id}/advance", response_model=CalendarResponse)
async def advance_time(calendar_id: str, request: TimeAdvanceRequest):
    """Advance calendar time and trigger events."""
    try:
        # In a real implementation, we'd load the calendar from database
        calendar_req = CalendarCreationRequest(name="Default Calendar")
        calendar_resp = await calendar_service.create_calendar(calendar_req)
        
        if not calendar_resp.success or not calendar_resp.calendar_data:
            raise HTTPException(status_code=500, detail="Failed to create calendar")
        
        return await calendar_service.advance_time(request, calendar_resp.calendar_data)
    except Exception as e:
        logger.error(f"Error advancing time: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calendar/query", response_model=CalendarResponse)
async def query_calendar(request: CalendarQueryRequest):
    """Query calendar information and events."""
    try:
        # For demonstration, create a calendar with some sample events
        calendar_req = CalendarCreationRequest(name="Sample Calendar")
        calendar_resp = await calendar_service.create_calendar(calendar_req)
        
        if not calendar_resp.success or not calendar_resp.calendar_data:
            raise HTTPException(status_code=500, detail="Failed to create calendar")
        
        return await calendar_service.query_calendar(request, calendar_resp.calendar_data)
    except Exception as e:
        logger.error(f"Error querying calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Religion/Pantheon Endpoints
@app.post("/religion/pantheon/generate", response_model=ReligionResponse)
async def generate_pantheon(request: PantheonGenerationRequest):
    """Generate a complete pantheon with deities and relationships."""
    try:
        return await religion_service.generate_pantheon(request)
    except Exception as e:
        logger.error(f"Error generating pantheon: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/religion/deity/generate", response_model=ReligionResponse)
async def generate_deity(request: DeityGenerationRequest):
    """Generate a single deity with complete details."""
    try:
        # Convert single deity request to pantheon request
        pantheon_request = PantheonGenerationRequest(
            name=f"Pantheon of {request.name or 'Unknown'}",
            deity_count=1,
            cultural_theme=request.cultural_theme,
            generate_relationships=False,
            generate_mythology=request.generate_mythology
        )
        
        response = await religion_service.generate_pantheon(pantheon_request)
        
        if response.success and response.deities:
            # Apply specific requirements from deity request
            deity = response.deities[0]
            if request.name:
                deity.name = request.name
            if request.rank:
                deity.rank = request.rank
            if request.domains:
                deity.domains = request.domains
            if request.alignment:
                deity.alignment = request.alignment
        
        return response
    except Exception as e:
        logger.error(f"Error generating deity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/religion/query", response_model=ReligionResponse)
async def query_religion(request: ReligionQueryRequest):
    """Query religious information by various criteria."""
    try:
        # For demonstration, generate a sample pantheon and filter results
        pantheon_req = PantheonGenerationRequest(
            religion_type=request.pantheon_id and "polytheistic" or "polytheistic",
            deity_count=8
        )
        response = await religion_service.generate_pantheon(pantheon_req)
        
        if not response.success:
            return response
        
        # Apply filters
        filtered_deities = response.deities
        
        if request.deity_name:
            filtered_deities = [d for d in filtered_deities if request.deity_name.lower() in d.name.lower()]
        
        if request.domains:
            filtered_deities = [
                d for d in filtered_deities 
                if any(domain in d.domains for domain in request.domains)
            ]
        
        if request.alignment:
            filtered_deities = [d for d in filtered_deities if d.alignment in request.alignment]
        
        response.deities = filtered_deities
        return response
    except Exception as e:
        logger.error(f"Error querying religion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Utility Endpoints
@app.get("/random/name")
async def generate_random_name(
    type: str = Query("fantasy", description="Type of name: fantasy, medieval, modern"),
    gender: Optional[str] = Query(None, description="Gender: male, female, neutral"),
    culture: Optional[str] = Query(None, description="Cultural theme")
):
    """Generate random names for NPCs, locations, etc."""
    try:
        # Simple name generation
        import random
        
        name_parts = {
            "fantasy": {
                "prefixes": ["Aer", "Bel", "Cor", "Dar", "El", "Fel", "Gar", "Hal"],
                "suffixes": ["ion", "ius", "ara", "eth", "wyn", "dor", "rim", "las"]
            },
            "medieval": {
                "prefixes": ["God", "Wil", "Rob", "Rich", "Ed", "Hen", "Walt", "Gil"],
                "suffixes": ["win", "bert", "ward", "red", "mund", "frid", "helm", "ric"]
            }
        }
        
        parts = name_parts.get(type, name_parts["fantasy"])
        name = random.choice(parts["prefixes"]) + random.choice(parts["suffixes"])
        
        return {
            "name": name,
            "type": type,
            "gender": gender,
            "culture": culture
        }
    except Exception as e:
        logger.error(f"Error generating name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "DM Log World Building Service",
        "version": "1.0.0",
        "description": "Comprehensive world building tools for tabletop RPGs",
        "endpoints": {
            "maps": "/maps/{dungeon,settlement,region,world}",
            "locations": "/locations/describe",
            "weather": "/weather/{generate,query,events}",
            "calendar": "/calendar/{create,events,advance,query}",
            "religion": "/religion/{pantheon,deity,query}",
            "utilities": "/random/name"
        },
        "docs": "/docs"
    }

if __name__ == "__main__":
    config = Config()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.SERVICE_PORT,
        reload=True
    )