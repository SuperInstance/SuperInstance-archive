#!/usr/bin/env python3
"""
Test script for the DM Log World Building Service
"""

import asyncio
import json
from datetime import datetime

from services.map_service import MapService
from services.location_service import LocationDescriptionService
from services.weather_service import WeatherService
from services.calendar_service import CalendarService
from services.religion_service import ReligionService

from models.maps import DungeonGenerationRequest, SettlementGenerationRequest
from models.location import LocationDescriptionRequest, LocationType, Atmosphere
from models.weather import WeatherGenerationRequest, SeasonType
from models.calendar import CalendarCreationRequest, EventCreationRequest, EventType, EventScope, WorldDate
from models.religion import PantheonGenerationRequest, ReligionType

async def test_map_generation():
    """Test map generation services."""
    print("=== Testing Map Generation ===")
    
    map_service = MapService()
    
    # Test dungeon generation
    print("\n1. Generating Dungeon...")
    dungeon_request = DungeonGenerationRequest(
        name="Test Dungeon",
        levels=2,
        room_count=8,
        theme="ancient",
        width=40,
        height=40,
        seed="test123"
    )
    
    dungeon_response = await map_service.generate_dungeon(dungeon_request)
    print(f"   Success: {dungeon_response.success}")
    print(f"   Generation Time: {dungeon_response.generation_time:.2f}s")
    if dungeon_response.map_data:
        print(f"   Map Size: {dungeon_response.map_data.width}x{dungeon_response.map_data.height}")
        print(f"   Levels: {len(dungeon_response.map_data.levels)}")
    
    # Test settlement generation
    print("\n2. Generating Settlement...")
    settlement_request = SettlementGenerationRequest(
        name="Test Town",
        settlement_type="town",
        population=2000,
        has_walls=True,
        road_layout="organic"
    )
    
    settlement_response = await map_service.generate_settlement(settlement_request)
    print(f"   Success: {settlement_response.success}")
    print(f"   Generation Time: {settlement_response.generation_time:.2f}s")
    if settlement_response.map_data:
        print(f"   Map Size: {settlement_response.map_data.width}x{settlement_response.map_data.height}")
        print(f"   Population: {settlement_response.map_data.population}")

async def test_location_descriptions():
    """Test location description generation."""
    print("\n=== Testing Location Descriptions ===")
    
    location_service = LocationDescriptionService()
    
    # Test outdoor area description
    print("\n1. Generating Outdoor Location...")
    location_request = LocationDescriptionRequest(
        location_type=LocationType.OUTDOOR_AREA,
        atmosphere=Atmosphere.PEACEFUL,
        include_sensory_details=True,
        detail_level="detailed",
        time_of_day="dawn",
        season="spring"
    )
    
    location_response = await location_service.generate_description(location_request)
    print(f"   Success: {location_response.success}")
    print(f"   Generation Time: {location_response.generation_time:.2f}s")
    if location_response.location_data:
        print(f"   Location: {location_response.location_data.name}")
        print(f"   Description: {location_response.location_data.short_description}")
        print(f"   Visual Details: {len(location_response.location_data.sensory_details.visual)} items")

async def test_weather_system():
    """Test weather generation."""
    print("\n=== Testing Weather System ===")
    
    weather_service = WeatherService()
    
    print("\n1. Generating Weather...")
    weather_request = WeatherGenerationRequest(
        season=SeasonType.SPRING,
        forecast_duration_hours=24,
        include_extreme_weather=True,
        weather_variability=0.7
    )
    
    weather_response = await weather_service.generate_weather(weather_request)
    print(f"   Success: {weather_response.success}")
    print(f"   Generation Time: {weather_response.generation_time:.2f}s")
    if weather_response.current_conditions:
        print(f"   Current Weather: {weather_response.current_conditions.weather_type}")
        print(f"   Temperature: {weather_response.current_conditions.temperature}°C")
        print(f"   Humidity: {weather_response.current_conditions.humidity:.1%}")
    if weather_response.forecast:
        print(f"   Forecast Periods: {len(weather_response.forecast.forecast_periods)}")

async def test_calendar_system():
    """Test calendar and event system."""
    print("\n=== Testing Calendar System ===")
    
    calendar_service = CalendarService()
    
    # Create calendar
    print("\n1. Creating Calendar...")
    calendar_request = CalendarCreationRequest(
        name="Test Calendar",
        cultural_theme="fantasy",
        month_count=12,
        days_per_week=7
    )
    
    calendar_response = await calendar_service.create_calendar(calendar_request)
    print(f"   Success: {calendar_response.success}")
    print(f"   Generation Time: {calendar_response.generation_time:.2f}s")
    if calendar_response.calendar_data:
        print(f"   Calendar: {calendar_response.calendar_data.name}")
        print(f"   Months: {len(calendar_response.calendar_data.months)}")
        print(f"   Holidays: {len(calendar_response.calendar_data.holidays)}")
        
        calendar = calendar_response.calendar_data
        
        # Create an event
        print("\n2. Creating Event...")
        event_request = EventCreationRequest(
            title="Spring Festival",
            description="Annual celebration of spring's arrival",
            event_type=EventType.SEASONAL,
            scope=EventScope.REGIONAL,
            start_date=WorldDate(year=1, month=3, day=15),
            duration_days=3
        )
        
        event_response = await calendar_service.create_event(event_request, calendar)
        print(f"   Success: {event_response.success}")
        if event_response.events:
            event = event_response.events[0]
            print(f"   Event: {event.title}")
            print(f"   Type: {event.event_type}")
            print(f"   Duration: {event.start_date.month}/{event.start_date.day} - {event.end_date.month if event.end_date else 'same'}/{event.end_date.day if event.end_date else event.start_date.day}")

async def test_religion_system():
    """Test pantheon and religion generation."""
    print("\n=== Testing Religion System ===")
    
    religion_service = ReligionService()
    
    print("\n1. Generating Pantheon...")
    pantheon_request = PantheonGenerationRequest(
        name="Test Pantheon",
        religion_type=ReligionType.POLYTHEISTIC,
        deity_count=8,
        cultural_theme="fantasy",
        generate_relationships=True,
        generate_mythology=True,
        generate_orders=True
    )
    
    religion_response = await religion_service.generate_pantheon(pantheon_request)
    print(f"   Success: {religion_response.success}")
    print(f"   Generation Time: {religion_response.generation_time:.2f}s")
    if religion_response.pantheon:
        print(f"   Pantheon: {religion_response.pantheon.name}")
        print(f"   Type: {religion_response.pantheon.religion_type}")
        print(f"   Deities: {len(religion_response.deities)}")
        print(f"   Religious Orders: {len(religion_response.religious_orders)}")
        
        # Show first deity details
        if religion_response.deities:
            deity = religion_response.deities[0]
            print(f"\n   Sample Deity: {deity.name}")
            print(f"   Rank: {deity.rank}")
            print(f"   Domains: {[d.value for d in deity.domains]}")
            print(f"   Alignment: {deity.alignment}")

async def run_all_tests():
    """Run all service tests."""
    print("DM Log World Building Service - Test Suite")
    print("=" * 50)
    
    try:
        await test_map_generation()
        await test_location_descriptions()
        await test_weather_system()
        await test_calendar_system()
        await test_religion_system()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_all_tests())