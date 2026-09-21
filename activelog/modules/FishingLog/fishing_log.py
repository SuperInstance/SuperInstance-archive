"""
FishingLog Module - Advanced fishing trip management with NMEA integration and computer vision.
Features: NMEA data parsing, fish counting CV, Coast Guard compliance, trip analytics.
"""

import asyncio
import json
import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import re
import math

@dataclass
class NMEASentence:
    """Parsed NMEA sentence data."""
    sentence_type: str
    timestamp: datetime
    data: Dict[str, Any]
    raw: str

@dataclass
class GPS_Position:
    """GPS position data from NMEA."""
    latitude: float
    longitude: float
    timestamp: datetime
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None

@dataclass
class FishCatch:
    """Individual fish catch record."""
    id: str
    species: str
    length: Optional[float]
    weight: Optional[float]
    timestamp: datetime
    location: GPS_Position
    image_path: Optional[str] = None
    confidence: float = 1.0
    method: str = "manual"  # manual, cv_detected, cv_confirmed

@dataclass
class TripData:
    """Complete fishing trip data."""
    id: str
    start_time: datetime
    end_time: Optional[datetime]
    start_location: GPS_Position
    end_location: Optional[GPS_Position]
    catches: List[FishCatch]
    nmea_log: List[NMEASentence]
    weather_conditions: Dict[str, Any]
    compliance_data: Dict[str, Any]

class NMEAParser:
    """NMEA 0183 sentence parser for marine electronics integration."""
    
    def __init__(self):
        self.sentence_parsers = {
            'GPGGA': self._parse_gga,
            'GPRMC': self._parse_rmc,
            'GPVTG': self._parse_vtg,
            'GPGLL': self._parse_gll,
            'SDDBT': self._parse_dbt,
            'SDMTW': self._parse_mtw,
            'WIMWV': self._parse_mwv
        }
    
    def parse_sentence(self, sentence: str) -> Optional[NMEASentence]:
        """Parse a single NMEA sentence."""
        try:
            sentence = sentence.strip()
            if not sentence.startswith('$'):
                return None
            
            # Remove checksum
            if '*' in sentence:
                sentence = sentence.split('*')[0]
            
            parts = sentence[1:].split(',')
            sentence_type = parts[0]
            
            if sentence_type in self.sentence_parsers:
                data = self.sentence_parsers[sentence_type](parts)
                return NMEASentence(
                    sentence_type=sentence_type,
                    timestamp=datetime.now(),
                    data=data,
                    raw=sentence
                )
            
        except Exception as e:
            print(f"Error parsing NMEA sentence: {e}")
        
        return None
    
    def _parse_gga(self, parts: List[str]) -> Dict[str, Any]:
        """Parse GGA sentence (Global Positioning System Fix Data)."""
        return {
            'time': parts[1] if len(parts) > 1 else None,
            'latitude': self._parse_coordinate(parts[2], parts[3]) if len(parts) > 3 else None,
            'longitude': self._parse_coordinate(parts[4], parts[5]) if len(parts) > 5 else None,
            'fix_quality': int(parts[6]) if len(parts) > 6 and parts[6] else 0,
            'num_satellites': int(parts[7]) if len(parts) > 7 and parts[7] else 0,
            'horizontal_dilution': float(parts[8]) if len(parts) > 8 and parts[8] else None,
            'altitude': float(parts[9]) if len(parts) > 9 and parts[9] else None,
            'altitude_units': parts[10] if len(parts) > 10 else None
        }
    
    def _parse_rmc(self, parts: List[str]) -> Dict[str, Any]:
        """Parse RMC sentence (Recommended Minimum Navigation Information)."""
        return {
            'time': parts[1] if len(parts) > 1 else None,
            'status': parts[2] if len(parts) > 2 else None,
            'latitude': self._parse_coordinate(parts[3], parts[4]) if len(parts) > 4 else None,
            'longitude': self._parse_coordinate(parts[5], parts[6]) if len(parts) > 6 else None,
            'speed': float(parts[7]) if len(parts) > 7 and parts[7] else None,
            'course': float(parts[8]) if len(parts) > 8 and parts[8] else None,
            'date': parts[9] if len(parts) > 9 else None,
            'magnetic_variation': parts[10] if len(parts) > 10 else None
        }
    
    def _parse_vtg(self, parts: List[str]) -> Dict[str, Any]:
        """Parse VTG sentence (Track Made Good and Ground Speed)."""
        return {
            'true_course': float(parts[1]) if len(parts) > 1 and parts[1] else None,
            'magnetic_course': float(parts[3]) if len(parts) > 3 and parts[3] else None,
            'speed_knots': float(parts[5]) if len(parts) > 5 and parts[5] else None,
            'speed_kmh': float(parts[7]) if len(parts) > 7 and parts[7] else None
        }
    
    def _parse_gll(self, parts: List[str]) -> Dict[str, Any]:
        """Parse GLL sentence (Geographic Position - Latitude/Longitude)."""
        return {
            'latitude': self._parse_coordinate(parts[1], parts[2]) if len(parts) > 2 else None,
            'longitude': self._parse_coordinate(parts[3], parts[4]) if len(parts) > 4 else None,
            'time': parts[5] if len(parts) > 5 else None,
            'status': parts[6] if len(parts) > 6 else None
        }
    
    def _parse_dbt(self, parts: List[str]) -> Dict[str, Any]:
        """Parse DBT sentence (Depth Below Transducer)."""
        return {
            'depth_feet': float(parts[1]) if len(parts) > 1 and parts[1] else None,
            'depth_meters': float(parts[3]) if len(parts) > 3 and parts[3] else None,
            'depth_fathoms': float(parts[5]) if len(parts) > 5 and parts[5] else None
        }
    
    def _parse_mtw(self, parts: List[str]) -> Dict[str, Any]:
        """Parse MTW sentence (Mean Temperature of Water)."""
        return {
            'temperature': float(parts[1]) if len(parts) > 1 and parts[1] else None,
            'units': parts[2] if len(parts) > 2 else None
        }
    
    def _parse_mwv(self, parts: List[str]) -> Dict[str, Any]:
        """Parse MWV sentence (Wind Speed and Angle)."""
        return {
            'wind_angle': float(parts[1]) if len(parts) > 1 and parts[1] else None,
            'reference': parts[2] if len(parts) > 2 else None,
            'wind_speed': float(parts[3]) if len(parts) > 3 and parts[3] else None,
            'speed_units': parts[4] if len(parts) > 4 else None,
            'status': parts[5] if len(parts) > 5 else None
        }
    
    def _parse_coordinate(self, coord_str: str, direction: str) -> Optional[float]:
        """Parse NMEA coordinate format to decimal degrees."""
        if not coord_str or not direction:
            return None
        
        try:
            if len(coord_str) >= 4:
                degrees = float(coord_str[:-7])
                minutes = float(coord_str[-7:])
                decimal = degrees + minutes / 60.0
                
                if direction in ['S', 'W']:
                    decimal = -decimal
                
                return decimal
        except:
            pass
        
        return None

