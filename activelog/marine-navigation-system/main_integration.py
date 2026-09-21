"""
Marine Navigation System - Main Integration
Complete integration of NMEA devices, weather radar, fish identification, and regulation compliance
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
import json
from dataclasses import dataclass, field

# Import all modules
from nmea_integration.nmea_parser import (
    NMEAIntegrationManager, NMEADevice, GPSPosition, 
    DepthData, WindData, WaterData, EngineData
)
from weather_radar.weather_radar import (
    WeatherRadarManager, WeatherRadarConfig, WeatherDataSource,
    WeatherRadarData, WeatherAlert
)
from fish_identifier.fish_species_identifier import (
    FishSpeciesIdentifier, FishSpecies, IdentificationResult,
    FishHabitat
)
from regulation_compliance.fishing_regulations import (
    RegulationChecker, ComplianceCheck, FishingRegulation,
    WaterType, ViolationSeverity
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarineSystemConfig:
    # NMEA Configuration
    nmea_devices: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Weather Configuration
    weather_api_key: Optional[str] = None
    weather_update_interval: int = 300
    weather_radar_range: float = 50.0
    
    # Fish ID Configuration
    fish_id_model_path: Optional[str] = None
    
    # General Configuration
    auto_compliance_check: bool = True
    save_identifications: bool = True
    log_level: str = "INFO"

@dataclass
class SystemStatus:
    nmea_connected: bool = False
    weather_active: bool = False
    fish_id_ready: bool = False
    regulations_loaded: bool = False
    current_location: Optional[Tuple[float, float]] = None
    current_depth: Optional[float] = None
    water_temperature: Optional[float] = None
    last_update: datetime = field(default_factory=datetime.now)

class MarineNavigationSystem:
    """
    Integrated marine navigation system combining:
    - NMEA device integration
    - Weather radar overlay
    - Fish species identification
    - Fishing regulation compliance
    """
    
    def __init__(self, config: MarineSystemConfig):
        self.config = config
        self.status = SystemStatus()
        
        # Initialize subsystems
        self.nmea_manager = NMEAIntegrationManager()
        self.weather_manager = None
        self.fish_identifier = FishSpeciesIdentifier(config.fish_id_model_path)
        self.regulation_checker = RegulationChecker()
        
        # Data storage
        self.current_nmea_data = None
        self.current_weather_data = None
        self.identification_history = []
        self.compliance_history = []
        
        # Callbacks
        self.location_callbacks = []
        self.weather_callbacks = []
        self.fish_id_callbacks = []
        self.compliance_callbacks = []
        
        # Setup logging
        logging.getLogger().setLevel(getattr(logging, config.log_level))
    
    async def initialize(self):
        """Initialize all subsystems"""
        logger.info("🌊 Initializing Marine Navigation System")
        
        try:
            # Initialize NMEA devices
            await self._initialize_nmea()
            
            # Initialize weather radar
            await self._initialize_weather()
            
            # Initialize fish identifier
            await self._initialize_fish_identifier()
            
            # Initialize regulation checker
            await self._initialize_regulations()
            
            # Setup data flow
            self._setup_data_callbacks()
            
            logger.info("✅ Marine Navigation System initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize system: {e}")
            raise
    
    async def _initialize_nmea(self):
        """Initialize NMEA device integration"""
        logger.info("🛰️ Initializing NMEA devices...")
        
        for device_id, device_config in self.config.nmea_devices.items():
            try:
                device = NMEADevice(**device_config)
                self.nmea_manager.add_device(device_id, device)
                logger.info(f"Added NMEA device: {device_id}")
            except Exception as e:
                logger.error(f"Failed to add NMEA device {device_id}: {e}")
        
        # Connect all devices
        await self.nmea_manager.connect_all_devices()
        self.status.nmea_connected = True
        
        logger.info("✅ NMEA devices initialized")
    
    async def _initialize_weather(self):
        """Initialize weather radar system"""
        logger.info("🌦️ Initializing weather radar...")
        
        try:
            weather_config = WeatherRadarConfig(
                data_source=WeatherDataSource.NOAA_NEXRAD,
                api_key=self.config.weather_api_key,
                update_interval=self.config.weather_update_interval,
                radar_range=self.config.weather_radar_range,
                opacity=0.7,
                show_lightning=True,
                show_wind_barbs=True
            )
            
            self.weather_manager = WeatherRadarManager(weather_config)
            await self.weather_manager.initialize()
            self.status.weather_active = True
            
            logger.info("✅ Weather radar initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize weather radar: {e}")
            self.weather_manager = None
    
    async def _initialize_fish_identifier(self):
        """Initialize fish species identifier"""
        logger.info("🐟 Initializing fish species identifier...")
        
        try:
            # Fish identifier is initialized in constructor
            self.status.fish_id_ready = True
            logger.info("✅ Fish species identifier ready")
            
        except Exception as e:
            logger.error(f"Failed to initialize fish identifier: {e}")
    
    async def _initialize_regulations(self):
        """Initialize regulation compliance checker"""
        logger.info("📋 Initializing fishing regulations...")
        
        try:
            # Regulation checker is initialized in constructor
            # Update regulations from official sources
            await self.regulation_checker.update_regulations_from_api()
            self.status.regulations_loaded = True
            logger.info("✅ Fishing regulations loaded")
            
        except Exception as e:
            logger.error(f"Failed to initialize regulations: {e}")
    
    def _setup_data_callbacks(self):
        """Setup data flow between subsystems"""
        
        # NMEA data callback
        def on_nmea_data(nmea_data):
            self.current_nmea_data = nmea_data
            
            # Update system status
            if nmea_data.gps:
                self.status.current_location = (nmea_data.gps.latitude, nmea_data.gps.longitude)
            
            if nmea_data.depth:
                self.status.current_depth = nmea_data.depth.depth_meters
            
            if nmea_data.water:
                self.status.water_temperature = nmea_data.water.temperature_celsius
            
            self.status.last_update = datetime.now()
            
            # Notify location callbacks
            if nmea_data.gps:
                for callback in self.location_callbacks:
                    try:
                        callback(nmea_data.gps.latitude, nmea_data.gps.longitude)
                    except Exception as e:
                        logger.error(f"Error in location callback: {e}")
            
            # Auto-update weather based on location
            if self.weather_manager and nmea_data.gps:
                asyncio.create_task(self._update_weather_for_location(
                    nmea_data.gps.latitude, nmea_data.gps.longitude
                ))
        
        self.nmea_manager.add_data_callback(on_nmea_data)
        
        # Weather data callback
        if self.weather_manager:
            def on_weather_data(weather_data):
                self.current_weather_data = weather_data
                
                for callback in self.weather_callbacks:
                    try:
                        callback(weather_data)
                    except Exception as e:
                        logger.error(f"Error in weather callback: {e}")
            
            self.weather_manager.add_data_callback(on_weather_data)
    
    async def _update_weather_for_location(self, lat: float, lon: float):
        """Update weather data for new location"""
        if self.weather_manager:
            try:
                await self.weather_manager.start_updates(
                    lat, lon, self.config.weather_radar_range
                )
            except Exception as e:
                logger.error(f"Failed to update weather for location: {e}")
    
    # Public API Methods
    
    def get_current_position(self) -> Optional[GPSPosition]:
        """Get current GPS position"""
        if self.current_nmea_data and self.current_nmea_data.gps:
            return self.current_nmea_data.gps
        return None
    
    def get_current_depth(self) -> Optional[float]:
        """Get current depth in meters"""
        if self.current_nmea_data and self.current_nmea_data.depth:
            return self.current_nmea_data.depth.depth_meters
        return None
    
    def get_water_temperature(self) -> Optional[float]:
        """Get current water temperature in Celsius"""
        if self.current_nmea_data and self.current_nmea_data.water:
            return self.current_nmea_data.water.temperature_celsius
        return None
    
    def get_wind_data(self) -> Optional[WindData]:
        """Get current wind data"""
        if self.current_nmea_data and self.current_nmea_data.wind:
            return self.current_nmea_data.wind
        return None
    
    def get_weather_data(self) -> Optional[WeatherRadarData]:
        """Get current weather radar data"""
        return self.current_weather_data
    
    def get_weather_alerts(self) -> List[WeatherAlert]:
        """Get current weather alerts"""
        if self.current_weather_data:
            return self.current_weather_data.weather_alerts
        return []
    
    async def identify_fish(self, image_path: str) -> Optional[IdentificationResult]:
        """Identify fish species from image"""
        try:
            position = self.get_current_position()
            location = (position.latitude, position.longitude) if position else None
            
            result = await self.fish_identifier.identify_from_image(
                image=image_path,
                location=location,
                water_temp=self.get_water_temperature(),
                depth=self.get_current_depth()
            )
            
            if self.config.save_identifications:
                self.identification_history.append(result)
            
            # Notify callbacks
            for callback in self.fish_id_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Error in fish ID callback: {e}")
            
            # Auto compliance check
            if self.config.auto_compliance_check and result.identifications:
                species_names = [id.species.common_name for id in result.identifications]
                await self._auto_compliance_check(species_names)
            
            return result
            
        except Exception as e:
            logger.error(f"Fish identification error: {e}")
            return None
    
    async def check_fishing_compliance(self, 
                                     target_species: List[str],
                                     fishing_date: date = None,
                                     gear_types: List[str] = None,
                                     fish_sizes: Dict[str, float] = None,
                                     catch_counts: Dict[str, int] = None) -> Optional[ComplianceCheck]:
        """Check fishing regulation compliance"""
        try:
            position = self.get_current_position()
            if not position:
                logger.warning("No GPS position available for compliance check")
                return None
            
            location = (position.latitude, position.longitude)
            
            compliance_check = await self.regulation_checker.check_compliance(
                location=location,
                target_species=target_species,
                fishing_date=fishing_date,
                gear_types=gear_types,
                fish_sizes=fish_sizes,
                catch_counts=catch_counts
            )
            
            self.compliance_history.append(compliance_check)
            
            # Notify callbacks
            for callback in self.compliance_callbacks:
                try:
                    callback(compliance_check)
                except Exception as e:
                    logger.error(f"Error in compliance callback: {e}")
            
            return compliance_check
            
        except Exception as e:
            logger.error(f"Compliance check error: {e}")
            return None
    
    async def _auto_compliance_check(self, species_names: List[str]):
        """Automatically check compliance for identified species"""
        try:
            await self.check_fishing_compliance(target_species=species_names)
        except Exception as e:
            logger.error(f"Auto compliance check error: {e}")
    
    def get_species_recommendations(self) -> List[FishSpecies]:
        """Get species recommendations based on current location and conditions"""
        try:
            position = self.get_current_position()
            if not position:
                return []
            
            location = (position.latitude, position.longitude)
            water_temp = self.get_water_temperature()
            depth = self.get_current_depth()
            
            # Determine habitat based on location and conditions
            # Simplified logic - in practice would be more sophisticated
            if depth and depth > 100:
                habitat = FishHabitat.DEEP_SEA
            elif water_temp and water_temp < 15:
                habitat = FishHabitat.SALTWATER  # Cold water
            else:
                habitat = FishHabitat.SALTWATER  # Default
            
            # Get current season
            current_month = datetime.now().strftime("%B").lower()
            
            return self.fish_identifier.get_species_recommendations(
                location=location,
                habitat=habitat,
                season=current_month
            )
            
        except Exception as e:
            logger.error(f"Error getting species recommendations: {e}")
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        position = self.get_current_position()
        
        return {
            "system_status": {
                "nmea_connected": self.status.nmea_connected,
                "weather_active": self.status.weather_active,
                "fish_id_ready": self.status.fish_id_ready,
                "regulations_loaded": self.status.regulations_loaded,
                "last_update": self.status.last_update.isoformat()
            },
            "current_position": {
                "latitude": position.latitude if position else None,
                "longitude": position.longitude if position else None,
                "altitude": position.altitude if position else None,
                "speed": position.speed if position else None,
                "course": position.course if position else None,
                "satellites": position.satellites if position else None
            } if position else None,
            "environmental_data": {
                "depth_meters": self.get_current_depth(),
                "water_temperature_celsius": self.get_water_temperature(),
                "wind_data": {
                    "speed_knots": self.current_nmea_data.wind.wind_speed_knots,
                    "direction_degrees": self.current_nmea_data.wind.wind_angle,
                    "reference": self.current_nmea_data.wind.reference
                } if self.current_nmea_data and self.current_nmea_data.wind else None
            },
            "weather_alerts": [
                {
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "description": alert.description[:100] + "..." if len(alert.description) > 100 else alert.description
                }
                for alert in self.get_weather_alerts()
            ],
            "statistics": {
                "fish_identifications": len(self.identification_history),
                "compliance_checks": len(self.compliance_history),
                "recent_violations": sum(1 for check in self.compliance_history[-10:] if check.violations)
            }
        }
    
    # Callback registration methods
    
    def add_location_callback(self, callback):
        """Add callback for location updates"""
        self.location_callbacks.append(callback)
    
    def add_weather_callback(self, callback):
        """Add callback for weather updates"""
        self.weather_callbacks.append(callback)
    
    def add_fish_id_callback(self, callback):
        """Add callback for fish identification results"""
        self.fish_id_callbacks.append(callback)
    
    def add_compliance_callback(self, callback):
        """Add callback for compliance check results"""
        self.compliance_callbacks.append(callback)
    
    # Utility methods
    
    def save_system_log(self, file_path: str):
        """Save comprehensive system log"""
        try:
            log_data = {
                "system_info": self.get_system_status(),
                "nmea_data": {
                    "gps": {
                        "latitude": self.current_nmea_data.gps.latitude,
                        "longitude": self.current_nmea_data.gps.longitude,
                        "timestamp": self.current_nmea_data.gps.timestamp.isoformat()
                    } if self.current_nmea_data and self.current_nmea_data.gps else None,
                    "depth": {
                        "depth_meters": self.current_nmea_data.depth.depth_meters,
                        "timestamp": self.current_nmea_data.depth.timestamp.isoformat()
                    } if self.current_nmea_data and self.current_nmea_data.depth else None
                },
                "fish_identifications": [
                    {
                        "timestamp": result.timestamp.isoformat(),
                        "location": result.location,
                        "species_count": len(result.identifications),
                        "species": [
                            {
                                "common_name": id.species.common_name,
                                "scientific_name": id.species.scientific_name,
                                "confidence": id.confidence
                            }
                            for id in result.identifications
                        ]
                    }
                    for result in self.identification_history[-10:]  # Last 10
                ],
                "compliance_checks": [
                    {
                        "timestamp": check.timestamp.isoformat(),
                        "location": check.location,
                        "target_species": check.target_species,
                        "violations_count": len(check.violations),
                        "violations": [
                            {
                                "type": v.violation_type,
                                "severity": v.severity.value,
                                "description": v.description
                            }
                            for v in check.violations
                        ]
                    }
                    for check in self.compliance_history[-10:]  # Last 10
                ]
            }
            
            with open(file_path, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            logger.info(f"System log saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save system log: {e}")
    
    async def cleanup(self):
        """Cleanup all subsystems"""
        logger.info("🧹 Cleaning up Marine Navigation System...")
        
        try:
            # Cleanup NMEA
            self.nmea_manager.disconnect_all()
            
            # Cleanup weather
            if self.weather_manager:
                await self.weather_manager.cleanup()
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Example usage and demo
async def demo_marine_system():
    """Demonstration of the marine navigation system"""
    
    # Configuration
    config = MarineSystemConfig(
        nmea_devices={
            "gps": {
                "device_type": "serial",
                "port": "/dev/ttyUSB0",
                "baudrate": 4800
            },
            "depth": {
                "device_type": "tcp",
                "host": "192.168.1.100",
                "port": 10110
            }
        },
        weather_api_key="your_weather_api_key",
        weather_update_interval=300,
        weather_radar_range=50.0,
        auto_compliance_check=True,
        save_identifications=True
    )
    
    # Create system
    marine_system = MarineNavigationSystem(config)
    
    # Setup callbacks
    def on_location_update(lat, lon):
        print(f"📍 New position: {lat:.4f}, {lon:.4f}")
    
    def on_weather_update(weather_data):
        print(f"🌦️ Weather update: {len(weather_data.weather_alerts)} alerts")
    
    def on_fish_identification(result):
        print(f"🐟 Fish identified: {len(result.identifications)} species")
        for identification in result.identifications:
            species = identification.species
            print(f"  - {species.common_name}: {identification.confidence:.2f}")
    
    def on_compliance_check(check):
        print(f"📋 Compliance check: {len(check.violations)} violations")
        for violation in check.violations:
            print(f"  - {violation.severity.value}: {violation.description}")
    
    marine_system.add_location_callback(on_location_update)
    marine_system.add_weather_callback(on_weather_update)
    marine_system.add_fish_id_callback(on_fish_identification)
    marine_system.add_compliance_callback(on_compliance_check)
    
    try:
        # Initialize system
        await marine_system.initialize()
        
        # Wait for data
        await asyncio.sleep(5)
        
        # Get system status
        status = marine_system.get_system_status()
        print("\n=== MARINE NAVIGATION SYSTEM STATUS ===")
        print(json.dumps(status, indent=2, default=str))
        
        # Simulate fish identification
        print("\n=== FISH IDENTIFICATION DEMO ===")
        # In practice, this would be a real image file
        # result = await marine_system.identify_fish("/path/to/fish_image.jpg")
        
        # Manual compliance check
        print("\n=== COMPLIANCE CHECK DEMO ===")
        compliance = await marine_system.check_fishing_compliance(
            target_species=["Red Snapper", "Grouper"],
            fishing_date=date(2024, 6, 15),
            gear_types=["rod_and_reel"],
            fish_sizes={"Red Snapper": 35.0},  # Undersized
            catch_counts={"Red Snapper": 1}
        )
        
        if compliance:
            print("Compliance check completed:")
            print(f"Violations: {len(compliance.violations)}")
            print(f"Recommendations: {len(compliance.recommendations)}")
        
        # Get species recommendations
        print("\n=== SPECIES RECOMMENDATIONS ===")
        recommendations = marine_system.get_species_recommendations()
        print(f"Recommended species for this area:")
        for species in recommendations[:3]:
            print(f"- {species.common_name}: {species.description}")
        
        # Save system log
        marine_system.save_system_log("/tmp/marine_system_log.json")
        
        # Run for demo period
        print("\n=== SYSTEM RUNNING ===")
        print("Marine Navigation System running... (Press Ctrl+C to stop)")
        await asyncio.sleep(30)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        logger.error(f"Demo error: {e}")
    finally:
        await marine_system.cleanup()

if __name__ == "__main__":
    asyncio.run(demo_marine_system())