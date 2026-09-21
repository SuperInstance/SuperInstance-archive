"""
Tide Prediction System for Fishing Spots
Advanced tide prediction with harmonic analysis and fishing spot integration
"""

import asyncio
import json
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class TideType(Enum):
    HIGH = "high"
    LOW = "low"

class TideStage(Enum):
    LOW = "low"
    RISING = "rising" 
    HIGH = "high"
    FALLING = "falling"

@dataclass
class TideEvent:
    time: datetime
    height: float  # meters above chart datum
    tide_type: TideType
    station_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'time': self.time.isoformat(),
            'height': self.height,
            'tide_type': self.tide_type.value,
            'station_id': self.station_id
        }

@dataclass
class TidePrediction:
    timestamp: datetime
    height: float  # meters above chart datum
    stage: TideStage
    rate_of_change: float  # meters per hour
    station_id: str
    next_high: Optional[TideEvent] = None
    next_low: Optional[TideEvent] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'timestamp': self.timestamp.isoformat(),
            'height': self.height,
            'stage': self.stage.value,
            'rate_of_change': self.rate_of_change,
            'station_id': self.station_id
        }
        
        if self.next_high:
            result['next_high'] = self.next_high.to_dict()
        if self.next_low:
            result['next_low'] = self.next_low.to_dict()
            
        return result