class FishCounterCV:
    """Computer vision system for automated fish detection and counting."""
    
    def __init__(self):
        self.fish_cascade = None
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2()
        self.species_classifiers = {}
        self.size_estimator = None
        
        # Initialize with mock classifiers (in real implementation, load trained models)
        self._initialize_classifiers()
    
    def _initialize_classifiers(self):
        """Initialize CV classifiers and models."""
        # Mock initialization - in real implementation, load trained models
        self.species_mapping = {
            0: "Bass",
            1: "Trout",
            2: "Salmon",
            3: "Pike",
            4: "Perch",
            5: "Catfish",
            6: "Unknown"
        }
        
        print("✅ Fish detection classifiers initialized")
    
    def detect_fish(self, image: np.ndarray, reference_object_size: Optional[float] = None) -> List[Dict[str, Any]]:
        """Detect fish in an image using computer vision."""
        detections = []
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply background subtraction for moving fish
            fg_mask = self.background_subtractor.apply(image)
            
            # Find contours
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                
                # Filter by area (fish should be reasonably sized)
                if 100 < area < 50000:
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Extract fish region
                    fish_roi = image[y:y+h, x:x+w]
                    
                    # Classify species (mock classification)
                    species_id = self._classify_species(fish_roi)
                    species = self.species_mapping.get(species_id, "Unknown")
                    
                    # Estimate size
                    length_estimate = self._estimate_length(w, h, reference_object_size)
                    weight_estimate = self._estimate_weight(length_estimate, species)
                    
                    detection = {
                        'id': f"fish_{i}_{datetime.now().timestamp()}",
                        'species': species,
                        'confidence': np.random.uniform(0.6, 0.95),  # Mock confidence
                        'bbox': (x, y, w, h),
                        'area': area,
                        'estimated_length': length_estimate,
                        'estimated_weight': weight_estimate,
                        'timestamp': datetime.now()
                    }
                    
                    detections.append(detection)
            
        except Exception as e:
            print(f"Error in fish detection: {e}")
        
        return detections
    
    def _classify_species(self, fish_roi: np.ndarray) -> int:
        """Classify fish species from image region."""
        # Mock classification - in real implementation, use trained CNN
        return np.random.randint(0, len(self.species_mapping))
    
    def _estimate_length(self, width: int, height: int, reference_size: Optional[float] = None) -> float:
        """Estimate fish length from bounding box dimensions."""
        # Simple estimation based on pixel dimensions
        # In real implementation, use reference objects and perspective correction
        pixel_length = max(width, height)
        
        if reference_size:
            # Use reference object for scale
            estimated_length = (pixel_length / 100) * reference_size  # Mock calculation
        else:
            # Use average pixel-to-cm ratio
            estimated_length = pixel_length * 0.1  # Mock: 0.1 cm per pixel
        
        return max(5.0, min(100.0, estimated_length))  # Clamp to reasonable range
    
    def _estimate_weight(self, length: float, species: str) -> float:
        """Estimate fish weight from length and species."""
        # Species-specific length-weight relationships
        species_factors = {
            "Bass": 0.12,
            "Trout": 0.08,
            "Salmon": 0.15,
            "Pike": 0.06,
            "Perch": 0.10,
            "Catfish": 0.14,
            "Unknown": 0.10
        }
        
        factor = species_factors.get(species, 0.10)
        # Weight = factor * length^3 (approximate allometric relationship)
        weight = factor * (length ** 3) / 1000  # Convert to kg
        
        return max(0.1, min(50.0, weight))  # Clamp to reasonable range
    
    def count_fish_in_video(self, video_path: str) -> Dict[str, Any]:
        """Count and analyze fish in a video file."""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return {"error": "Could not open video file"}
        
        total_detections = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Process every 10th frame for efficiency
            if frame_count % 10 == 0:
                detections = self.detect_fish(frame)
                for detection in detections:
                    detection['frame'] = frame_count
                    total_detections.append(detection)
        
        cap.release()
        
        # Analyze results
        species_count = {}
        total_weight = 0
        avg_length = 0
        
        for detection in total_detections:
            species = detection['species']
            species_count[species] = species_count.get(species, 0) + 1
            total_weight += detection.get('estimated_weight', 0)
            avg_length += detection.get('estimated_length', 0)
        
        if total_detections:
            avg_length /= len(total_detections)
        
        return {
            "total_fish_detected": len(total_detections),
            "species_breakdown": species_count,
            "total_estimated_weight_kg": round(total_weight, 2),
            "average_length_cm": round(avg_length, 2),
            "frames_processed": frame_count,
            "detections": total_detections
        }

class CoastGuardCompliance:
    """Coast Guard compliance and reporting system."""
    
    def __init__(self):
        self.regulations = self._load_regulations()
        self.reporting_endpoints = {
            "NOAA": "https://api.fisheries.noaa.gov/reporting",
            "state_wildlife": "https://api.statefish.gov/reports",
            "vessel_monitoring": "https://api.uscg.gov/vms"
        }
    
    def _load_regulations(self) -> Dict[str, Any]:
        """Load fishing regulations database."""
        return {
            "species_limits": {
                "Bass": {"daily_limit": 5, "size_limit_cm": 35.6, "season": "year_round"},
                "Trout": {"daily_limit": 5, "size_limit_cm": 20.3, "season": "april_october"},
                "Salmon": {"daily_limit": 2, "size_limit_cm": 45.7, "season": "june_september"},
                "Pike": {"daily_limit": 3, "size_limit_cm": 53.3, "season": "may_march"},
                "Perch": {"daily_limit": 25, "size_limit_cm": 15.2, "season": "year_round"},
                "Catfish": {"daily_limit": 10, "size_limit_cm": 25.4, "season": "year_round"}
            },
            "licensing_requirements": {
                "freshwater_license": True,
                "saltwater_license": False,
                "special_permits": []
            },
            "reporting_requirements": {
                "trip_reports": True,
                "catch_reports": True,
                "vessel_monitoring": False
            }
        }
    
    def check_compliance(self, trip_data: TripData) -> Dict[str, Any]:
        """Check trip compliance with regulations."""
        compliance_issues = []
        warnings = []
        
        # Check daily limits
        species_count = {}
        oversized_fish = []
        undersized_fish = []
        
        for catch in trip_data.catches:
            species = catch.species
            species_count[species] = species_count.get(species, 0) + 1
            
            # Check size limits
            if species in self.regulations["species_limits"]:
                limits = self.regulations["species_limits"][species]
                
                if catch.length and catch.length < limits["size_limit_cm"]:
                    undersized_fish.append(catch)
                
                # Check daily limits
                if species_count[species] > limits["daily_limit"]:
                    compliance_issues.append(f"Daily limit exceeded for {species}: {species_count[species]} > {limits['daily_limit']}")
        
        # Check season restrictions
        current_month = trip_data.start_time.strftime("%B").lower()
        for species, count in species_count.items():
            if species in self.regulations["species_limits"]:
                season = self.regulations["species_limits"][species]["season"]
                if season != "year_round" and not self._check_season(current_month, season):
                    compliance_issues.append(f"Out of season catch: {species} (season: {season})")
        
        # Generate compliance report
        compliance_score = max(0, 100 - len(compliance_issues) * 20 - len(warnings) * 5)
        
        return {
            "compliance_score": compliance_score,
            "issues": compliance_issues,
            "warnings": warnings,
            "species_count": species_count,
            "undersized_fish": len(undersized_fish),
            "oversized_fish": len(oversized_fish),
            "license_status": "valid",
            "reporting_required": self.regulations["reporting_requirements"]["trip_reports"]
        }
    
    def _check_season(self, current_month: str, season: str) -> bool:
        """Check if current month is within fishing season."""
        season_months = {
            "april_october": ["april", "may", "june", "july", "august", "september", "october"],
            "june_september": ["june", "july", "august", "september"],
            "may_march": ["may", "june", "july", "august", "september", "october", "november", "december", "january", "february", "march"]
        }
        
        return current_month in season_months.get(season, [])
    
    def generate_report(self, trip_data: TripData) -> Dict[str, Any]:
        """Generate official compliance report for authorities."""
        compliance = self.check_compliance(trip_data)
        
        report = {
            "report_id": f"RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "vessel_info": {
                "vessel_id": "MOCK_VESSEL_123",
                "operator": "John Angler",
                "license_number": "FL123456789"
            },
            "trip_details": {
                "start_time": trip_data.start_time.isoformat(),
                "end_time": trip_data.end_time.isoformat() if trip_data.end_time else None,
                "start_location": asdict(trip_data.start_location),
                "end_location": asdict(trip_data.end_location) if trip_data.end_location else None,
                "duration_hours": self._calculate_trip_duration(trip_data)
            },
            "catch_summary": compliance["species_count"],
            "compliance_status": compliance,
            "environmental_data": trip_data.weather_conditions,
            "generated_at": datetime.now().isoformat()
        }
        
        return report
    
    def _calculate_trip_duration(self, trip_data: TripData) -> float:
        """Calculate trip duration in hours."""
        if trip_data.end_time:
            delta = trip_data.end_time - trip_data.start_time
            return delta.total_seconds() / 3600
        return 0.0
    
    async def submit_report(self, report: Dict[str, Any], endpoint: str = "NOAA") -> Dict[str, Any]:
        """Submit compliance report to authorities."""
        # Mock submission - in real implementation, make HTTP requests
        print(f"📋 Submitting report {report['report_id']} to {endpoint}")
        
        return {
            "submission_id": f"SUB_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "accepted",
            "endpoint": endpoint,
            "submitted_at": datetime.now().isoformat(),
            "confirmation_number": f"CONF_{np.random.randint(100000, 999999)}"
        }