@dataclass
class TideStation:
    station_id: str
    name: str
    latitude: float
    longitude: float
    time_zone: str
    datum_offset: float = 0.0  # meters offset from MLLW
    mean_range: Optional[float] = None  # average tidal range in meters
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class HarmonicConstituent:
    """Tidal harmonic constituent for prediction calculations"""
    name: str
    amplitude: float  # meters
    phase: float     # degrees
    speed: float     # degrees per hour
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class NOAATideService:
    """NOAA Tides and Currents API integration"""
    
    BASE_URL = "https://tidesandcurrents.noaa.gov/api/datagetter"
    
    def __init__(self, api_timeout: int = 30):
        self.api_timeout = api_timeout
        
    def get_stations_near_location(self, lat: float, lon: float, radius_km: float = 50.0) -> List[TideStation]:
        """Find NOAA tide stations near a location"""
        # NOAA doesn't have a direct nearby stations API, so we use a predefined list
        # In a real implementation, this would query NOAA's station metadata
        
        # Sample stations (would be loaded from NOAA data)
        sample_stations = [
            TideStation("8518750", "The Battery, NY", 40.7006, -74.0142, "America/New_York", mean_range=1.4),
            TideStation("8516945", "Kings Point, NY", 40.8100, -73.7650, "America/New_York", mean_range=2.1),
            TideStation("8510560", "Montauk, NY", 41.0483, -71.9600, "America/New_York", mean_range=0.9),
            TideStation("8557380", "Lewes, DE", 38.7817, -75.1200, "America/New_York", mean_range=1.2),
            TideStation("8534720", "Atlantic City, NJ", 39.3550, -74.4183, "America/New_York", mean_range=1.3),
            TideStation("8467150", "Bridgeport, CT", 41.1733, -73.1817, "America/New_York", mean_range=2.0),
            TideStation("8461490", "New London, CT", 41.3617, -72.0883, "America/New_York", mean_range=0.9),
        ]
        
        # Calculate distances and filter
        nearby_stations = []
        for station in sample_stations:
            distance = self._calculate_distance(lat, lon, station.latitude, station.longitude)
            if distance <= radius_km:
                nearby_stations.append(station)
        
        # Sort by distance
        nearby_stations.sort(key=lambda s: self._calculate_distance(lat, lon, s.latitude, s.longitude))
        
        return nearby_stations
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in kilometers using haversine formula"""
        R = 6371  # Earth radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def get_tide_predictions(self, station_id: str, start_date: datetime, end_date: datetime) -> List[TideEvent]:
        """Get tide predictions from NOAA API"""
        try:
            params = {
                'product': 'predictions',
                'application': 'fishing_pro',
                'begin_date': start_date.strftime('%Y%m%d'),
                'end_date': end_date.strftime('%Y%m%d'),
                'datum': 'MLLW',
                'station': station_id,
                'time_zone': 'gmt',
                'units': 'metric',
                'interval': 'hilo',  # High and low tides only
                'format': 'json'
            }
            
            # For demonstration, simulate NOAA API response
            return self._simulate_tide_data(station_id, start_date, end_date)
            
            # Real implementation would use:
            # response = requests.get(self.BASE_URL, params=params, timeout=self.api_timeout)
            # response.raise_for_status()
            # data = response.json()
            # return self._parse_noaa_predictions(data, station_id)
            
        except Exception as e:
            logger.error(f"Failed to get tide predictions for station {station_id}: {e}")
            return []
    
    def _simulate_tide_data(self, station_id: str, start_date: datetime, end_date: datetime) -> List[TideEvent]:
        """Simulate tide data for demonstration"""
        tide_events = []
        current_time = start_date
        
        # Semi-diurnal tide pattern (2 highs, 2 lows per day)
        tidal_period = timedelta(hours=12, minutes=25)  # Average semi-diurnal period
        
        # Starting with a low tide
        is_high = False
        tide_count = 0
        
        while current_time < end_date:
            # Simulate tidal heights based on time of year and lunar cycle
            base_range = 1.2  # Base tidal range in meters
            
            # Add some variation based on lunar cycle (spring/neap tides)
            days_since_epoch = (current_time - datetime(2024, 1, 1, tzinfo=timezone.utc)).days
            lunar_cycle = math.sin(2 * math.pi * days_since_epoch / 29.53)  # Lunar month
            range_modifier = 1.0 + 0.4 * lunar_cycle
            
            if is_high:
                # High tide
                height = base_range * range_modifier + 0.3 * math.sin(2 * math.pi * days_since_epoch / 365.25)
                tide_type = TideType.HIGH
            else:
                # Low tide  
                height = -base_range * range_modifier * 0.3 + 0.1 * math.sin(2 * math.pi * days_since_epoch / 365.25)
                tide_type = TideType.LOW
            
            # Add some random variation
            import random
            height += random.uniform(-0.1, 0.1)
            
            tide_event = TideEvent(
                time=current_time,
                height=height,
                tide_type=tide_type,
                station_id=station_id
            )
            
            tide_events.append(tide_event)
            
            # Move to next tide
            # Vary the period slightly to simulate real tides
            period_variation = timedelta(minutes=random.randint(-30, 30))
            current_time += tidal_period + period_variation
            is_high = not is_high
            tide_count += 1
        
        return tide_events

class HarmonicTidePredictor:
    """Advanced harmonic tide prediction using tidal constituents"""
    
    def __init__(self, constituents: List[HarmonicConstituent]):
        self.constituents = constituents
        
        # Standard harmonic constituents with typical values
        # In a real implementation, these would be loaded from NOAA harmonic data
        self.default_constituents = [
            HarmonicConstituent("M2", 0.6, 0.0, 28.9841042),    # Principal lunar semi-diurnal
            HarmonicConstituent("S2", 0.2, 30.0, 30.0),          # Principal solar semi-diurnal
            HarmonicConstituent("N2", 0.12, 15.0, 28.4397295),   # Lunar elliptic semi-diurnal
            HarmonicConstituent("K1", 0.15, 45.0, 15.0410686),   # Lunar diurnal
            HarmonicConstituent("O1", 0.1, 60.0, 13.9430356),    # Lunar diurnal
            HarmonicConstituent("M4", 0.03, 0.0, 57.9682084),    # Shallow water overtide
            HarmonicConstituent("MS4", 0.02, 30.0, 58.9841042),  # Shallow water overtide
        ]
    
    def predict_height(self, timestamp: datetime, station_datum: float = 0.0) -> float:
        """Predict tide height at specific time using harmonic analysis"""
        # Calculate hours since a reference epoch
        reference_epoch = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        hours_since_epoch = (timestamp - reference_epoch).total_seconds() / 3600.0
        
        # Use default constituents if none provided
        constituents = self.constituents if self.constituents else self.default_constituents
        
        # Calculate tide height from harmonic constituents
        tide_height = station_datum
        
        for constituent in constituents:
            # Convert phase to radians
            phase_rad = math.radians(constituent.phase)
            speed_rad_per_hour = math.radians(constituent.speed)
            
            # Calculate constituent contribution
            argument = speed_rad_per_hour * hours_since_epoch + phase_rad
            contribution = constituent.amplitude * math.cos(argument)
            tide_height += contribution
        
        return tide_height
    
    def predict_stage(self, timestamp: datetime, window_minutes: int = 30) -> Tuple[TideStage, float]:
        """Determine tide stage and rate of change"""
        # Calculate tide heights before and after current time
        dt = timedelta(minutes=window_minutes)
        
        height_before = self.predict_height(timestamp - dt)
        height_current = self.predict_height(timestamp)
        height_after = self.predict_height(timestamp + dt)
        
        # Calculate rate of change (meters per hour)
        rate_before = (height_current - height_before) / (window_minutes / 60.0)
        rate_after = (height_after - height_current) / (window_minutes / 60.0)
        average_rate = (rate_before + rate_after) / 2.0
        
        # Determine stage
        if abs(average_rate) < 0.05:  # Near slack water
            if height_current > 0.5:  # Arbitrary threshold for high water
                stage = TideStage.HIGH
            else:
                stage = TideStage.LOW
        elif average_rate > 0:
            stage = TideStage.RISING
        else:
            stage = TideStage.FALLING
        
        return stage, average_rate

class TidePredictionService:
    """Main tide prediction service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.noaa_service = NOAATideService()
        
        # Cache for station data and predictions
        self.station_cache: Dict[str, TideStation] = {}
        self.prediction_cache: Dict[str, List[TideEvent]] = {}
        
        # Default prediction window
        self.default_prediction_days = self.config.get('prediction_days', 7)
        
    def find_nearest_station(self, lat: float, lon: float) -> Optional[TideStation]:
        """Find the nearest tide station to a location"""
        stations = self.noaa_service.get_stations_near_location(lat, lon, radius_km=100.0)
        return stations[0] if stations else None
    
    def get_tide_prediction_for_location(self, lat: float, lon: float, 
                                       timestamp: Optional[datetime] = None) -> Optional[TidePrediction]:
        """Get tide prediction for a specific location and time"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Find nearest station
        station = self.find_nearest_station(lat, lon)
        if not station:
            logger.error(f"No tide station found near {lat}, {lon}")
            return None
        
        return self.get_tide_prediction_for_station(station.station_id, timestamp)
    
    def get_tide_prediction_for_station(self, station_id: str, 
                                      timestamp: Optional[datetime] = None) -> Optional[TidePrediction]:
        """Get tide prediction for a specific station and time"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Get tide events for the period
        start_date = timestamp - timedelta(days=1)
        end_date = timestamp + timedelta(days=self.default_prediction_days)
        
        tide_events = self._get_cached_predictions(station_id, start_date, end_date)
        if not tide_events:
            return None
        
        # Use harmonic prediction for current height and stage
        predictor = HarmonicTidePredictor([])  # Using default constituents
        current_height = predictor.predict_height(timestamp)
        stage, rate_of_change = predictor.predict_stage(timestamp)
        
        # Find next high and low tides
        next_high = None
        next_low = None
        
        for event in tide_events:
            if event.time > timestamp:
                if event.tide_type == TideType.HIGH and next_high is None:
                    next_high = event
                elif event.tide_type == TideType.LOW and next_low is None:
                    next_low = event
                
                if next_high and next_low:
                    break
        
        return TidePrediction(
            timestamp=timestamp,
            height=current_height,
            stage=stage,
            rate_of_change=rate_of_change,
            station_id=station_id,
            next_high=next_high,
            next_low=next_low
        )
    
    def get_tide_events(self, station_id: str, start_date: datetime, 
                       end_date: datetime) -> List[TideEvent]:
        """Get high and low tide events for a station within date range"""
        return self._get_cached_predictions(station_id, start_date, end_date)
    
    def _get_cached_predictions(self, station_id: str, start_date: datetime, 
                              end_date: datetime) -> List[TideEvent]:
        """Get tide predictions with caching"""
        cache_key = f"{station_id}_{start_date.date()}_{end_date.date()}"
        
        if cache_key not in self.prediction_cache:
            predictions = self.noaa_service.get_tide_predictions(station_id, start_date, end_date)
            self.prediction_cache[cache_key] = predictions
        
        return self.prediction_cache[cache_key]
    
    def get_fishing_windows(self, lat: float, lon: float, 
                          preferred_stages: List[TideStage] = None,
                          days_ahead: int = 3) -> List[Dict[str, Any]]:
        """Get optimal fishing windows based on tide preferences"""
        if preferred_stages is None:
            preferred_stages = [TideStage.RISING, TideStage.FALLING]
        
        # Find nearest station
        station = self.find_nearest_station(lat, lon)
        if not station:
            return []
        
        windows = []
        start_time = datetime.now(timezone.utc)
        
        # Check tide conditions every 30 minutes for the next few days
        for hours in range(0, days_ahead * 24, 1):  # Check every hour
            check_time = start_time + timedelta(hours=hours)
            prediction = self.get_tide_prediction_for_station(station.station_id, check_time)
            
            if prediction and prediction.stage in preferred_stages:
                # This could be a good fishing window
                window_start = check_time
                window_end = check_time + timedelta(hours=2)  # 2-hour fishing window
                
                windows.append({
                    'start_time': window_start.isoformat(),
                    'end_time': window_end.isoformat(),
                    'tide_stage': prediction.stage.value,
                    'tide_height': prediction.height,
                    'rate_of_change': prediction.rate_of_change,
                    'next_high': prediction.next_high.to_dict() if prediction.next_high else None,
                    'next_low': prediction.next_low.to_dict() if prediction.next_low else None,
                    'station': station.name,
                    'fishing_score': self._calculate_fishing_score(prediction)
                })
        
        # Remove overlapping windows and sort by fishing score
        consolidated_windows = self._consolidate_windows(windows)
        return sorted(consolidated_windows, key=lambda x: x['fishing_score'], reverse=True)[:20]
    
    def _calculate_fishing_score(self, prediction: TidePrediction) -> float:
        """Calculate fishing quality score based on tide conditions"""
        score = 50.0  # Base score
        
        # Prefer moving water
        if prediction.stage in [TideStage.RISING, TideStage.FALLING]:
            score += 25.0
        
        # Moderate rate of change is often better than extreme
        rate_abs = abs(prediction.rate_of_change)
        if 0.1 < rate_abs < 0.5:
            score += 15.0
        elif rate_abs > 0.8:
            score -= 10.0  # Very fast tide changes can be challenging
        
        # Prefer certain tide heights (mid-range often productive)
        if 0.3 < abs(prediction.height) < 1.5:
            score += 10.0
        
        return min(score, 100.0)  # Cap at 100
    
    def _consolidate_windows(self, windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Consolidate overlapping time windows"""
        if not windows:
            return []
        
        # Sort by start time
        sorted_windows = sorted(windows, key=lambda x: x['start_time'])
        consolidated = [sorted_windows[0]]
        
        for current in sorted_windows[1:]:
            last = consolidated[-1]
            
            # Check if windows overlap
            last_end = datetime.fromisoformat(last['end_time'])
            current_start = datetime.fromisoformat(current['start_time'])
            
            if current_start <= last_end:
                # Merge windows - extend end time and use better score
                current_end = datetime.fromisoformat(current['end_time'])
                last['end_time'] = max(last_end, current_end).isoformat()
                last['fishing_score'] = max(last['fishing_score'], current['fishing_score'])
            else:
                consolidated.append(current)
        
        return consolidated
    
    def get_spot_tide_info(self, spot_lat: float, spot_lon: float, 
                          target_datetime: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive tide information for a fishing spot"""
        if target_datetime is None:
            target_datetime = datetime.now(timezone.utc)
        
        station = self.find_nearest_station(spot_lat, spot_lon)
        if not station:
            return {"error": "No tide station found"}
        
        prediction = self.get_tide_prediction_for_station(station.station_id, target_datetime)
        if not prediction:
            return {"error": "No tide prediction available"}
        
        # Get tide events for context
        start_date = target_datetime - timedelta(hours=12)
        end_date = target_datetime + timedelta(hours=36)
        tide_events = self.get_tide_events(station.station_id, start_date, end_date)
        
        return {
            'station': station.to_dict(),
            'current_prediction': prediction.to_dict(),
            'tide_events': [event.to_dict() for event in tide_events],
            'fishing_windows': self.get_fishing_windows(spot_lat, spot_lon, days_ahead=2)
        }

async def main():
    """Example usage of the tide prediction system"""
    
    # Initialize tide service
    tide_service = TidePredictionService({
        'prediction_days': 7
    })
    
    # Example location (Montauk, NY area)
    lat, lon = 41.0488, -71.8558
    
    print("=== Tide Prediction Example ===")
    
    # Find nearest station
    station = tide_service.find_nearest_station(lat, lon)
    if station:
        print(f"Nearest station: {station.name} ({station.station_id})")
        print(f"Distance from fishing spot: ~{tide_service.noaa_service._calculate_distance(lat, lon, station.latitude, station.longitude):.1f} km")
    
    # Get current tide prediction
    current_prediction = tide_service.get_tide_prediction_for_location(lat, lon)
    if current_prediction:
        print(f"\nCurrent tide conditions:")
        print(f"- Height: {current_prediction.height:.2f} m")
        print(f"- Stage: {current_prediction.stage.value}")
        print(f"- Rate of change: {current_prediction.rate_of_change:.3f} m/hr")
        
        if current_prediction.next_high:
            print(f"- Next high tide: {current_prediction.next_high.time.strftime('%Y-%m-%d %H:%M UTC')} ({current_prediction.next_high.height:.2f}m)")
        
        if current_prediction.next_low:
            print(f"- Next low tide: {current_prediction.next_low.time.strftime('%Y-%m-%d %H:%M UTC')} ({current_prediction.next_low.height:.2f}m)")
    
    # Get fishing windows
    print(f"\nOptimal fishing windows for next 3 days:")
    windows = tide_service.get_fishing_windows(lat, lon, days_ahead=3)
    
    for i, window in enumerate(windows[:5], 1):  # Show top 5
        start_time = datetime.fromisoformat(window['start_time'])
        end_time = datetime.fromisoformat(window['end_time'])
        print(f"{i}. {start_time.strftime('%m/%d %H:%M')} - {end_time.strftime('%H:%M')} UTC")
        print(f"   Tide: {window['tide_stage']} ({window['tide_height']:.2f}m)")
        print(f"   Fishing score: {window['fishing_score']:.0f}/100")
    
    # Get comprehensive spot tide info
    print(f"\nComprehensive tide info for spot:")
    spot_info = tide_service.get_spot_tide_info(lat, lon)
    
    if 'station' in spot_info:
        print(f"Using station: {spot_info['station']['name']}")
        
        current = spot_info['current_prediction']
        print(f"Current: {current['stage']} tide at {current['height']:.2f}m")
        
        print(f"\nNext tide events:")
        for event in spot_info['tide_events'][:6]:  # Next 6 events
            event_time = datetime.fromisoformat(event['time'])
            print(f"- {event_time.strftime('%m/%d %H:%M')}: {event['tide_type']} ({event['height']:.2f}m)")

if __name__ == "__main__":
    asyncio.run(main())