class FishingLog:
    """Main FishingLog module orchestrator."""
    
    def __init__(self):
        self.nmea_parser = NMEAParser()
        self.fish_counter = FishCounterCV()
        self.compliance = CoastGuardCompliance()
        self.active_trip = None
        self.trip_history = []
        
        print("🎣 FishingLog module initialized")
    
    async def start_trip(self, location: GPS_Position) -> str:
        """Start a new fishing trip."""
        trip_id = f"TRIP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.active_trip = TripData(
            id=trip_id,
            start_time=datetime.now(),
            end_time=None,
            start_location=location,
            end_location=None,
            catches=[],
            nmea_log=[],
            weather_conditions={},
            compliance_data={}
        )
        
        print(f"🚤 Started fishing trip: {trip_id}")
        return trip_id
    
    async def end_trip(self, location: GPS_Position) -> Dict[str, Any]:
        """End the current fishing trip."""
        if not self.active_trip:
            return {"error": "No active trip to end"}
        
        self.active_trip.end_time = datetime.now()
        self.active_trip.end_location = location
        
        # Run compliance check
        compliance_report = self.compliance.check_compliance(self.active_trip)
        self.active_trip.compliance_data = compliance_report
        
        # Save trip
        self.trip_history.append(self.active_trip)
        trip_summary = self._generate_trip_summary(self.active_trip)
        
        self.active_trip = None
        
        print(f"🏁 Trip ended. Caught {len(trip_summary['catches'])} fish")
        return trip_summary
    
    async def log_catch(self, species: str, length: Optional[float] = None, 
                       weight: Optional[float] = None, image_path: Optional[str] = None,
                       location: Optional[GPS_Position] = None) -> str:
        """Log a manual fish catch."""
        if not self.active_trip:
            return {"error": "No active trip"}
        
        catch_id = f"CATCH_{len(self.active_trip.catches) + 1}_{datetime.now().strftime('%H%M%S')}"
        
        catch = FishCatch(
            id=catch_id,
            species=species,
            length=length,
            weight=weight,
            timestamp=datetime.now(),
            location=location or self.active_trip.start_location,
            image_path=image_path,
            method="manual"
        )
        
        self.active_trip.catches.append(catch)
        
        print(f"🐟 Logged catch: {species} ({catch_id})")
        return catch_id
    
    async def process_nmea_stream(self, nmea_data: str) -> Dict[str, Any]:
        """Process NMEA data stream from marine electronics."""
        sentences = nmea_data.strip().split('\n')
        parsed_sentences = []
        
        for sentence in sentences:
            parsed = self.nmea_parser.parse_sentence(sentence)
            if parsed:
                parsed_sentences.append(parsed)
                
                if self.active_trip:
                    self.active_trip.nmea_log.append(parsed)
                    
                    # Update trip location if GPS data
                    if parsed.sentence_type in ['GPGGA', 'GPRMC'] and parsed.data.get('latitude'):
                        self.active_trip.end_location = GPS_Position(
                            latitude=parsed.data['latitude'],
                            longitude=parsed.data['longitude'],
                            timestamp=parsed.timestamp
                        )
        
        return {
            "sentences_processed": len(sentences),
            "valid_sentences": len(parsed_sentences),
            "active_trip": self.active_trip.id if self.active_trip else None
        }
    
    async def analyze_catch_video(self, video_path: str) -> Dict[str, Any]:
        """Analyze video for automatic fish detection and counting."""
        print(f"🎥 Analyzing video: {video_path}")
        
        analysis_result = self.fish_counter.count_fish_in_video(video_path)
        
        if self.active_trip and not analysis_result.get("error"):
            # Add CV detections to trip
            for detection in analysis_result.get("detections", []):
                catch = FishCatch(
                    id=detection['id'],
                    species=detection['species'],
                    length=detection['estimated_length'],
                    weight=detection['estimated_weight'],
                    timestamp=detection['timestamp'],
                    location=self.active_trip.end_location or self.active_trip.start_location,
                    confidence=detection['confidence'],
                    method="cv_detected"
                )
                self.active_trip.catches.append(catch)
        
        return analysis_result
    
    def _generate_trip_summary(self, trip: TripData) -> Dict[str, Any]:
        """Generate comprehensive trip summary."""
        species_count = {}
        total_weight = 0
        avg_length = 0
        
        for catch in trip.catches:
            species_count[catch.species] = species_count.get(catch.species, 0) + 1
            if catch.weight:
                total_weight += catch.weight
            if catch.length:
                avg_length += catch.length
        
        if trip.catches:
            avg_length /= len(trip.catches)
        
        duration = 0
        if trip.end_time:
            duration = (trip.end_time - trip.start_time).total_seconds() / 3600
        
        return {
            "trip_id": trip.id,
            "duration_hours": round(duration, 2),
            "catches": len(trip.catches),
            "species_breakdown": species_count,
            "total_weight_kg": round(total_weight, 2),
            "average_length_cm": round(avg_length, 2),
            "compliance_score": trip.compliance_data.get("compliance_score", 0),
            "nmea_sentences": len(trip.nmea_log),
            "start_location": asdict(trip.start_location),
            "end_location": asdict(trip.end_location) if trip.end_location else None
        }
    
    async def get_trip_analytics(self) -> Dict[str, Any]:
        """Get comprehensive fishing analytics."""
        if not self.trip_history:
            return {"message": "No trips recorded yet"}
        
        total_trips = len(self.trip_history)
        total_catches = sum(len(trip.catches) for trip in self.trip_history)
        total_hours = sum(
            (trip.end_time - trip.start_time).total_seconds() / 3600 
            for trip in self.trip_history if trip.end_time
        )
        
        species_totals = {}
        best_trip = max(self.trip_history, key=lambda t: len(t.catches))
        
        for trip in self.trip_history:
            for catch in trip.catches:
                species_totals[catch.species] = species_totals.get(catch.species, 0) + 1
        
        return {
            "total_trips": total_trips,
            "total_catches": total_catches,
            "total_fishing_hours": round(total_hours, 2),
            "catches_per_hour": round(total_catches / total_hours if total_hours > 0 else 0, 2),
            "species_breakdown": species_totals,
            "best_trip": {
                "trip_id": best_trip.id,
                "catches": len(best_trip.catches),
                "date": best_trip.start_time.strftime("%Y-%m-%d")
            },
            "average_compliance_score": round(
                sum(trip.compliance_data.get("compliance_score", 0) for trip in self.trip_history) / total_trips, 1
            )
        }

# CLI interface for testing
async def main():
    """CLI interface for FishingLog module."""
    fishing_log = FishingLog()
    
    print("🎣 FishingLog Module Test Suite")
    print("=" * 40)
    
    # Test 1: Start a trip
    print("\n1. Starting fishing trip...")
    start_location = GPS_Position(
        latitude=25.7617,
        longitude=-80.1918,
        timestamp=datetime.now()
    )
    trip_id = await fishing_log.start_trip(start_location)
    print(f"✅ Trip started: {trip_id}")
    
    # Test 2: Process NMEA data
    print("\n2. Processing NMEA data...")
    sample_nmea = """$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
$SDDBT,16.2,f,4.9,M,2.7,F*00"""
    
    nmea_result = await fishing_log.process_nmea_stream(sample_nmea)
    print(f"✅ NMEA processed: {nmea_result}")
    
    # Test 3: Log manual catches
    print("\n3. Logging manual catches...")
    catch1 = await fishing_log.log_catch("Bass", length=45.7, weight=2.3)
    catch2 = await fishing_log.log_catch("Trout", length=30.5, weight=1.1)
    print(f"✅ Logged catches: {catch1}, {catch2}")
    
    # Test 4: Fish counter CV (mock video)
    print("\n4. Testing fish detection CV...")
    # In real implementation, this would process actual video
    mock_video_result = {
        "total_fish_detected": 3,
        "species_breakdown": {"Bass": 2, "Trout": 1},
        "total_estimated_weight_kg": 4.8,
        "average_length_cm": 38.2
    }
    print(f"✅ CV Analysis: {mock_video_result}")
    
    # Test 5: End trip and check compliance
    print("\n5. Ending trip and checking compliance...")
    end_location = GPS_Position(
        latitude=25.7700,
        longitude=-80.1800,
        timestamp=datetime.now()
    )
    trip_summary = await fishing_log.end_trip(end_location)
    print(f"✅ Trip ended: {trip_summary}")
    
    # Test 6: Generate compliance report
    print("\n6. Generating compliance report...")
    if fishing_log.trip_history:
        last_trip = fishing_log.trip_history[-1]
        compliance_report = fishing_log.compliance.generate_report(last_trip)
        print(f"✅ Compliance report: {compliance_report['report_id']}")
        
        # Submit to authorities
        submission = await fishing_log.compliance.submit_report(compliance_report)
        print(f"✅ Report submitted: {submission['confirmation_number']}")
    
    # Test 7: Trip analytics
    print("\n7. Getting trip analytics...")
    analytics = await fishing_log.get_trip_analytics()
    print(f"✅ Analytics: {analytics}")
    
    print("\n🎉 FishingLog module tests completed!")

if __name__ == "__main__":
    asyncio.run(main())